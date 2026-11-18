
import html
from analysis import build_report
from telegram_bot import send_message


def money(value):
    if value is None:
        return "ناموجود"
    value = float(value)
    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f} تریلیون"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f} میلیارد"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f} میلیون"
    return f"${value:,.0f}"


def signed(value):
    if value is None:
        return "ناموجود"
    return f"{value:+.2f}%"


def main():
    r = build_report()
    m = r["market"]
    g = m.get("global", {})
    stable = m.get("stablecoins")
    tvl = m.get("defi_tvl")

    lines = [
        "📡 <b>CRYPTOSCOPE AI</b>",
        "━━━━━━━━━━━━━━━━",
        f"🧭 <b>جهت کلی بازار:</b> {html.escape(r['direction'])}",
        f"📊 <b>امتیاز تحلیلی:</b> {r['score'] if r['score'] is not None else 'ناموجود'} از ۱۰۰",
        f"🔎 <b>اطمینان تحلیل:</b> {r['confidence']}",
        "",
        "💰 <b>وضعیت بازار و سرمایه</b>",
        f"• ارزش کل بازار: {money(g.get('market_cap'))}",
        f"• تغییر ارزش بازار: {signed(g.get('market_cap_change_24h'))}",
        f"• دامیننس بیت‌کوین: {g.get('btc_dominance', 'ناموجود')}%",
        "",
        "🌊 <b>شاخص‌های نقدینگی</b>",
    ]

    if stable:
        lines.append(
            f"• عرضه استیبل‌کوین‌ها: ۷ روز {signed(stable.get('change_7d'))} | "
            f"۳۰ روز {signed(stable.get('change_30d'))}"
        )
    else:
        lines.append("• عرضه استیبل‌کوین‌ها: داده موجود نیست")

    if tvl:
        lines.append(
            f"• TVL دیفای: ۷ روز {signed(tvl.get('change_7d'))} | "
            f"۳۰ روز {signed(tvl.get('change_30d'))}"
        )
    else:
        lines.append("• TVL دیفای: داده موجود نیست")

    lines += ["", "⛓️ <b>وضعیت آنچین و شبکه</b>"]

    for factor in r["factors"]:
        if factor["name"] in (
            "فعالیت شبکه بیت‌کوین",
            "قدرت شبکه بیت‌کوین"
        ):
            lines.append(
                f"• {html.escape(factor['name'])}: "
                f"{html.escape(factor['detail'])}"
            )

    lines += ["", "🧠 <b>ارزیابی عوامل بازار</b>"]

    for factor in r["factors"]:
        if factor["name"] in (
            "فعالیت شبکه بیت‌کوین",
            "قدرت شبکه بیت‌کوین"
        ):
            continue
        lines.append(
            f"• <b>{html.escape(factor['name'])}</b>: "
            f"{html.escape(factor['detail'])}"
        )

    lines += [
        "",
        "⏳ <b>مدت احتمالی تداوم روند</b>",
        html.escape(r["horizon"]),
        "",
        "🚨 <b>اخبار و ریسک‌های مهم ۴۸ ساعت اخیر</b>"
    ]

    if not r["news"]["available"]:
        lines.append(
            "⚠️ دریافت خبر با خطا مواجه شد؛ "
            "نمی‌توان نتیجه گرفت که خبر مهمی وجود ندارد."
        )
    elif r["important_news"]:
        for item in r["important_news"][:5]:
            title = html.escape(item["title"])
            source = html.escape(item["source"])
            url = html.escape(item["url"], quote=True)
            lines.append(
                f"\n• <b>{item['level']}</b> | {source}\n"
                f'<a href="{url}">{title}</a>'
            )
    else:
        lines.append("در داده‌های دریافت‌شده خبر مهمی شناسایی نشد.")

    lines += [
        "",
        "⚠️ <b>محدودیت تحلیل</b>",
        "عرضه استیبل‌کوین و TVL شاخص جانشین نقدینگی‌اند؛ "
        "جریان خالص ETF، ورود و خروج صرافی‌ها و تراکنش نهنگ‌ها "
        "به‌طور مستقیم در این نسخه اندازه‌گیری نمی‌شوند.",
        "",
        "این گزارش توصیه خرید یا فروش نیست."
    ]

    message = "\n".join(lines)

    # Telegram message length safety
    if len(message) > 3900:
        message = message[:3750] + "\n\nگزارش به دلیل محدودیت طول کوتاه شد."

    if not send_message(message):
        raise RuntimeError("ارسال پیام تلگرام ناموفق بود.")


if __name__ == "__main__":
    main()
