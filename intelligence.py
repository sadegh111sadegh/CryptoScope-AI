"""Market regime and cross-factor divergence diagnostics."""
from math import isfinite


def number(value):
    try:
        value = float(value)
        return value if isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _sign(value, threshold=0.0):
    value = number(value)
    if value is None or abs(value) <= threshold:
        return 0
    return 1 if value > 0 else -1


def detect_market_regime(market, technical):
    btc = (market.get("coins") or {}).get("bitcoin") or {}
    daily = number(btc.get("change_24h"))
    weekly = number(btc.get("change_7d"))
    asset = (technical.get("assets") or {}).get("bitcoin") or {}
    tech_score = number(asset.get("score"))
    if weekly is None and tech_score is None:
        return {"label": "نامشخص", "trend": "نامشخص", "volatility_state": "نامشخص",
                "evidence": ["داده کافی برای تشخیص رژیم بازار وجود ندارد"]}
    score = (weekly or 0) * 0.55 + (daily or 0) * 0.15 + (tech_score or 0) * 0.035
    if score >= 2.5:
        label, trend = "روند صعودی", "صعودی"
    elif score <= -2.5:
        label, trend = "روند نزولی", "نزولی"
    elif weekly is not None and abs(weekly) < 2 and (tech_score is None or abs(tech_score) < 25):
        label, trend = "بازار رنج", "خنثی"
    elif weekly is not None and weekly > 0 and tech_score is not None and tech_score < -25:
        label, trend = "اصلاح در ساختار بزرگ‌تر صعودی", "ترکیبی"
    elif weekly is not None and weekly < 0 and tech_score is not None and tech_score > 25:
        label, trend = "بازگشت احتمالی در ساختار بزرگ‌تر نزولی", "ترکیبی"
    else:
        label, trend = "گذار یا عدم‌قطعیت", "ترکیبی"
    abs_daily = abs(daily) if daily is not None else None
    volatility = "بالا" if abs_daily is not None and abs_daily >= 5 else "متوسط" if abs_daily is not None and abs_daily >= 2 else "پایین/نامشخص"
    evidence = []
    if weekly is not None:
        evidence.append(f"تغییر هفتگی BTC: {weekly:+.2f}%")
    if daily is not None:
        evidence.append(f"تغییر ۲۴ ساعته BTC: {daily:+.2f}%")
    if tech_score is not None:
        evidence.append(f"امتیاز تکنیکال چندتایم‌فریمی: {tech_score:+.0f}")
    return {"label": label, "trend": trend, "volatility_state": volatility, "raw_score": round(score, 3), "evidence": evidence}


def detect_divergences(market, technical):
    findings = []
    btc = (market.get("coins") or {}).get("bitcoin") or {}
    price_week = number(btc.get("change_7d"))
    etf = (market.get("etf_flows") or {}).get("assets") or {}
    btc_etf = etf.get("BTC") or {}
    flow = number(btc_etf.get("weekly_usd_m"))
    stable = number((market.get("stablecoins") or {}).get("change_7d"))
    tech = number(((technical.get("assets") or {}).get("bitcoin") or {}).get("score"))

    if price_week is not None and flow is not None:
        if price_week > 1 and flow < -25:
            findings.append({"type": "bearish", "name": "قیمت در برابر جریان ETF", "detail": "قیمت هفتگی مثبت است اما جریان خالص ETF منفی است؛ احتمال واگرایی تقاضا وجود دارد."})
        elif price_week < -1 and flow > 25:
            findings.append({"type": "bullish", "name": "قیمت در برابر جریان ETF", "detail": "قیمت هفتگی منفی است اما جریان خالص ETF مثبت است؛ احتمال جذب عرضه وجود دارد."})
    if price_week is not None and stable is not None:
        if price_week > 1 and stable < -0.5:
            findings.append({"type": "bearish", "name": "قیمت در برابر عرضه استیبل‌کوین", "detail": "قیمت رشد کرده ولی عرضه استیبل‌کوین‌ها کاهش یافته است؛ پشتوانه نقدینگی را با احتیاط بسنجید."})
        elif price_week < -1 and stable > 0.5:
            findings.append({"type": "bullish", "name": "قیمت در برابر عرضه استیبل‌کوین", "detail": "قیمت افت کرده ولی عرضه استیبل‌کوین‌ها افزایش یافته است؛ ظرفیت بالقوه نقدینگی بیشتر شده است."})
    if price_week is not None and tech is not None:
        if price_week > 1 and tech < -25:
            findings.append({"type": "bearish", "name": "قیمت در برابر تکنیکال", "detail": "بازده هفتگی مثبت است اما اجماع تکنیکال منفی است."})
        elif price_week < -1 and tech > 25:
            findings.append({"type": "bullish", "name": "قیمت در برابر تکنیکال", "detail": "بازده هفتگی منفی است اما اجماع تکنیکال مثبت است."})
    return findings
