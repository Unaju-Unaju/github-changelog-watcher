# GitHub Changelog 新着監視スクリプト

[GitHub Changelog](https://github.blog/changelog/) を定期的にチェックし、新しいお知らせがあれば内容をメールで通知する試作品です。

## セットアップ

まず、他のプロジェクトと依存関係が混ざらないよう、仮想環境を作成します。

```bash
python -m venv .venv
```

作成した仮想環境を有効化します。

```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

以降のコマンドは、仮想環境を有効化した状態で実行してください。まず、pipが使えるか確認します。

```bash
python -m pip --version
```

`No module named pip` のようなエラーが出た場合のみ、以下でpipを有効化します。

```bash
python -m ensurepip --upgrade
python -m pip install --upgrade pip
```

pipが使える状態になったら、依存ライブラリをインストールします。

```bash
python -m pip install -r requirements.txt
```

作業を終了する際は、以下のコマンドで仮想環境を抜けられます。

```bash
deactivate
```

## 実行方法

```bash
python main.py
```

## 仕組み

1. `https://github.blog/changelog/` のHTMLを取得する
2. 各お知らせ（タイトル・URL・日付）を抜き出す
3. `data/seen_urls.json` に保存済みのURL一覧と比較し、まだ見ていないURLを「新着」とする
4. 新着があれば、メール送信（設定していなければコンソールにプレビュー表示）する
5. 今回確認した全URLを `data/seen_urls.json` に保存する

**初回実行時は `data/seen_urls.json` がまだ存在しないため、その時点の全記事が「新着」として扱われます。** 2回目以降の実行から、本当の意味での新着だけが検出されます。

## 実際にメールを送りたい場合

接続先はGmailの `smtp.gmail.com:465`（SSL）に設定しています。Gmail以外を使う場合はコード内の`SMTP_HOST`/`SMTP_PORT`を変更してください。

1. Googleアカウントで「アプリパスワード」を発行する（2段階認証を有効にした上で、Googleアカウントの[セキュリティ設定](https://myaccount.google.com/security) → アプリパスワード から発行）
2. 以下の環境変数をすべて設定してから実行する

```bash
export SMTP_USER="you@gmail.com"
export SMTP_PASS="xxxx xxxx xxxx xxxx"   # 発行したアプリパスワード
export MAIL_TO="you@example.com"
python main.py
```

3つの環境変数が全く設定されていなければプレビューモード（正常動作）、3つとも揃っていれば実送信します。1つや2つだけ設定されている場合は設定ミスとみなし、どの変数が未設定かを示すエラーで停止します（この場合 `data/seen_urls.json` は更新されません）。

## 定期実行する場合

cronやlaunchdなど、OS標準のスケジューラーに登録することで定期実行も可能です。

## 別サイトに転用する場合

- `main.py` 冒頭の `SITE_URL` を対象サイトのURLに変更する
- `parse_entries()` 内のCSSセレクタ（`ChangelogItem` / `ChangelogItem-title` / `Tag--type-alt` など）を対象サイトのHTML構造に合わせて変更する

それ以外の部分（差分検知・メール通知・保存処理）はそのまま流用できます。

## 動作確認済み

- 実サイト（`https://github.blog/changelog/`）からのHTML取得・新着検出
- メール未設定時のコンソールプレビュー表示
- 環境変数設定時の実際のメール送信（Gmail経由）
- 2回目以降の実行で、既知記事が新着と判定されないこと
