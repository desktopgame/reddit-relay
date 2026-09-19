# Reddit Relay — init.md

## 目的

Reddit の投稿を Karakeep に安定して取り込むための、ローカル向け小型プロキシを作る。

現在の Karakeep は RSS から新着 URL を検出した後、その URL を通常の LINK bookmark として登録し、Crawler が元 URL を再取得する。

Reddit では最近この Crawler が bot challenge に遭遇し、

* 「私は人間です」等の challenge ページが保存される
* readable content が正常に取得できない
* screenshot も challenge 画面になる

という問題がある。

このプロジェクトでは、Karakeep が Reddit 本体を直接クロールしない構成にする。

```text
Reddit
  ↓
reddit-relay
  ├─ RSS feed
  └─ local HTML article
         ↓
      Karakeep
```

Karakeep から見れば、通常の RSS と通常の Web ページに見えることを目標とする。

---

## 基本方針

最初から Reddit 固有の取得手段を1つに固定しない。

内部では Reddit 投稿を共通形式へ正規化し、その上に RSS / HTML 出力を載せる。

```text
Reddit RSS
    │
    ├── 将来: Reddit OAuth API
    │
    └── 将来: その他の取得手段
             ↓
      NormalizedPost
             ↓
      ┌──────┴──────┐
      ↓             ↓
   RSS feed      HTML page
```

初期実装では、可能なら Reddit 公式 RSS を source とする。

Reddit RSS だけでは本文等が不足する場合は、その時点で OAuth API 対応を追加する。

取得 source と Karakeep 向け出力は分離すること。

---

## 非目標

初期実装では以下を目標にしない。

* Reddit の完全ミラー
* Reddit UI の再現
* ログイン状態の再現
* 投稿・vote・コメント投稿
* Karakeep 本体の改造
* bot challenge の突破
* CAPTCHA 自動処理
* headless browser で Reddit を偽装閲覧
* 大量クロール
* 公開サービスとしての運用

あくまで個人利用の read-only relay とする。

---

## 想定配置

EVO-X2 上で動作させる。

Karakeep も EVO-X2 上に存在する。

最初は localhost または Docker 内部ネットワークだけで利用できればよく、インターネットへ公開しない。

既存構成:

```text
Karakeep
  host: 127.0.0.1:3010
  docker-compose: VPS/karakeep/
```

reddit-relay は Karakeep から HTTP で到達できればよい。

Docker 化する場合は Karakeep と同一 compose に無理に統合せず、独立プロジェクトでもよい。

---

## 必須 endpoint

最低限、以下を実装する。

### Feed

```http
GET /feed/{subreddit}
```

例:

```text
http://reddit-relay/feed/LocalLLaMA
```

RSS 2.0 または Atom を返す。

各 entry の link は reddit.com ではなく、この relay の HTML endpoint を指す。

例:

```xml
<item>
  <title>Example Reddit Post</title>
  <guid isPermaLink="false">reddit:t3_abc123</guid>
  <link>http://reddit-relay/post/t3_abc123</link>
  <pubDate>...</pubDate>
</item>
```

重要:

Karakeep は RSS 内の `content:encoded` を bookmark 本文として保存しない。

Karakeep が使うのは主に、

* title
* link
* guid
* categories

であり、link を通常の LINK bookmark として作成した後、Crawler が link 先を読む。

したがって feed の link は必ず relay 内の HTML ページを指すこと。

---

### Post

```http
GET /post/{post_id}
```

Reddit 投稿を、Karakeep Crawler が読みやすい静的 HTML として返す。

HTML はできるだけシンプルにする。

例:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Post title</title>
  <meta name="author" content="username">
  <meta property="og:title" content="Post title">
  <meta property="og:url" content="original reddit URL">
</head>
<body>
  <article>
    <h1>Post title</h1>

    <p>
      r/LocalLLaMA · u/example · 2026-09-19
    </p>

    <div class="content">
      ...
    </div>

    <p>
      <a href="https://www.reddit.com/...">
        Original on Reddit
      </a>
    </p>
  </article>
