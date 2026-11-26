"""Market regime and cross-factor divergence diagnostics."""
from math import isfinite


def number(value):
    try:
        value = float(value)
        return value if isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _timeframe_direction(item):
    """Return a direction only when EMA structure, slopes and ADX align."""
    if not item:
        return 0
    price = number(item.get("price"))
    ema20 = number(item.get("ema20"))
    ema50 = number(item.get("ema50"))
    ema200 = number(item.get("ema200"))
    slope20 = number(item.get("ema20_slope_pct"))
    slope50 = number(item.get("ema50_slope_pct"))
    adx = number(item.get("adx14"))
    if any(value is None for value in (price, ema20, ema50, ema200, slope20, slope50, adx)):
        return 0
    if price > ema20 > ema50 > ema200 and slope20 > 0 and slope50 > 0 and adx >= 18:
        return 1
    if price < ema20 < ema50 < ema200 and slope20 < 0 and slope50 < 0 and adx >= 18:
        return -1
    return 0


def detect_market_regime(market, technical):
    """Classify BTC from daily structure, 4h confirmation, ADX and range width."""
    assets = technical.get("assets") or {}
    btc = assets.get("bitcoin") or {}
    timeframes = btc.get("timeframes") or {}
    daily = timeframes.get("1d") or {}
    four_hour = timeframes.get("4h") or {}

    daily_direction = _timeframe_direction(daily)
    four_hour_direction = _timeframe_direction(four_hour)
    daily_adx = number(daily.get("adx14"))
    range_width = number(daily.get("range_width_pct"))
    atr_pct = number(daily.get("atr_pct"))
    tech_score = number(btc.get("score"))

    evidence = []
    if daily_adx is not None:
        evidence.append(f"ADX روزانه: {daily_adx:.1f}")
    if range_width is not None:
        evidence.append(f"پهنای محدوده ۲۰ روزه: {range_width:.1f}%")
    if atr_pct is not None:
        evidence.append(f"ATR روزانه نسبت به قیمت: {atr_pct:.2f}%")
    if daily_direction:
        evidence.append("ساختار EMA و شیب روزانه: " + ("صعودی" if daily_direction > 0 else "نزولی"))
    elif daily:
        evidence.append("ساختار EMA روزانه: هم‌راستایی روند تأیید نشد")
    if four_hour_direction:
        evidence.append("تأیید ۴ ساعته: " + ("صعودی" if four_hour_direction > 0 else "نزولی"))
    elif four_hour:
        evidence.append("تأیید ۴ ساعته: هم‌جهت با روند روزانه نیست یا قدرت کافی ندارد")

    if not daily or daily_adx is None or range_width is None:
        label, trend = "نامشخص", "نامشخص"
        evidence.insert(0, "داده روزانه کافی برای تشخیص ساختار بازار وجود ندارد")
    elif daily_direction == 1 and four_hour_direction == 1:
        label, trend = "روند صعودی", "صعودی"
    elif daily_direction == -1 and four_hour_direction == -1:
        label, trend = "روند نزولی", "نزولی"
    elif daily_adx < 18 and range_width <= 12 and four_hour_direction == 0:
        label, trend = "بازار رنج", "خنثی"
        evidence.append("قدرت روند پایین و محدوده نوسان ۲۰ روزه فشرده است")
    elif daily_direction == 1 and four_hour_direction == -1:
        label, trend = "اصلاح در ساختار بزرگ‌تر صعودی", "ترکیبی"
    elif daily_direction == -1 and four_hour_direction == 1:
        label, trend = "بازگشت احتمالی در ساختار بزرگ‌تر نزولی", "ترکیبی"
    else:
        label, trend = "گذار یا عدم‌قطعیت", "ترکیبی"

    volatility = (
        "بالا" if atr_pct is not None and atr_pct >= 5 else
        "متوسط" if atr_pct is not None and atr_pct >= 2 else
        "پایین" if atr_pct is not None else "نامشخص"
    )
    return {
        "label": label,
        "trend": trend,
        "volatility_state": volatility,
        "technical_score": tech_score,
        "evidence": evidence or ["شواهد تکنیکال کافی در دسترس نیست"],
    }


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
