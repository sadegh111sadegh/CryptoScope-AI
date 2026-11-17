
from analysis import build_report
from telegram_bot import send_message


def main():

    market, direction, score, factors, headlines, high = build_report()

    lines = [
        "📡 CRYPTOSCOPE AI",
        "",
        f"🧭 وضعیت بازار: {direction}",
        f"🎯 امتیاز: {score if score is not None else 'ناموجود'}",
        f"₿ دامیننس بیت‌کوین: {market.get('btc_dominance', 'ناموجود')}%",
        "",
        "📊 عوامل تحلیل:"
    ]

    for name, value, detail in factors:

        value_text = value if value is not None else "ناموجود"

        lines.append(
            f"• {name}: {value_text} | {detail}"
        )

    lines += ["", "🚨 اخبار مهم:"]

    for item in high[:5]:

        lines.append(
            f"\n• {item['score']}/100"
            f"\n{item['title']}"
            f"\n{item['url']}"
        )

    if not high:
        lines.append("خبر با ریسک بالا شناسایی نشد.")

    lines.append("")
    lines.append("⚠️ این گزارش توصیه خرید یا فروش نیست.")

    if not send_message("\n".join(lines)):
        raise RuntimeError("ارسال پیام تلگرام ناموفق بود.")


if __name__ == "__main__":
    main()
