import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

TARGET_URL = "https://www.hotenavi.com/ukiuki/empty"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}" if NTFY_TOPIC else ""
STATE_FILE = Path("state.json")
JST = ZoneInfo("Asia/Tokyo")


def fetch_vacancy():
    """Fetch the page and extract the vacancy count and distinct room numbers."""
    response = requests.get(
        TARGET_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; UkiukiVacancyMonitor/1.0)"},
        timeout=25,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    count_match = re.search(r"空室\s*(\d+)\s*室", page_text)
    if not count_match:
        raise RuntimeError("空室数を読み取れません。ページ構造が変わった可能性があります。")

    vacancy_count = int(count_match.group(1))

    # The page may contain more than one link per room. A set removes duplicates.
    room_numbers = set()
    for anchor in soup.find_all("a"):
        parts = [anchor.get_text(" ", strip=True)]
        for image in anchor.find_all("img"):
            parts.extend([
                image.get("alt", ""),
                image.get("title", ""),
            ])
        label = " ".join(part for part in parts if part).strip()
        match = re.fullmatch(r"(\d{3,4})", label)
        if match:
            room_numbers.add(match.group(1))

    rooms = sorted(room_numbers, key=int)

    # Fail safely instead of treating a changed page layout as "no vacancies".
    if len(rooms) != vacancy_count:
        raise RuntimeError(
            f"空室数と部屋番号の数が一致しません "
            f"(空室数={vacancy_count}, 部屋番号={rooms})。通知・状態更新を中止しました。"
        )

    return vacancy_count, rooms


def send_notification(previous_count, previous_rooms, current_count, current_rooms):
    if not NTFY_TOPIC:
        raise RuntimeError("環境変数 NTFY_TOPIC が設定されていません。")

    new_rooms = sorted(set(current_rooms) - set(previous_rooms), key=int)
    lines = [
        f"空室数: {previous_count}室 → {current_count}室",
        "現在の空室: " + ("、".join(current_rooms) + "号室" if current_rooms else "なし"),
    ]
    if new_rooms:
        lines.append("新しく空室になった部屋: " + "、".join(new_rooms) + "号室")
    elif current_count > previous_count:
        lines.append("空室数が増加しました。部屋番号の差分は確認できませんでした。")
    lines.append(TARGET_URL)

    response = requests.post(
        NTFY_URL,
        data="\n".join(lines).encode("utf-8"),
        headers={
            "Title": "HOTEL UKIUKI Vacancy Alert",
            "Priority": "high",
            "Tags": "bell",
            "Click": TARGET_URL,
        },
        timeout=25,
    )
    response.raise_for_status()


def load_state():
    if not STATE_FILE.exists():
        return None
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return {
            "count": int(state["count"]),
            "rooms": sorted(set(map(str, state["rooms"])), key=int),
            "last_check_date_jst": state.get("last_check_date_jst", ""),
        }
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"state.jsonを読み取れません: {exc}") from exc


def save_state(count, rooms, now):
    state = {
        "count": count,
        "rooms": rooms,
        # One small daily state change keeps the scheduled repository active.
        "last_check_date_jst": now.strftime("%Y-%m-%d"),
    }
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    now = datetime.now(JST)
    count, rooms = fetch_vacancy()
    previous = load_state()

    print(f"{now:%Y-%m-%d %H:%M:%S} JST: {count}室 / 部屋番号={rooms}")

    if previous is None:
        save_state(count, rooms, now)
        print("初回実行のため、現在の状態を基準値として保存しました。通知は行いません。")
        return

    previous_count = previous["count"]
    previous_rooms = previous["rooms"]
    new_rooms = set(rooms) - set(previous_rooms)

    if new_rooms or count > previous_count:
        send_notification(previous_count, previous_rooms, count, rooms)
        print("空室の増加を検知し、ntfyへ通知しました。")
    else:
        print("新しい空室は検知されませんでした。")

    save_state(count, rooms, now)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
