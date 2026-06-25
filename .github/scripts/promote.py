#!/usr/bin/env python3
"""Promote the routine's latest `claude/*` digest branch into `main`.

Why this exists: the Claude Code cloud routine reliably pushes the daily digest
to an auto-named `claude/great-volta-*` branch, but cannot push to `main`
(restricted branch pushes). GitHub Pages serves `main/docs`, so without this
the published feed goes stale. This action runs server-side (no Claude branch
restriction) and copies the routine's already-rendered docs/ + state/ from the
newest digest branch onto main — no re-rendering, so the feed/index format never
drifts from what the routine produced.

Safety:
- Only promotes when the source branch's newest target-date is strictly newer
  than main's (a fresh routine branch is always a superset of main + the new day,
  because each run builds on the current main).
- Deletes the consumed branch and any subsumed (older) claude/* branches so they
  don't accumulate.
"""
import re
import subprocess
import sys


def run(*args, check=True):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def max_target_date(ref):
    """Newest <mlrss:target-date> in ref:docs/feed.xml, or None."""
    res = run("show", f"{ref}:docs/feed.xml", check=False)
    if res.returncode != 0:
        return None
    dates = re.findall(r"<mlrss:target-date>(\d{4}-\d{2}-\d{2})", res.stdout)
    return max(dates) if dates else None


def short(ref):
    return ref.replace("origin/", "", 1)


def main():
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    pushed_ref = sys.argv[2] if len(sys.argv) > 2 else ""

    refs = run(
        "for-each-ref", "--sort=-committerdate",
        "--format=%(refname:short)", "refs/remotes/origin/claude/",
    ).stdout.split()
    if not refs:
        print("No claude/* branches found; nothing to do.")
        return 0

    main_max = max_target_date("HEAD")

    if event == "push" and pushed_ref:
        src = "origin/" + pushed_ref.replace("refs/heads/", "", 1)
    else:
        src = refs[0]  # newest by committer date
    src_max = max_target_date(src)
    print(f"event={event} src={src} src_max={src_max} main_max={main_max}")

    if src_max is None:
        print(f"Source {src} has no readable feed.xml; aborting.")
        return 0

    promoted = False
    if main_max is None or src_max > main_max:
        run("checkout", src, "--", "docs/", "state/")
        run("add", "docs/", "state/")
        if run("diff", "--cached", "--quiet", check=False).returncode == 0:
            print("No content changes after checkout; skipping commit.")
        else:
            run("commit", "-m", f"chore(feed): promote routine digest {src_max}")
            run("push", "origin", "HEAD:main")
            print(f"Promoted {short(src)} -> main ({src_max}).")
            main_max = src_max
            promoted = True
    else:
        print("Source not newer than main; nothing to promote.")

    # Clean up: the consumed source branch, plus any older subsumed claude/* branch.
    for r in refs:
        rmax = max_target_date(r)
        is_subsumed = rmax is not None and main_max is not None and rmax < main_max
        if r == src or is_subsumed:
            del_res = run("push", "origin", "--delete", short(r), check=False)
            status = "ok" if del_res.returncode == 0 else "failed"
            print(f"delete {short(r)} (max={rmax}): {status}")

    print("promoted" if promoted else "no-op")
    return 0


if __name__ == "__main__":
    sys.exit(main())
