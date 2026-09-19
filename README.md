# reddit-relay

Reddit の投稿を Karakeep に安定して取り込むための、ローカル向け read-only プロキシ。

Karakeep に Reddit 本体を直接クロールさせず、reddit-relay が Reddit RSS を取得して
SQLite にキャッシュし、通常の RSS と静的 HTML として配信する。

```text
Reddit
  ↓
reddit-relay
  ├─ RSS feed  (/feed/{subreddit})
  └─ HTML page (/post/{post_id})
         ↓
      Karakeep
```

## セットアップ

```powershell
uv sync
Copy-Item .env.example .env
# .env を編集して REDDIT_SUBREDDITS と REDDIT_RELAY_BASE_URL を設定
uv run uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Karakeep と同じホスト / Docker ネットワークから到達できる `REDDIT_RELAY_BASE_URL` を
設定すること。Karakeep に登録する RSS は `{BASE_URL}/feed/{subreddit}`。

## Endpoints

| Method | Path | 説明 |
| --- | --- | --- |
| GET | `/feed/{subreddit}` | RSS 2.0。link は relay 内の `/post/{id}` を指す |
| GET | `/post/{post_id}` | キャッシュ済み投稿の静的 HTML |
| GET | `/health` | `last_refresh` と `cached_posts` を返す |

## 設定 (.env)

| 変数 | 既定値 | 説明 |
| --- | --- | --- |
| `REDDIT_RELAY_HOST` | `127.0.0.1` | bind ホスト |
| `REDDIT_RELAY_PORT` | `8080` | bind ポート |
| `REDDIT_RELAY_BASE_URL` | `http://127.0.0.1:8080` | Karakeep から見た relay の URL |
| `REDDIT_RELAY_DB` | `data/reddit-relay.db` | SQLite ファイル |
| `REDDIT_SUBREDDITS` | `LocalLLaMA` | 取得対象 (カンマ区切り) |
| `REDDIT_REFRESH_INTERVAL_MINUTES` | `60` | Reddit 取得間隔 |
| `REDDIT_MAX_POSTS_PER_SUBREDDIT` | `50` | feed に出す最大件数 |
| `REDDIT_USER_AGENT` | `reddit-relay/0.1 ...` | Reddit への UA |
| `REDDIT_REQUEST_TIMEOUT_SECONDS` | `20` | HTTP タイムアウト |
| `REDDIT_RELAY_LOG_LEVEL` | `INFO` | ログレベル |

## 設計上の要点

- Reddit へのアクセスは `Refresher` の定期実行のみ。`/post` と `/feed` は SQLite キャッシュだけを読む。
- 取得失敗時もキャッシュは残り、feed / post は配信を継続する。
- feed の `guid` は `reddit:t3_<id>` で安定。link は relay の HTML を指す。
- Reddit 由来 HTML は `nh3` でサニタイズし、相対リンクは reddit.com 絶対 URL に変換する。
- canonical は Karakeep が bookmark URL を上書きして Reddit を再クロールする可能性があるため付けていない。

## Karakeep 接続確認

1. `{BASE_URL}/feed/{subreddit}` を Karakeep に登録
2. bookmark URL が `{BASE_URL}/post/...` になること
3. Reader View に本文が表示されること
4. recrawl しても Reddit への追加アクセスが発生しないこと

## 構成

```text
app/
  main.py          FastAPI 起動・lifespan・/health
  config.py        環境変数
  db.py            SQLite キャッシュ
  refresh.py       定期取得 (Reddit に触れる唯一の箇所)
  templating.py    Jinja2 環境
  validation.py    入力検証
  models/post.py   NormalizedPost
  reddit/
    source.py       RedditSource インターフェース
    rss_source.py   RSS 実装
    oauth_source.py 将来の OAuth 実装スタブ
    atom.py         Atom パーサ
    htmlutil.py     抽出・サニタイズ
  routes/
    feed.py
    post.py
  templates/
    feed.xml
    post.html
data/
  reddit-relay.db
```

## ロードマップ

- Phase 1: 単一 subreddit / RSS / SQLite / feed / post — 実装済み
- Phase 2: 複数 subreddit / 設定化 / 定期更新 / ログ / health / stale cache — 実装済み
- Phase 3: OAuth API / media / comments / Docker / metrics — 必要になったら
