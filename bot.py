import html
from analysis import build_report
from telegram_bot import send_message

def trend_label(value):
    if value is None:
        return "اطلاعات کافی نداریم"
    value = float(value)
    if value >= 3:
        return "خیلی زیاد رشد کرده"
    if value >= 1:
        return "رشد خوبی داشته"
    if value >= 0.2:
        return "کمی رشد کرده"
    if value > -0.2:
        return "تقریباً بدون تغییر بوده"
    if value > -1:
        return "کمی افت کرده"
    if value > -3:
        return "افت قابل توجهی داشته"
    return "شدیداً افت کرده"

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
        f"• ارزش کل بازار: در ۲۴ ساعت گذشته {trend_label(global_data.get('market_cap_change_24h'))}",
        f"• بیت‌کوین: امروز {trend_label(btc.get('change_24h'))} | این هفته {trend_label(btc.get('change_7d'))}",
    ]
    if fg:
        value = fg["value"]
        lines += ["", "😨 <b>ترس و طمع بازار</b>",
                  f"{fear_bar(value)}  <b>{fg['interpretation']}</b>",
                  "این بخش فقط حال‌وهوای خریداران و فروشندگان را نشان می‌دهد."]
    else:
        lines += ["", "😨 <b>ترس و طمع:</b> داده دریافت نشد"]

    lines += ["", "🌊 <b>نقدینگی و سرمایه در اکوسیستم</b>"]
    if stable:
        lines.append(f"• پول آماده ورود به بازار: {trend_label(stable.get('change_7d'))}")
    else:
        lines.append("• عرضه استیبل‌کوین‌ها: داده در دسترس نیست")
    if tvl:
        lines.append(f"• سرمایه داخل پروژه‌های دیفای: {trend_label(tvl.get('change_7d'))}")
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
    lines += ["", "⛓️ <b>وضعیت شبکه بیت‌کوین</b>"]
    network = report.get("network") or {}
    for key, label in (("n-transactions", "تعداد تراکنش‌ها"), ("hash-rate", "قدرت محاسباتی شبکه")):
        item = network.get(key)
        if item and item.get("change_7d") is not None:
            lines.append(f"• {label}: در مقایسه با حدود ۷ روز قبل {trend_label(item['change_7d'])}")
        else:
            lines.append(f"• {label}: داده معتبر در دسترس نیست")
    lines.append("افزایش تراکنش به معنی افزایش فعالیت شبکه است، نه لزوماً خرید؛ هش‌ریت بیشتر به امنیت شبکه مربوط است.")

    lines += ["", "📐 <b>تحلیل تکنیکال چندتایم‌فریمی</b>"]
    technical = report.get("technical") or {}
    if technical.get("available"):
        for asset_id in ("bitcoin", "ethereum", "solana"):
            asset = (technical.get("assets") or {}).get(asset_id) or {}
            if asset.get("score") is None:
                continue
            lines.append(
                f"• <b>{html.escape(asset.get('name', asset_id))}:</b> "
                f"{html.escape(asset.get('signal', 'نامشخص'))} | امتیاز {asset['score']}/100"
            )
            for interval in ("1d", "4h", "1h"):
                item = (asset.get("timeframes") or {}).get(interval)
                if not item:
                    continue
                rsi = item.get("rsi14")
                rsi_text = f"{rsi:.1f}" if rsi is not None else "ناموجود"
                lines.append(
                    f"  ◦ {interval}: {html.escape(item.get('signal', ''))} | "
                    f"RSI {rsi_text} | EMA20 {item.get('ema20', 0):,.2f}"
                )
        lines.append("تایم‌فریم روزانه وزن بیشتری دارد؛ کندل باز در محاسبه لحاظ نمی‌شود.")
    else:
        lines.append("داده تکنیکال کافی دریافت نشد؛ از ساخت سیگنال بر اساس داده ناقص خودداری شد.")

    lines += ["", "🧠 <b>تفسیر عوامل اثرگذار</b>"]
    for factor in report["factors"]:
        lines.append(f"• <b>{html.escape(factor['name'])}:</b> {html.escape(factor['detail'])}")

    lines += ["", "⏳ <b>افق احتمالی روند</b>", html.escape(report["horizon"])]

    # Show news only when at least one important headline was retrieved.
    important_news = report.get("important_news") or []
    if important_news:
        lines += ["", "🚨 <b>خبرهای مهم ۴۸ ساعت اخیر</b>"]
        for item in important_news[:4]:
            lines.append(
                f"• <b>{html.escape(item['level'])} | {html.escape(item['category'])}</b>\n"
                f"{safe_link(item)}\n"
                f"<i>{html.escape(item['source'])}</i>"
            )

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
