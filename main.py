"""GitHub Changelog の新着をチェックし、あればメール通知する（無ければコンソールにプレビュー表示）。"""

import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
SEEN_PATH = BASE_DIR / "data" / "seen_urls.json"
SITE_URL = "https://github.blog/changelog/"
USER_AGENT = "Mozilla/5.0 (compatible; changelog-watcher/1.0)"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def fetch_html(url: str) -> str:
    # ページのHTMLを取得する。タイムアウトとUser-Agentを指定して行儀よく取得する
    response = requests.get(url, timeout=10, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.text


def parse_entries(html: str, base_url: str) -> list[dict]:
    # ChangelogItemごとにタイトル・URL・日付・種別を抜き出す
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    for item in soup.find_all(class_="ChangelogItem"):
        link_tag = item.find("a", class_="ChangelogItem-title")
        if link_tag is None:
            continue
        href = link_tag.get("href")
        if href is None:
            continue

        title = link_tag.get_text(strip=True)
        url = urljoin(base_url, href)

        time_tag = item.find("time")
        date = time_tag.get("datetime", "") if time_tag else ""

        type_tag = item.find("span", class_="Tag--type-alt")
        entry_type = type_tag.get_text(strip=True) if type_tag else ""

        entries.append({"title": title, "url": url, "date": date, "type": entry_type})
    return entries


def load_seen(path: Path) -> set[str]:
    # 前回までに検知済みのURL一覧を読み込む。初回実行時はファイルが無いので空集合を返す
    if not path.exists():
        return set()

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # JSONとして読めても中身がURL文字列のリストでなければ異常とみなして停止する
    if not isinstance(data, list) or not all(isinstance(url, str) for url in data):
        raise RuntimeError(f"JSONファイルはURL文字列のリストである必要があります: {path}")

    return set(data)


def save_seen(path: Path, urls: set[str]) -> None:
    # data/ ディレクトリが無ければ作成し、URL一覧を整形して保存する
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(urls), f, ensure_ascii=False, indent=2)


def find_new_entries(entries: list[dict], seen_urls: set[str]) -> list[dict]:
    # URLがまだ検知済み一覧に無いものだけを新着として返す
    return [entry for entry in entries if entry["url"] not in seen_urls]


def build_message(new_entries: list[dict]) -> tuple[str, str]:
    # 日本語の件名・本文を組み立てる
    subject = f"【新着情報】GitHub Changelogに{len(new_entries)}件の更新"
    lines = []
    for entry in new_entries:
        date = entry["date"] or "日付不明"
        lines.append(f"- {entry['title']} ({date})\n  {entry['url']}")
    body = "\n".join(lines)
    return subject, body


def notify(subject: str, body: str) -> None:
    # SMTP関連の環境変数の設定状況を確認する
    required = ["SMTP_USER", "SMTP_PASS", "MAIL_TO"]
    values = {name: os.environ.get(name) for name in required}
    missing = [name for name, value in values.items() if not value]

    if len(missing) == len(required):
        # 3つとも未設定：プレビューモード（正常系）
        print("--- ここでメールを送信します（現在はプレビューのみ） ---")
        print(f"件名: {subject}")
        print("本文:")
        print(body)
        print("---------------------------------------------------")
        return

    if missing:
        # 一部だけ設定されている：設定ミスとして停止する
        raise RuntimeError(f"環境変数の設定が不完全です。未設定: {', '.join(missing)}")

    # 3つとも設定済み：実際にメールを送信する
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = values["SMTP_USER"]
    message["To"] = values["MAIL_TO"]
    message.set_content(body)

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(values["SMTP_USER"], values["SMTP_PASS"])
        smtp.send_message(message)
    print(f"{values['MAIL_TO']} 宛に送信しました。")


def main() -> None:
    html = fetch_html(SITE_URL)
    entries = parse_entries(html, SITE_URL)
    if not entries:
        raise RuntimeError("記事を1件も取得できませんでした。サイト構造が変わった可能性があります。")

    seen_urls = load_seen(SEEN_PATH)
    new_entries = find_new_entries(entries, seen_urls)

    if new_entries:
        print(f"[新着 {len(new_entries)}件を検出]")
        subject, body = build_message(new_entries)
        notify(subject, body)
    else:
        print("新着はありませんでした。")

    # notify が例外を送出した場合はここに到達せず、新着URLは「未検知」のまま残る
    all_urls = seen_urls | {entry["url"] for entry in entries}
    save_seen(SEEN_PATH, all_urls)


if __name__ == "__main__":
    main()