</body>
</html>
```

JavaScript は不要。

Karakeep の Readability / metascraper が安定して本文を取れる構造を優先する。

---

## NormalizedPost

source ごとの差異を外側へ漏らさない。

概念的に以下のような内部型を持つ。

```text
NormalizedPost
  id
  subreddit
  title
  author
  created_at
  original_url
  selftext
  selftext_html
  external_url
  thumbnail_url
  categories
```

必須なのは、

```text
id
title
original_url
created_at
```

本文投稿の場合は、

```text
selftext / selftext_html
```

を保持する。

リンク投稿の場合は、

```text
external_url
```

を保持する。

---

## Reddit source

### 初期候補: Reddit RSS

まず以下のような Reddit RSS から取得できる情報を調べる。

```text
https://www.reddit.com/r/{subreddit}/.rss
```

取得可能な情報を NormalizedPost へ変換する。

RSS だけで必要十分なら、初期バージョンは RSS のみで完成としてよい。

---

### 将来候補: Reddit OAuth API

RSS が不足・停止・制限された場合に備え、source interface を差し替え可能にしておく。

OAuth API の認証情報を HTML/RSS rendering 層へ直接持ち込まないこと。

例:

```text
RedditSource
  list_posts(subreddit)
  get_post(id)
```

実装例:

```text
RssRedditSource
OAuthRedditSource
```

---

## キャッシュ

Reddit へのアクセス頻度を relay 側で完全に制御できるようにする。

Karakeep が `/post/{id}` を何回取得しても、そのたびに Reddit を再取得しないこと。

最低限、

```text
post_id
payload
fetched_at
```

を保存する。

SQLite でよい。

例:

```text
posts
  id PRIMARY KEY
  subreddit
  title
  author
  original_url
  body_html
  body_text
  created_at
  fetched_at
  raw_json optional
```

RSS feed の生成は、このキャッシュを利用してよい。

---

## Reddit へのアクセス原則

外部アクセスは source 更新処理に限定する。

```text
Karakeep GET /post/... → Reddit へアクセス
```

にはしない。

正しくは、

```text
scheduled source refresh
    ↓
Reddit
    ↓
SQLite cache

Karakeep GET /post/...
    ↓
SQLite cache only
```

とする。

これにより Karakeep の recrawl や再インデックスが Reddit 側のリクエスト数に影響しない。

---

## 更新頻度

頻度は設定可能にする。

初期値の例:

```text
30分または60分
```

ただしコードに固定しない。

例:

```env
REDDIT_REFRESH_INTERVAL_MINUTES=60
```

各 subreddit を同時刻に一斉取得せず、必要なら少しずらせる設計が望ましい。

---

## 対象 subreddit

設定ファイルまたは env で指定可能にする。

例:

```env
REDDIT_SUBREDDITS=LocalLLaMA,selfhosted
```

将来的に subreddit ごとの設定を増やしやすい構造にする。

---

## Feed の重複排除

Karakeep は guid を使って既取り込み判定を行うため、guid は安定させる。

推奨:

```text
reddit:t3_<post id>
```

投稿タイトルや URL の変更で guid が変わらないこと。

---

## Original URL

Karakeep に保存される bookmark URL は relay URL になる。

そのため、元 Reddit URL を HTML 内に必ず明示する。

可能なら以下も追加する。

```html
<link rel="canonical" href="https://www.reddit.com/...">
```

ただし Karakeep が canonical を bookmark URL として上書きして Reddit を再クロールする挙動がある場合は、この canonical は外すこと。

実機確認を優先する。

---

## Media

初期実装では最低限でよい。

画像投稿の場合、

```text
i.redd.it
preview.redd.it
```

等への直接画像 URL を HTML に含めてもよい。

ただし画像取得によって Karakeep が Reddit 系 CDN へアクセスする点には注意する。

最初は、

* title
* text
* original URL

だけでもよい。

メディア対応は後回し可。

---

## コメント

初期実装ではコメント取得を必須としない。

まず投稿本文のみで完成させる。

将来、

```text
GET /post/{id}?comments=true
```

等を追加してもよいが、本文 relay とコメント relay は分離して考える。

Hermes がニュース要約する用途では、まず OP 本文だけで十分。

---

## Karakeep との接続確認

完成条件として、Karakeep に relay RSS を登録し、以下を確認する。

1. Karakeep が RSS を正常に取得する
2. 新規投稿が bookmark として追加される
3. bookmark URL が `reddit-relay/post/...` になる
4. Karakeep Crawler が relay HTML を取得する
5. Reader View に投稿本文が正常表示される
6. screenshot に challenge ページではなく relay HTML が表示される
7. AI tag generation が正常動作する
8. 全文検索に投稿本文が含まれる
9. 元 Reddit URL がブラウザから辿れる
10. recrawl しても Reddit への追加アクセスが発生しない

特に 10 を確認すること。

---

## ログ

少なくとも以下を記録する。

```text
source refresh start
source refresh success/failure
subreddit
new posts count
Reddit HTTP status
cache hit/miss
feed request
post request
```

Reddit token 等の secret は絶対にログへ出さない。

---

## エラー時

Reddit が取得不能でも、既存キャッシュは配信し続ける。

```text
Reddit unavailable
      ↓
