from market_data import get_market_snapshot
from news import fetch_news
from technical_analysis import analyze_market


def _number(value):
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _score(change, multiplier):
    value = _number(change)
    if value is None:
        return None
    return max(-100, min(100, round(value * multiplier)))


def _interpret(change, positive, negative, neutral="تغییر معناداری دیده نمی‌شود"):
    value = _number(change)
    if value is None:
        return "داده معتبر در دسترس نیست"
    if value > 0.15:
        return positive
    if value < -0.15:
        return negative
    return neutral


def _flow_detail(value):
    amount = _number(value)
    if amount is None:
        return "داده جریان ETF در دسترس نیست"
    if abs(amount) < 1:
        return "ورود و خروج پول ETF تقریباً متعادل بوده"
    if amount > 0:
        return "در بازه بررسی‌شده پول خالص وارد ETFها شده"
    return "در بازه بررسی‌شده پول خالص از ETFها خارج شده"


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
        _interpret(cap_change, "ارزش کل بازار در ۲۴ ساعت رشد کرده",
                   "ارزش کل بازار در ۲۴ ساعت افت کرده"), 2)

    btc = (market.get("coins") or {}).get("bitcoin") or {}
    btc_week = btc.get("change_7d")
    add("روند هفتگی بیت‌کوین", btc_week, 4,
        _interpret(btc_week, "قیمت بیت‌کوین در هفته اخیر رشد داشته",
                   "قیمت بیت‌کوین در هفته اخیر افت داشته"), 2)

    stable = market.get("stablecoins") or {}
    stable_week = stable.get("change_7d")
    add("عرضه استیبل‌کوین‌ها", stable_week, 35,
        _interpret(stable_week,
                   "عرضه استیبل‌کوین‌ها بیشتر شده؛ ظرفیت بالقوه نقدینگی بازار افزایش یافته",
                   "عرضه استیبل‌کوین‌ها کمتر شده؛ ظرفیت بالقوه نقدینگی کاهش یافته",
                   "عرضه استیبل‌کوین‌ها تقریباً ثابت بوده"), 1)

    tvl = market.get("defi_tvl") or {}
    tvl_week = tvl.get("change_7d")
    add("سرمایه قفل‌شده دیفای (TVL)", tvl_week, 8,
        _interpret(tvl_week, "TVL دیفای افزایش یافته",
                   "TVL دیفای کاهش یافته",
                   "TVL دیفای تقریباً ثابت بوده؛ تغییر آن به‌تنهایی جهت بازار را مشخص نمی‌کند"), 1)

    etf = market.get("etf_flows") or {}
    btc_etf = (etf.get("assets") or {}).get("BTC") or {}
    btc_etf_week = btc_etf.get("weekly_usd_m")
    add("جریان خالص هفتگی ETF بیت‌کوین", btc_etf_week, 0.12,
        _flow_detail(btc_etf_week), 2)

    network = market.get("bitcoin_network") or {}
    transactions = network.get("n-transactions") or {}
    tx_change = transactions.get("change_7d")
    add("تعداد تراکنش‌های شبکه بیت‌کوین", tx_change, 3,
        _interpret(tx_change, "فعالیت ثبت‌شده شبکه بیشتر شده",
                   "فعالیت ثبت‌شده شبکه کمتر شده",
                   "تغییر فعالیت شبکه ناچیز است؛ این شاخص به‌تنهایی نشانه خرید یا فروش نیست"), 1)

    hashrate = network.get("hash-rate") or {}
    hash_change = hashrate.get("change_7d")
    add("هش‌ریت شبکه بیت‌کوین", hash_change, 3,
        _interpret(hash_change, "قدرت محاسباتی و امنیت اقتصادی شبکه افزایش یافته",
                   "قدرت محاسباتی شبکه کاهش یافته",
                   "هش‌ریت تقریباً ثابت است؛ این شاخص بیشتر وضعیت امنیت شبکه را نشان می‌دهد"), 1)

    try:
        technical = analyze_market()
    except Exception as exc:
        technical = {"available": False, "assets": {}, "errors": [str(exc)]}

    btc_technical = (technical.get("assets") or {}).get("bitcoin") or {}
    technical_score = btc_technical.get("score")
    add(
        "تحلیل تکنیکال چندتایم‌فریمی بیت‌کوین",
        technical_score,
        1,
        "اجماع تایم‌فریم‌ها: " + str(btc_technical.get("signal", "داده کافی نیست")),
        2,
    )

    score = None
    if len(signals) >= 2:
        total_weight = sum(weight for _, weight in signals)
        score = round(sum(value * weight for value, weight in signals) / total_weight)

    if score is None or len(signals) < 2:
        direction = "داده کافی نیست"
    elif score >= 15:
        direction = "تمایل صعودی"
    elif score <= -15:
        direction = "تمایل نزولی"
    else:
        direction = "خنثی؛ جهت مشخصی دیده نمی‌شود"

    coverage = len(signals)
    confidence = "بالا" if coverage >= 6 else "متوسط" if coverage >= 4 else "پایین"
    values = [value for value, _ in signals]
    bullish = sum(1 for value in values if value > 8)
    bearish = sum(1 for value in values if value < -8)
    if coverage >= 5 and max(bullish, bearish) >= 4 and abs(score or 0) >= 20:
        horizon = (
            "سناریوی محتمل: جهت غالب ممکن است حدود ۳ تا ۷ روز ادامه پیدا کند؛ "
            "این فقط برآورد مشروط به حفظ شرایط فعلی است و باید با گزارش‌های بعدی بازبینی شود."
        )
    elif coverage >= 3:
        horizon = (
            "فعلاً برای تعیین تعداد روزهای ادامه روند هم‌جهتی کافی بین شاخص‌ها وجود ندارد. "
            "گزارش بعدی می‌تواند این برآورد را تغییر دهد."
        )
    else:
        horizon = "داده کافی برای تخمین مدت روند نداریم؛ از اعلام تعداد روز به‌صورت حدسی خودداری می‌کنیم."

    fear_greed = market.get("fear_greed")
    if fear_greed:
        value = fear_greed.get("value")
        if value is not None:
            fear_greed["interpretation"] = (
                "ترس شدید" if value <= 20 else "ترس" if value <= 40 else
                "حالت خنثی" if value <= 60 else "طمع" if value <= 80 else "طمع شدید"
            )

    items = news.get("items") or []
    important_news = [item for item in items if item.get("score", 0) >= 70][:7]
    critical_news = [item for item in important_news if item.get("level") == "بحرانی"][:5]
    market["data_quality"] = {
        "available_factors": coverage,
        "total_factors": len(factors),
        "errors": len(market.get("errors") or []),
    }

    return {
        "market": market,
        "technical": technical,
        "direction": direction,
        "score": score,
        "confidence": confidence,
        "horizon": horizon,
        "factors": factors,
        "network": network,
        "news": news,
        "important_news": important_news,
        "critical_news": critical_news,
    }
