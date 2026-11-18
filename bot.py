import html
from analysis import build_report
from telegram_bot import send_message

def pct(value):
    return "نامشخص" if value is None else f"{float(value):+.1f}٪"

def flow_label(value):
    if value is None:
        return "نامشخص"
    amount = float(value)
    if abs(amount) < 1:
        return "تقریباً بدون ورود یا خروج"
    strength = "زیاد" if abs(amount) >= 100 else "متوسط" if abs(amount) >= 25 else "کم"
    return ("ورود پول " if amount > 0 else "خروج پول ") + strength

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
        f"• وضعیت کل بازار در ۲۴ ساعت: {pct(global_data.get('market_cap_change_24h'))}",
        f"• قیمت بیت‌کوین: امروز {pct(btc.get('change_24h'))} | این هفته {pct(btc.get('change_7d'))}",
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
        lines.append(f"• پول آماده ورود به بازار (استیبل‌کوین‌ها): {pct(stable.get('change_7d'))} در هفته اخیر")
    else:
        lines.append("• عرضه استیبل‌کوین‌ها: داده در دسترس نیست")
    if tvl:
        lines.append(f"• سرمایه قفل‌شده در دیفای: {pct(tvl.get('change_7d'))} در هفته اخیر")
    else:
        lines.append("• TVL دیفای: داده در دسترس نیست")

    lines += ["", "📊 <b>جریان ورود و خروج پول ETF</b>"]
    etf = market.get("etf_flows") or {}
    if etf.get("available"):
        for symbol, label in (("BTC", "بیت‌کوین"), ("ETH", "اتریوم"), ("SOL", "سولانا")):
            flow = (etf.get("assets") or {}).get(symbol)
            if flow:
                daily = float(flow["daily_usd_m"])
                weekly = float(flow["weekly_usd_m"])
                lines.append(f"• {label}: امروز {flow_label(daily)} | این هفته {flow_label(weekly)}")
            else:
                lines.append(f"• {label}: داده این دارایی منتشر نشده یا دریافت آن ناموفق بوده است.")
        lines.append("ورود پول یعنی تقاضای بیشتر؛ خروج پول یعنی فشار فروش احتمالی. داده‌ها مربوط به ETFهای آمریکا هستند.")
    else:
        lines.append("• داده ETF دریافت نشد.")
        etf_errors = [err for err in market.get("errors", []) if str(err).startswith("ETF ")]
        if etf_errors:
            for err in etf_errors:
                lines.append("  علت: " + html.escape(str(err)[:350]))
        else:
            lines.append("  علت: جزئیات خطا ثبت نشده است.")
    lines += ["", "⛓️ <b>وضعیت شبکه بیت‌کوین</b>",
              "فعلاً داده معتبر کافی برای اعلام تغییرات شبکه نداریم."]

    lines += ["", "🧠 <b>تفسیر عوامل اثرگذار</b>"]
    for factor in report["factors"]:
        lines.append(f"• <b>{html.escape(factor['name'])}:</b> {html.escape(factor['detail'])}")

    lines += ["", "⏳ <b>افق احتمالی روند</b>", html.escape(report["horizon"]),
              "", "🚨 <b>خبرهای مهم ۴۸ ساعت اخیر</b>"]
    news = report["news"]
    if not news.get("available"):
        lines.append("⚠️ دریافت خبر از منابع ناموفق بود؛ درباره نبود خبر مهم نمی‌توان نتیجه‌گیری کرد.")
    elif report["important_news"]:
        for item in report["important_news"][:4]:
            lines.append(f"• <b>{html.escape(item['level'])} | {html.escape(item['category'])}</b>\n{safe_link(item)}\n<i>{html.escape(item['source'])}</i>")
    else:
        lines.append("منابع خبری پاسخ داده‌اند، اما خبر مهمی مطابق معیارهای این گزارش شناسایی نشد.")

    lines += ["", "⚠️ این تحلیل احتمالی است، نه پیش‌بینی قطعی یا توصیه خریدوفروش."]
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
