from market_data import get_market_snapshot
from news import fetch_news

def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _score(change, multiplier):
    value = _number(change)
    if value is None:
        return None
    return max(-100, min(100, round(value * multiplier)))

def _interpret(change, positive, negative, neutral="تقریباً بدون تغییر"):
    value = _number(change)
    if value is None:
        return "داده در دسترس نیست"
    if value > 0.15:
        return positive
    if value < -0.15:
        return negative
    return neutral

def build_report():
    market = get_market_snapshot()
    news = fetch_news()
    factors, signals = [], []

    def add(name, change, multiplier, detail, weight=1):
        score = _score(change, multiplier)
        factors.append({"name": name, "score": score, "detail": detail})
        if score is not None:
            signals.append((score, weight))

    global_data = market.get("global") or {}
    cap_change = global_data.get("market_cap_change_24h")
    add("ارزش کل بازار", cap_change, 7,
        _interpret(cap_change, "نشانه رشد کوتاه‌مدت ارزش بازار", "نشانه افت کوتاه‌مدت ارزش بازار"), 2)

    btc = market.get("coins", {}).get("bitcoin", {})
    btc_week = btc.get("change_7d")
    add("عملکرد هفتگی بیت‌کوین", btc_week, 4,
        _interpret(btc_week, "بیت‌کوین در هفته اخیر رشد داشته", "بیت‌کوین در هفته اخیر افت داشته"), 2)

    stable = market.get("stablecoins")
    stable_week = stable.get("change_7d") if stable else None
    add("عرضه استیبل‌کوین‌ها", stable_week, 35,
        _interpret(stable_week, "عرضه در حال افزایش است؛ می‌تواند ظرفیت نقدینگی را بیشتر کند",
                   "عرضه کاهش یافته؛ می‌تواند نشانه جمع‌شدن بخشی از نقدینگی باشد", "تغییر عرضه ناچیز است"))

    tvl = market.get("defi_tvl")
    tvl_week = tvl.get("change_7d") if tvl else None
    add("ارزش قفل‌شده دیفای", tvl_week, 8,
        _interpret(tvl_week, "سرمایه قفل‌شده در دیفای افزایش یافته",
                   "سرمایه قفل‌شده در دیفای کاهش یافته", "تغییر TVL ناچیز است"))

    etf = market.get("etf_flows") or {}
    btc_etf = (etf.get("assets") or {}).get("BTC")
    btc_etf_week = btc_etf.get("weekly_usd_m") if btc_etf else None
    etf_detail = (
        f"خالص جریان ETF بیت‌کوین در ۷ روز اخیر: {btc_etf_week:+.1f} میلیون دلار"
        if btc_etf_week is not None else "داده جریان ETF بیت‌کوین در دسترس نیست"
    )
    add("جریان خالص ETF بیت‌کوین", btc_etf_week, 0.12, etf_detail, 2)

    score = None
    if signals:
        denominator = sum(weight for _, weight in signals)
        score = round(sum(value * weight for value, weight in signals) / denominator)

    if score is None or len(signals) < 2:
        direction = "داده کافی نیست"
    elif score >= 15:
        direction = "تمایل صعودی"
    elif score <= -15:
        direction = "تمایل نزولی"
    else:
        direction = "خنثی؛ جهت مشخصی دیده نمی‌شود"

    confidence = "متوسط" if len(signals) >= 4 else "پایین" if len(signals) >= 2 else "بسیار پایین"
    valid_scores = [value for value, _ in signals]
    aligned = len(valid_scores) >= 3 and (
        all(value > 8 for value in valid_scores) or all(value < -8 for value in valid_scores)
    )
    if aligned and confidence == "متوسط":
        horizon = "اگر شرایط فعلی حفظ شود، ادامه جهت غالب برای چند روز تا حدود یک هفته محتمل است؛ این سناریو باید روزانه بازبینی شود."
    else:
        horizon = "با داده‌های فعلی مدت روند قابل تخمین قابل اتکا نیست؛ شاخص‌ها هم‌جهتی کافی ندارند."

    fear_greed = market.get("fear_greed")
    if fear_greed:
        value = fear_greed["value"]
        fear_greed["interpretation"] = (
            "ترس شدید" if value <= 20 else "ترس" if value <= 40 else
            "خنثی" if value <= 60 else "طمع" if value <= 80 else "طمع شدید"
        )

    important_news = [item for item in news.get("items", []) if item["score"] >= 70][:7]
    critical_news = [item for item in important_news if item["level"] == "بحرانی"][:5]
    return {
        "market": market, "direction": direction, "score": score,
        "confidence": confidence, "horizon": horizon, "factors": factors,
        "network": market.get("bitcoin_network", {}), "news": news,
        "important_news": important_news, "critical_news": critical_news,
    }
