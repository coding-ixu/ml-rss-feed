# ml-rss-feed

Public GitHub Pages リポジトリ。`ml-rss-automation` の Claude Code Routine から `docs/` と `state/` が自動更新される。

## レイアウト

```
docs/
  .nojekyll
  index.html       # 自動生成（render_index.py）
  feed.xml         # 自動生成（update_feed.py）
state/
  seen.json        # 重複排除キャッシュ（生IDは含まない）
  last_run.json    # 最後の実行サマリ
```

## GitHub Pages 設定

```
Settings → Pages
  Source:  Deploy from a branch
  Branch:  main
  Folder:  /docs
```

公開URL（Project site の場合）:

```
https://<github-user>.github.io/ml-rss-feed/
https://<github-user>.github.io/ml-rss-feed/feed.xml
```

## 注意

- このリポジトリは Public です。生IDや本文、メールアドレス、トラッキングURLは絶対に書き込まないでください。
- 書き換え対象は `docs/` と `state/` のみ。`ml-rss-automation` 側の `CLAUDE.md` で強制されています。
- Routine は `main` に直接 push します。PR ベースの運用ではありません。
