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

    regime = report.get("market_regime") or {}
    forecast = report.get("forecast") or {}
    if regime.get("label"):
        lines += ["", "🧭 <b>رژیم بازار</b>", html.escape(regime["label"]) + " | نوسان: " + html.escape(str(regime.get("volatility_state", "نامشخص")))]
        for evidence in (regime.get("evidence") or [])[:4]:
            lines.append("  ◦ " + html.escape(str(evidence)))
    if forecast.get("available"):
        probs = forecast.get("probabilities") or {}
        lines += [
            "", "🔮 <b>سناریوهای احتمالی ۲۴ ساعت آینده</b>",
            f"🟢 صعودی: {probs.get('up', 0):.1f}% | 🔴 نزولی: {probs.get('down', 0):.1f}% | ⚪ خنثی: {probs.get('neutral', 0):.1f}%",
            "<i>" + html.escape(forecast.get("note", "برآورد سناریویی؛ نه سیگنال قطعی")) + "</i>",
        ]
    divergences = report.get("divergences") or []
    if divergences:
        lines += ["", "⚠️ <b>واگرایی‌های شناسایی‌شده</b>"]
        for item in divergences[:4]:
            lines.append("• " + html.escape(item.get("name", "")) + ": " + html.escape(item.get("detail", "")))
    performance = report.get("forecast_performance") or {}
    if performance.get("settled", 0):
        brier = performance.get("brier_score")
        accuracy = performance.get("directional_accuracy")
        perf_text = f"ارزیابی {performance['settled']} پیش‌بینی بالغ‌شده"
        if accuracy is not None:
            perf_text += f" | دقت جهت: {accuracy:.1f}%"
        if brier is not None:
            perf_text += f" | Brier: {brier:.3f}"
        lines += ["", "🧪 <b>ارزیابی عملکرد مدل</b>", perf_text]
    if report.get("confidence") == "در حال ارزیابی":
        lines.append("اطمینان پیش‌بینی هنوز کالیبره نشده؛ تاریخچه کافی برای اعلام دقت معتبر وجود ندارد.")

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

    options = report.get("options_expiry") or {}
    if options.get("available"):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        iran_tz = ZoneInfo("Asia/Tehran")
        lines += ["", "🧨 <b>سررسید آپشن‌ها | Deribit</b>"]
        lines.append(
            f"سهم OI سررسیدشونده در ۲۴ ساعت آینده: "
            f"<b>{options.get('oi_expiring_24h_pct', 0):.1f}%</b> "
            f"| ریسک کلی سررسید: <b>{html.escape(str(options.get('expiry_risk', 'نامشخص')))}</b>"
        )
        for symbol, label in (("BTC", "بیت‌کوین"), ("ETH", "اتریوم")):
            expiries = (options.get("assets") or {}).get(symbol) or []
            if not expiries:
                continue
            item = expiries[0]
            expiry_raw = item.get("expiry")
            try:
                expiry_time = datetime.fromisoformat(expiry_raw.replace("Z", "+00:00")).astimezone(iran_tz)
                iran_clock = expiry_time.strftime("%H:%M")
                iran_date = expiry_time.strftime("%Y-%m-%d")
            except (TypeError, ValueError):
                iran_clock = "نامشخص"
                iran_date = item.get("expiry_date", "نامشخص")

            ratio = item.get("put_call_ratio")
            if ratio is None:
                interpretation = "اطلاعات کافی برای تشخیص تمایل بازار نداریم."
                ratio_text = "نامشخص"
            elif ratio >= 1.3:
                interpretation = "احتمال فشار نزولی بیشتر است؛ اما ریزش شارپ تأیید نمی‌شود."
                ratio_text = f"{ratio:.2f}"
            elif ratio <= 0.75:
                interpretation = "تمایل قراردادها بیشتر صعودی است؛ اما تضمین رشد قیمت نیست."
                ratio_text = f"{ratio:.2f}"
            else:
                interpretation = "وضعیت نسبتاً متعادل است؛ نشانه قوی از فشار نزولی دیده نمی‌شود."
                ratio_text = f"{ratio:.2f}"

            lines += [
                f"• <b>{label}</b>",
                f"  ساعت سررسید: <b>{iran_clock}</b> | تاریخ: {iran_date} (به وقت ایران)",
                f"  حجم OI: <b>{item.get('total_oi', 0):,.2f} {symbol}</b> | Put/Call: <b>{ratio_text}</b>",
                f"  برداشت: {interpretation}",
            ]
        lines.append("<i>Put/Call نسبت قراردادهای فروش به خرید است؛ عدد بالاتر از ۱ یعنی تعداد/حجم قراردادهای Put بیشتر است. این نسبت به‌تنهایی احتمال عددی یا پیش‌بینی قطعی قیمت نیست.</i>")

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
    technical_lines = []
    daily_setups = []
    technical_errors = []
    assets = technical.get("assets") or {}
    for asset_id in ("bitcoin", "ethereum", "solana"):
        asset = assets.get(asset_id) or {}
        name = html.escape(asset.get("name", asset_id))
        timeframes = asset.get("timeframes") or {}
        if asset.get("score") is not None:
            technical_lines.append(
                f"• <b>{name}:</b> {html.escape(asset.get('signal', 'نامشخص'))} | "
                f"اجماع {asset['score']}/100"
            )
        elif not timeframes:
            technical_errors.extend(asset.get("errors") or [])

        for interval in ("1d", "4h", "1h"):
            item = timeframes.get(interval)
            if not item:
                continue
            rsi = item.get("rsi14")
            ema20 = item.get("ema20")
            macd = item.get("macd_histogram")
            details = []
            if rsi is not None:
                details.append(f"RSI {rsi:.1f}")
            if ema20 is not None:
                details.append(f"EMA20 {ema20:,.2f}")
            if macd is not None:
                details.append("MACD مثبت" if macd > 0 else "MACD منفی" if macd < 0 else "MACD خنثی")
            status = html.escape(item.get("signal", "نامشخص"))
            technical_lines.append(
                f"  ◦ {name} | {interval}: {status}" +
                (" | " + " | ".join(details) if details else "")
            )

        daily = timeframes.get("1d") or {}
        setup = daily.get("entry_setup")
        if setup:
            daily_setups.append(
                f"• <b>{name}</b> | ورود: {setup['entry']:,.4f} | "
                f"حد ضرر: {setup['stop_loss']:,.4f} | "
                f"هدف: {setup['take_profit']:,.4f} | "
                f"ریسک به بازده: {setup['risk_reward']}"
            )

    lines += ["", "📐 <b>تحلیل تکنیکال چندتایم‌فریمی</b>"]
    if technical_lines:
        lines += technical_lines
    else:
        lines.append("داده تکنیکال معتبر در این اجرا دریافت نشد؛ بنابراین اجماع تایم‌فریم‌ها قابل محاسبه نیست.")
    if daily_setups:
        lines += ["", "🎯 <b>موقعیت ورود روزانه</b>"] + daily_setups
    else:
        lines += ["", "🎯 <b>سیگنال معاملاتی:</b> فعلاً هیچ ستاپ ورود روزانه‌ای با شروط سیستم تأیید نشده است."]
    if technical_errors:
        unique_errors = list(dict.fromkeys(str(error) for error in technical_errors))
        lines.append("علت/خطای دریافت داده: " + html.escape("؛ ".join(unique_errors[:2])[:260]))
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