refresh fails
      ↓
old cache remains
      ↓
Karakeep feed/post endpoints remain available
```

source 取得失敗を理由に feed 全体を 500 にしない方が望ましい。

---

## Security

ローカル利用を前提とする。

* write endpoint は作らない
* Reddit 認証情報を browser 側へ露出しない
* secrets は `.env`
* `.env` は gitignore
* external redirect proxy のような任意 URL fetch 機能を作らない
* subreddit / post id は入力検証する
* HTML に Reddit 由来の raw HTML をそのまま出す場合は sanitize を検討する

特に `selftext_html` をそのまま返す場合は XSS を考慮する。

可能なら Markdown / text を安全な HTML に再レンダリングする。

---

## プロジェクト構成案

技術スタックは opencode が適切に選んでよい。

Python/FastAPI でも Node でもよい。

小さい構成を優先する。

例:

```text
reddit-relay/
  init.md
  README.md
  .env.example

  app/
    main.*
    config.*
    db.*

    reddit/
      source.*
      rss_source.*
      oauth_source.*

    models/
      post.*

    routes/
      feed.*
      post.*

    templates/
      post.html

  data/
    reddit-relay.db
```

Dockerfile / docker-compose は必要になった段階で追加する。

---

## API example

### Feed

```text
GET /feed/LocalLLaMA
```

### HTML

```text
GET /post/t3_abc123
```

### Health

```text
GET /health
```

返却:

```json
{
  "status": "ok"
}
```

任意で、

```json
{
  "status": "ok",
  "last_refresh": "...",
  "cached_posts": 123
}
```

程度まで出してよい。

---

## 実装優先順位

### Phase 1

* subreddit を1つ固定してよい
* Reddit RSS取得
* NormalizedPost
* SQLite cache
* `/feed/{subreddit}`
* `/post/{id}`
* Karakeep から実機確認

ここで一度動かす。

### Phase 2

* 複数 subreddit
* 設定化
* periodic refresh
* logging
* health
* stale cache 運用

### Phase 3

必要になった場合のみ:

* Reddit OAuth API
* media
* comments
* Docker化
* metrics

---

## 最重要方針

過剰実装しない。

このプロジェクトの目的は、

> Reddit の投稿を、Karakeep が普通の RSS + Web article として安全かつ安定して読めるようにする

ことだけ。

Karakeep / Hermes / RocketChat の責務を reddit-relay に持ち込まない。

```text
reddit-relay
    ↓
Karakeep
    ↓
news pipeline
    ↓
RocketChat
    ↓
Hermes
```

reddit-relay は最初の1段だけ担当する。

---

## 完成の定義

以下が成立したら最初の完成とする。

```text
Reddit の新着投稿
    ↓
reddit-relay が取得・キャッシュ
    ↓
RSS に出る
    ↓
Karakeep が bookmark 化
    ↓
relay HTML を crawl
    ↓
Reader View で本文が読める
```

かつ、

```text
Karakeep が Reddit.com の投稿ページを直接 crawl しない
```

こと。
