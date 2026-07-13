#!/usr/bin/env python3
"""Verify the LIVE public feed is fresh, not just the repo.

The routine, the promote action, and the Pages self-heal all guard the
*publishing* of an already-generated digest. None of them notice when no
digest was generated at all, or when the served site silently diverges from
main. This check closes that gap by asserting what the user actually sees:
the newest <mlrss:target-date> on the public URL must be yesterday (JST).

Exit codes (consumed by feed-freshness-watchdog.yml):
  0 = live feed is fresh
  2 = live feed is stale but main is fresh  -> Pages/CDN layer, rebuild fixes
  3 = main itself is stale                  -> routine/promote layer, alert
  4 = live feed unreachable/unparseable     -> serving layer, alert
"""
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

LIVE_URL = "https://coding-ixu.github.io/ml-rss-feed/feed.xml"
TARGET_DATE_RE = re.compile(r"<mlrss:target-date>(\d{4}-\d{2}-\d{2})</mlrss:target-date>")


def newest_target_date(xml: str) -> str:
    dates = TARGET_DATE_RE.findall(xml)
    return max(dates) if dates else ""


def emit(key: str, value: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")
    print(f"{key}={value}")


def main() -> int:
    now_jst = datetime.now(ZoneInfo("Asia/Tokyo"))
    expected = (now_jst - timedelta(days=1)).date().isoformat()
    if os.environ.get("SIMULATE_STALE") == "true":
        expected = (now_jst + timedelta(days=1)).date().isoformat()
        print("::warning::SIMULATE_STALE=true — using impossible expected date to test the alert path")

    main_xml = Path("docs/feed.xml").read_text(encoding="utf-8")
    main_latest = newest_target_date(main_xml)

    live_latest = ""
    live_error = ""
    # Query string busts the Fastly/browser cache so we judge fresh content.
    url = f"{LIVE_URL}?watchdog={now_jst.strftime('%Y%m%d%H%M%S')}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            live_latest = newest_target_date(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - any fetch failure is a stale verdict
        live_error = str(exc)

    emit("expected", expected)
    emit("main_latest", main_latest)
    emit("live_latest", live_latest)
    emit("live_error", live_error)

    if live_error or not live_latest:
        emit("verdict", "unreachable")
        return 4
    if live_latest >= expected:
        emit("verdict", "fresh")
        return 0
    if main_latest >= expected:
        emit("verdict", "pages_stale")
        return 2
    emit("verdict", "main_stale")
    return 3


if __name__ == "__main__":
    sys.exit(main())
