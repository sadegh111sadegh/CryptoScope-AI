import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_message(messages):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN یا TELEGRAM_CHAT_ID در Secrets تنظیم نشده است.")
    if isinstance(messages, str):
        messages = [messages]
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for message in messages:
        response = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError("Telegram API ارسال پیام را تأیید نکرد: " + str(payload))
    return True
