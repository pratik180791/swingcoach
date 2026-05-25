"""
SwingCoach Telegram Notifier
Sends a formatted daily summary card to a Telegram channel/chat.
Runs from GitHub Actions immediately after generate_briefing.py commits docs/.

Required GitHub repo secrets:
  TELEGRAM_BOT_TOKEN  — token from @BotFather
  TELEGRAM_CHAT_ID    — channel/group/user ID (e.g. @mychannel or -1001234567890)

Required env var (set inline in the workflow, not a secret):
  PAGES_URL           — your GitHub Pages URL (auto-derived from repository in workflow)
"""

import json
import os
import sys
import requests
from pathlib import Path

BRIEFING_PATH = Path(__file__).parent.parent / "docs" / "briefing.json"

REGIME_ICONS = {
    "BREADTH_THRUST":   "🚀",
    "STRONG_BULL":      "🟢",
    "BULL":             "🟩",
    "NEUTRAL":          "🟡",
    "CHOPPY":           "〰️",
    "BEAR":             "🟠",
    "STRONG_BEAR":      "🔴",
    "EXTREME_OVERSOLD": "⚡",
}


def format_message(b: dict, pages_url: str) -> str:
    regime    = b.get("regime", "")
    icon      = REGIME_ICONS.get(regime, "📊")
    mm_score  = b.get("mm_score", 0)
    chop      = b.get("chop_score", 0)
    headline  = b.get("headline", "")
    scan      = b.get("scan_tonight", False)
    risk_pct  = b.get("risk_pct", 0)
    risk_lvl  = b.get("risk_level", "")
    date      = b.get("date", "")

    score_str = f"+{mm_score}" if mm_score > 0 else str(mm_score)
    scan_line = "✅ *SCAN TONIGHT*" if scan else "🚫 *NO SCAN*"

    # Top 3 key signals (strip leading emoji clusters for cleaner text)
    signals = b.get("key_signals", [])[:3]
    signals_text = "\n".join(f"  • {s}" for s in signals)

    return "\n".join(filter(None, [
        f"📊 *SwingCoach — {date}*",
        "",
        f"{icon} *{regime}*  |  MM: `{score_str}`  |  Chop: `{chop}/12`",
        "",
        f"_{headline}_",
        "",
        f"{scan_line}  |  Capital: {risk_pct}%  |  Risk: {risk_lvl}",
        "",
        signals_text,
        "",
        f"[Full briefing →]({pages_url})",
    ]))


def send_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }, timeout=15)
    resp.raise_for_status()
    msg_id = resp.json()["result"]["message_id"]
    print(f"Telegram: sent (message_id={msg_id})")


def main():
    token    = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id  = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    pages_url = os.environ.get("PAGES_URL", "").strip()

    if not token or not chat_id:
        print("SKIP: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping Telegram send.")
        sys.exit(0)

    if not BRIEFING_PATH.exists():
        print(f"ERROR: {BRIEFING_PATH} not found. Run generate_briefing.py first.")
        sys.exit(1)

    b = json.loads(BRIEFING_PATH.read_text())
    msg = format_message(b, pages_url or "https://github.com")
    send_message(token, chat_id, msg)


if __name__ == "__main__":
    main()
