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
    usable = sum(1 for item in report.get("factors", []) if item.get("score") is not None)

    lines = [
        "📡 <b>CRYPTOSCOPE AI | گزارش روزانه بازار</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🧭 <b>جمع‌بندی:</b> {html.escape(report['direction'])}",
        f"🔎 <b>اطمینان:</b> {html.escape(str(report['confidence']))} | بر پایه {usable} شاخص قابل استفاده",
    ]

    market_lines = []
    market_cap_change = global_data.get("market_cap_change_24h")
    btc_24h = btc.get("change_24h")
    btc_7d = btc.get("change_7d")
    if market_cap_change is not None:
        market_lines.append(f"• ارزش کل بازار: در ۲۴ ساعت گذشته {trend_label(market_cap_change)}")
    if btc_24h is not None or btc_7d is not None:
        parts = []
        if btc_24h is not None:
            parts.append("امروز " + trend_label(btc_24h))
        if btc_7d is not None:
            parts.append("این هفته " + trend_label(btc_7d))
        market_lines.append("• بیت‌کوین: " + " | ".join(parts))
    if market_lines:
        lines += ["", "💹 <b>نمای کلی بازار</b>"] + market_lines

    if fg and fg.get("value") is not None:
        value = int(fg["value"])
        lines += [
            "", "😨 <b>ترس و طمع بازار</b>",
            f"{fear_bar(value)}  <b>{html.escape(str(fg.get('interpretation', '')))} | {value}/100</b>",
        ]

    liquidity_lines = []
    if stable and stable.get("change_7d") is not None:
        liquidity_lines.append(f"• پول آماده ورود به بازار: {trend_label(stable['change_7d'])}")
    if tvl and tvl.get("change_7d") is not None:
        liquidity_lines.append(f"• سرمایه داخل پروژه‌های دیفای: {trend_label(tvl['change_7d'])}")
    if liquidity_lines:
        lines += ["", "🌊 <b>نقدینگی و سرمایه در اکوسیستم</b>"] + liquidity_lines

    etf = market.get("etf_flows") or {}
    etf_lines = []
    if etf.get("available"):
        for symbol, label in (("BTC", "بیت‌کوین"), ("ETH", "اتریوم"), ("SOL", "سولانا")):
            flow = (etf.get("assets") or {}).get(symbol)
            if not flow:
                continue
            parts = []
            daily = flow.get("daily_usd_m")
            weekly = flow.get("weekly_usd_m")
            if daily is not None:
                parts.append("امروز " + flow_label(daily))
            if weekly is not None:
                parts.append("این هفته " + flow_label(weekly))
            if parts:
                etf_lines.append(f"• {label}: " + " | ".join(parts))
    if etf_lines:
        lines += ["", "📊 <b>جریان ورود و خروج پول ETF</b>"] + etf_lines

    network = report.get("network") or {}
    network_lines = []
    for key, label in (("n-transactions", "تعداد تراکنش‌ها"), ("hash-rate", "قدرت محاسباتی شبکه")):
        item = network.get(key)
        if item and item.get("change_7d") is not None:
            network_lines.append(f"• {label}: در مقایسه با حدود ۷ روز قبل {trend_label(item['change_7d'])}")
    if network_lines:
        lines += ["", "⛓️ <b>وضعیت شبکه بیت‌کوین</b>"] + network_lines
        lines.append("افزایش تراکنش به معنی افزایش فعالیت شبکه است، نه لزوماً خرید؛ هش‌ریت بیشتر به امنیت شبکه مربوط است.")

    technical = report.get("technical") or {}
    if technical.get("available"):
        technical_lines = []
        daily_setups = []
        for asset_id in ("bitcoin", "ethereum", "solana"):
            asset = (technical.get("assets") or {}).get(asset_id) or {}
            if asset.get("score") is None:
                continue
            technical_lines.append(
                f"• <b>{html.escape(asset.get('name', asset_id))}:</b> "
                f"{html.escape(asset.get('signal', 'نامشخص'))} | امتیاز {asset['score']}/100"
            )
            for interval in ("1d", "4h", "1h"):
                item = (asset.get("timeframes") or {}).get(interval)
                if not item:
                    continue
                rsi = item.get("rsi14")
                ema20 = item.get("ema20")
                details = []
                if rsi is not None:
                    details.append(f"RSI {rsi:.1f}")
                if ema20 is not None:
                    details.append(f"EMA20 {ema20:,.2f}")
                if details:
                    technical_lines.append(
                        f"  ◦ {interval}: {html.escape(item.get('signal', ''))} | " + " | ".join(details)
                    )
            daily = (asset.get("timeframes") or {}).get("1d") or {}
            setup = daily.get("entry_setup")
            if setup:
                daily_setups.append(
                    f"• <b>{html.escape(asset.get('name', asset_id))}</b> | "
                    f"ورود: {setup['entry']:,.4f} | "
                    f"حد ضرر: {setup['stop_loss']:,.4f} | "
                    f"هدف: {setup['take_profit']:,.4f} | "
                    f"ریسک به بازده: {setup['risk_reward']}"
                )
        if technical_lines:
            lines += ["", "📐 <b>تحلیل تکنیکال چندتایم‌فریمی</b>"] + technical_lines
        if daily_setups:
            lines += ["", "🎯 <b>موقعیت ورود روزانه</b>"] + daily_setups

    factors = [
        item for item in report.get("factors", [])
        if item.get("score") is not None and item.get("detail")
    ]
    if factors:
        lines += ["", "🧠 <b>تفسیر عوامل اثرگذار</b>"]
        for factor in factors:
            lines.append(f"• <b>{html.escape(factor['name'])}:</b> {html.escape(factor['detail'])}")

    horizon = report.get("horizon")
    if horizon and not any(term in str(horizon) for term in ("داده کافی", "اطلاعات کافی", "نامشخص")):
        lines += ["", "⏳ <b>افق احتمالی روند</b>", html.escape(str(horizon))]

    important_news = report.get("important_news") or []
    if important_news:
        lines += ["", "🚨 <b>خبرهای مهم ۴۸ ساعت اخیر</b>"]
        for item in important_news[:4]:
            lines.append(
                f"• <b>{html.escape(item['level'])} | {html.escape(item['category'])}</b>\n"
                f"{safe_link(item)}\n"
                f"<i>{html.escape(item['source'])}</i>"
            )

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
