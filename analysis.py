from market_data import get_market_snapshot
from news import fetch_news
from technical_analysis import analyze_market
from intelligence import detect_market_regime, detect_divergences, number as _number
from forecasting import forecast_scenarios
from adaptive_weights import calculate_adaptive_weights
from signal_tracker import (
    DEFAULT_PATH, load_history, save_history, settle_forecasts,
    record_forecast, performance_summary,
)


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


def build_report(history_path=DEFAULT_PATH):
    market = get_market_snapshot()
    news = fetch_news()
    factors, signals = [], []

    def add(name, change, multiplier, detail, weight=1):
        score = _score(change, multiplier)
        factors.append({"name": name, "score": score, "detail": detail, "base_weight": weight})
        if score is not None:
            signals.append((name, score, weight))

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
                   "عرضه استیبل‌کوین‌ها تقریباً ثابت بوده؛ تغییر آن به‌تنهایی جهت بازار را مشخص نمی‌کند"), 1)

    tvl = market.get("defi_tvl") or {}
    tvl_week = tvl.get("change_7d")
    add("سرمایه قفل‌شده دیفای (TVL)", tvl_week, 8,
        _interpret(tvl_week, "TVL دیفای افزایش یافته",
                   "TVL دیفای کاهش یافته",
                   "TVL دیفای تقریباً ثابت بوده؛ این شاخص به‌تنهایی جهت بازار را مشخص نمی‌کند"), 1)

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

    # Mature old forecasts before calculating weights, so only realized outcomes
    # can influence future reports.
    history = load_history(history_path)
    current_price = _number(btc.get("price"))
    history = settle_forecasts(history, current_price)
    adaptive = calculate_adaptive_weights(history)
    weighted = []
    factor_scores = {}
    for name, value, base_weight in signals:
        learned_weight = adaptive["weights"].get(name, 1.0)
        effective_weight = base_weight * learned_weight
        weighted.append((value, effective_weight))
        factor_scores[name] = value
    score = None
    if len(weighted) >= 2:
        total_weight = sum(weight for _, weight in weighted)
        score = round(sum(value * weight for value, weight in weighted) / total_weight)

    if score is None or len(weighted) < 2:
        direction = "داده کافی نیست"
    elif score >= 15:
        direction = "تمایل صعودی"
    elif score <= -15:
        direction = "تمایل نزولی"
    else:
        direction = "خنثی؛ جهت مشخصی دیده نمی‌شود"

    regime = detect_market_regime(market, technical)
    divergences = detect_divergences(market, technical)
    forecast = forecast_scenarios(score, regime, divergences, len(weighted), 24)
    if current_price is not None and forecast.get("available"):
        history = record_forecast(history, current_price, forecast, factor_scores)
    save_history(history, history_path)
    performance = performance_summary(history)

    # Until enough matured out-of-sample observations exist, do not call the
    # directional forecast highly confident.
    if performance["settled"] >= 30 and performance["directional_accuracy"] is not None:
        confidence = "بالا" if performance["directional_accuracy"] >= 60 else "متوسط" if performance["directional_accuracy"] >= 52 else "پایین"
    else:
        confidence = "در حال ارزیابی"
    coverage = len(weighted)

    if coverage >= 5 and score is not None and abs(score) >= 20:
        horizon = (
            "سناریوی جهت‌دار فعلی صرفاً برای افق کوتاه‌مدت بررسی می‌شود؛ "
            "برای افق چندروزه باید داده و تأیید مستقل بیشتری فراهم شود."
        )
    elif coverage >= 3:
        horizon = "هم‌جهتی شاخص‌ها برای برآورد مطمئن ادامه روند کافی نیست."
    else:
        horizon = "داده کافی برای تخمین مدت روند نداریم."

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
    for factor in factors:
        factor["adaptive_weight"] = adaptive["weights"].get(factor["name"], 1.0)

    return {
        "market": market, "technical": technical, "direction": direction,
        "score": score, "confidence": confidence, "horizon": horizon,
        "factors": factors, "network": network, "news": news,
        "important_news": important_news, "critical_news": critical_news,
        "market_regime": regime, "divergences": divergences,
        "forecast": forecast, "forecast_performance": performance,
        "adaptive_weights": adaptive, "forecast_history_path": history_path,
    }
