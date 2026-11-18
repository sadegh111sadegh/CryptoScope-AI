
from market_data import get_market_snapshot
from news import fetch_news


def clamp(x):
    return max(-100, min(100, round(x)))


def trend_score(change, multiplier=8):
    if change is None:
        return None
    return clamp(change * multiplier)


def build_report():
    market = get_market_snapshot()
    news = fetch_news()

    factors = []
    scores = []

    def add(name, score, detail, weight=1):
        factors.append({
            "name": name,
            "score": score,
            "detail": detail
        })
        if score is not None:
            scores.extend([score] * weight)

    # Broad market fundamentals
    global_data = market.get("global", {})
    cap_change = global_data.get("market_cap_change_24h")

    add(
        "ارزش کل بازار",
        trend_score(cap_change, 5),
        f"تغییر ۲۴ ساعته: {cap_change:.2f}%"
        if cap_change is not None else "داده در دسترس نیست",
        2
    )

    # Stablecoin supply
    stable = market.get("stablecoins")
    if stable:
        stable_score = trend_score(stable.get("change_7d"), 10)
        add(
            "عرضه استیبل‌کوین‌ها",
            stable_score,
            f"۷ روزه: {stable.get('change_7d')}% | ۳۰ روزه: {stable.get('change_30d')}%",
            2
        )
    else:
        add("عرضه استیبل‌کوین‌ها", None, "داده در دسترس نیست")

    # DeFi TVL
    tvl = market.get("defi_tvl")
    if tvl:
        tvl_score = trend_score(tvl.get("change_7d"), 8)
        add(
            "ارزش قفل‌شده دیفای (TVL)",
            tvl_score,
            f"۷ روزه: {tvl.get('change_7d')}% | ۳۰ روزه: {tvl.get('change_30d')}%",
            2
        )
    else:
        add("ارزش قفل‌شده دیفای", None, "داده در دسترس نیست")

    # Bitcoin network activity
    network = market.get("bitcoin_network", {})
    tx = network.get("n-transactions")
    if tx:
        add(
            "فعالیت شبکه بیت‌کوین",
            trend_score(tx.get("change_7d"), 8),
            f"تغییر تراکنش‌ها در ۷ روز: {tx.get('change_7d')}%"
        )
    else:
        add("فعالیت شبکه بیت‌کوین", None, "داده در دسترس نیست")

    # Bitcoin hashrate: network security / miner participation proxy
    hr = network.get("hash-rate")
    if hr:
        add(
            "قدرت شبکه بیت‌کوین",
            trend_score(hr.get("change_7d"), 8),
            f"تغییر هش‌ریت در ۷ روز: {hr.get('change_7d')}%"
        )
    else:
        add("قدرت شبکه بیت‌کوین", None, "داده در دسترس نیست")

    # Sentiment is a secondary indicator
    fg = market.get("fear_greed")
    if fg:
        fg_score = clamp((fg["value"] - 50) * 1.2)
        add(
            "احساسات بازار",
            fg_score,
            f'{fg["value"]}/100 - {fg["label"]}'
        )
    else:
        add("احساسات بازار", None, "داده در دسترس نیست")

    # BTC price is context, not technical analysis
    btc = market.get("coins", {}).get("bitcoin", {})
    btc_change = btc.get("change_7d")
    add(
        "عملکرد هفتگی بیت‌کوین",
        trend_score(btc_change, 5),
        f"تغییر ۷ روزه: {btc_change}%"
        if btc_change is not None else "داده در دسترس نیست"
    )

    score = round(sum(scores) / len(scores)) if scores else None

    if score is None:
        direction = "نامشخص"
    elif score >= 20:
        direction = "تمایل صعودی"
    elif score <= -20:
        direction = "تمایل نزولی"
    else:
        direction = "خنثی / بدون جهت روشن"

    available = sum(1 for f in factors if f["score"] is not None)
    confidence = (
        "متوسط" if available >= 5
        else "پایین" if available >= 3
        else "بسیار پایین"
    )

    # Estimate horizon only when independent liquidity indicators agree
    stable_change = (stable or {}).get("change_7d")
    tvl_change = (tvl or {}).get("change_7d")

    aligned = (
        stable_change is not None and tvl_change is not None
        and stable_change * tvl_change > 0
    )

    if score is not None and abs(score) >= 25 and aligned and available >= 5:
        horizon = "حدود ۱ تا ۳ هفته؛ تخمین مشروط با اطمینان متوسط رو به پایین"
    elif score is not None and abs(score) >= 20 and available >= 4:
        horizon = "احتمالاً چند روز؛ برای تخمین طولانی‌تر شواهد کافی نیست"
    else:
        horizon = "فعلاً قابل تخمین نیست؛ شاخص‌ها هم‌جهتی کافی ندارند"

    # Important headlines are risk context, not automatic bearish signals
    important_news = [
        item for item in news.get("items", [])
        if item["score"] >= 70
    ][:7]

    critical_news = [
        item for item in news.get("items", [])
        if item["level"] == "بحرانی"
    ][:5]

    return {
        "market": market,
        "direction": direction,
        "score": score,
        "confidence": confidence,
        "horizon": horizon,
        "factors": factors,
        "news": news,
        "important_news": important_news,
        "critical_news": critical_news
    }
