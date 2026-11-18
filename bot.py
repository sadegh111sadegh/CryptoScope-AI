import html
from analysis import build_report
from telegram_bot import send_message

def money(value):
    if value is None:
        return "ناموجود"
    value = float(value)
    if value >= 1_000_000_000_000:
        return f"\${value / 1_000_000_000_000:.2f} تریلیون"
    if value >= 1_000_000_000:
        return f"\${value / 1_000_000_000:.2f} میلیارد"
    if value >= 1_000_000:
        return f"\${value / 1_000_000:.2f} میلیون"
    return f"\${value:,.0f}"

def pct(value):
    return "ناموجود" if value is None else f"{float(value):+.2f}٪"

def dominance(value):
    return "ناموجود" if value is None else f"{float(value):.2f}٪"

def fear_bar(value):
    filled = max(0, min(10, round(value / 10)))
    return "🟥" * filled + "⬜" * (10 - filled)

def safe_link(item):
    url = item.get("url", "")
    title = html.escape(item.get("title", "خبر بدون عنوان"))
    if not url.startswith(("https://", "http://")):
        return title
    return f'<a href="{html.escape(url, quote=True)}">{title}</a>'

def build_messages(report):
    market = report["market"]
    global_data = market.get("global") or {}
    stable = market.get("stablecoins")
    tvl = market.get("defi_tvl")
    btc = market.get("coins", {}).get("bitcoin", {})
    fg = market.get("fear_greed")
    usable = sum(1 for item in report["factors"] if item["score"] is not None)
    lines = [
        "📡 <b>CRYPTOSCOPE AI | گزارش روزانه بازار</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🧭 <b>جمع‌بندی:</b> {html.escape(report['direction'])}",
        f"🔎 <b>اطمینان:</b> {report['confidence']} | بر پایه {usable} شاخص قابل استفاده",
        "", "💹 <b>نمای کلی بازار</b>",
        f"• ارزش کل بازار: {money(global_data.get('market_cap'))}",
        f"• تغییر ارزش بازار در ۲۴ ساعت: {pct(global_data.get('market_cap_change_24h'))}",
        f"• حجم معاملات ۲۴ ساعت: {money(global_data.get('volume_24h'))}",
        f"• سهم بیت‌کوین از بازار: {dominance(global_data.get('btc_dominance'))}",
        f"• تغییر قیمت BTC: روزانه {pct(btc.get('change_24h'))} | هفتگی {pct(btc.get('change_7d'))}",
    ]
    if fg:
        value = fg["value"]
        lines += ["", "😨 <b>ترس و طمع بازار</b>",
                  f"{fear_bar(value)}  <b>{value}/100 — {fg['interpretation']}</b>",
                  "۰ = ترس شدید | ۱۰۰ = طمع شدید",
                  "این شاخص احساسات را نشان می‌دهد، نه درصد احتمال ریزش یا رشد."]
    else:
        lines += ["", "😨 <b>ترس و طمع:</b> داده دریافت نشد"]

    lines += ["", "🌊 <b>نقدینگی و سرمایه در اکوسیستم</b>"]
    if stable:
        lines.append(f"• عرضه استیبل‌کوین‌ها: ۷ روز {pct(stable.get('change_7d'))} | ۳۰ روز {pct(stable.get('change_30d'))}")
        lines.append("  رشد عرضه می‌تواند ظرفیت نقدینگی را بیشتر کند؛ لزوماً به معنی ورود پول به صرافی‌ها نیست.")
    else:
        lines.append("• عرضه استیبل‌کوین‌ها: داده در دسترس نیست")
    if tvl:
        lines.append(f"• TVL دیفای: ۷ روز {pct(tvl.get('change_7d'))} | ۳۰ روز {pct(tvl.get('change_30d'))}")
        lines.append("  تغییر TVL هم از ورود سرمایه و هم از تغییر قیمت دارایی‌ها اثر می‌گیرد.")
    else:
        lines.append("• TVL دیفای: داده در دسترس نیست")

    lines += ["", "⛓️ <b>آنچین و سلامت شبکه بیت‌کوین</b>"]
    network = report.get("network", {})
    tx, hashrate = network.get("n-transactions"), network.get("hash-rate")
    lines.append(f"• تعداد تراکنش‌ها: تغییر ۷ روزه {pct(tx.get('change_7d'))}" if tx else "• تعداد تراکنش‌ها: داده در دسترس نیست")
    lines.append(f"• هش‌ریت شبکه: تغییر ۷ روزه {pct(hashrate.get('change_7d'))}" if hashrate else "• هش‌ریت شبکه: داده در دسترس نیست")
    lines.append("  این شاخص‌ها وضعیت استفاده و امنیت شبکه را توصیف می‌کنند؛ به‌تنهایی سیگنال خرید یا فروش نیستند.")

    lines += ["", "🧠 <b>تفسیر عوامل اثرگذار</b>"]
    for factor in report["factors"]:
        lines.append(f"• <b>{html.escape(factor['name'])}:</b> {html.escape(factor['detail'])}")

    lines += ["", "⏳ <b>افق احتمالی روند</b>", html.escape(report["horizon"]),
              "", "🚨 <b>خبرهای مهم ۴۸ ساعت اخیر</b>"]
    news = report["news"]
    if not news.get("available"):
        lines.append("⚠️ دریافت خبر از منابع ناموفق بود؛ درباره نبود خبر مهم نمی‌توان نتیجه‌گیری کرد.")
    elif report["important_news"]:
        for item in report["important_news"][:6]:
            lines.append(f"• <b>{html.escape(item['level'])} | {html.escape(item['category'])}</b>\n{safe_link(item)}\n<i>{html.escape(item['source'])}</i>")
    else:
        lines.append("منابع خبری پاسخ داده‌اند، اما خبر مهمی مطابق معیارهای این گزارش شناسایی نشد.")

    lines += ["", "📌 <b>جریان واقعی پول؛ چه چیزی اندازه‌گیری نشده؟</b>",
              "جریان خالص ETF، ورود/خروج صرافی‌ها و خریدوفروش نهنگ‌ها در این نسخه مستقیماً اندازه‌گیری نمی‌شوند؛ بنابراین رشد استیبل‌کوین یا TVL را ورود قطعی پول معرفی نمی‌کنیم.",
              "", "⚠️ این گزارش سناریوی تحلیلی است، نه پیش‌بینی قطعی یا توصیه خریدوفروش."]
    if market.get("errors"):
        lines += ["", f"ℹ️ تعداد منابع داده ناموفق: {len(market['errors'])}؛ بخش‌های بدون داده در گزارش مشخص شده‌اند."]

    messages, current = [], ""
    for line in lines:
        candidate = (current + "\n" + line).strip() if current else line
        if len(candidate) > 3800:
            if current:
                messages.append(current)
            current = line[:3700]
        else:
            current = candidate
    if current:
        messages.append(current)
    return messages

def main():
    report = build_report()
    if not send_message(build_messages(report)):
        raise RuntimeError("ارسال گزارش تلگرام ناموفق بود.")

if __name__ == "__main__":
    main()
