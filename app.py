import streamlit as st
import pandas as pd
from analysis import build_report
from backtest import run_market_backtest

st.set_page_config(page_title="CryptoScope AI", page_icon="📡", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');
html,body,[class*="css"]{font-family:Vazirmatn,sans-serif;direction:rtl}
.stApp{background:#080d18;color:#e5e7eb}.block-container{max-width:1450px}
.hero,.panel,.metric{background:#101b2c;border:1px solid #26364f;border-radius:16px;padding:18px;margin:12px 0}
.hero{background:linear-gradient(120deg,#14233c,#172554)}
.metric-title{color:#9fb2cc;font-size:13px}.metric-value{font-size:23px;font-weight:800;color:white}
</style>
""", unsafe_allow_html=True)

def money(v):
    if v is None:return "ناموجود"
    v=float(v)
    for threshold,unit in ((1e12,"T"),(1e9,"B"),(1e6,"M")):
        if abs(v)>=threshold:return f"${v/threshold:.2f} {unit}"
    return f"${v:,.2f}"

def pct(v): return "ناموجود" if v is None else f"{float(v):+.2f}%"

st.markdown('<div class="hero"><h1>📡 CryptoScope AI</h1><p>تحلیل آنچین، فاندامنتال، جریان سرمایه و اخبار بازار رمزارز</p></div>',unsafe_allow_html=True)
if st.button("🔄 دریافت آخرین تحلیل"):
    st.cache_data.clear()
try:
    with st.spinner("در حال دریافت داده‌ها و ساخت تحلیل..."):
        report=build_report()
    market=report.get("market") or {}
    glob=market.get("global") or {}
    quality=market.get("data_quality") or {}
    st.markdown(f'<div class="panel"><h2>جهت بازار: {report["direction"]}</h2><h3>امتیاز: {report["score"] if report["score"] is not None else "ناموجود"} از ۱۰۰</h3><p>اطمینان: {report["confidence"]} | شاخص معتبر: {quality.get("available_factors", 0)} از {quality.get("total_factors", 0)}</p><p>{report["horizon"]}</p></div>',unsafe_allow_html=True)
    st.subheader("هوشمندی بازار و سناریوها")
    regime = report.get("market_regime") or {}
    forecast = report.get("forecast") or {}
    r1, r2, r3 = st.columns(3)
    r1.metric("رژیم بازار", regime.get("label", "نامشخص"))
    r2.metric("وضعیت نوسان", regime.get("volatility_state", "نامشخص"))
    r3.metric("اطمینان مدل", report.get("confidence", "در حال ارزیابی"))
    if forecast.get("available"):
        probs = forecast.get("probabilities") or {}
        p1, p2, p3 = st.columns(3)
        p1.metric("سناریوی صعودی", f'{probs.get("up", 0):.1f}%')
        p2.metric("سناریوی نزولی", f'{probs.get("down", 0):.1f}%')
        p3.metric("سناریوی خنثی", f'{probs.get("neutral", 0):.1f}%')
        st.caption(f'روش: {forecast.get("method")} | کالیبره‌شده: {"بله" if forecast.get("calibrated") else "خیر"} | {forecast.get("note", "")}')
    if report.get("divergences"):
        for item in report["divergences"]:
            st.warning(f'{item.get("name")}: {item.get("detail")}')
    perf = report.get("forecast_performance") or {}
    st.caption(f'پیش‌بینی‌های ارزیابی‌شده: {perf.get("settled", 0)} | در انتظار: {perf.get("pending", 0)} | دقت جهت: {perf.get("directional_accuracy") if perf.get("directional_accuracy") is not None else "هنوز داده کافی نیست"} | Brier: {perf.get("brier_score") if perf.get("brier_score") is not None else "—"}')
    cards=[("ارزش کل بازار",money(glob.get("market_cap"))),("حجم ۲۴ ساعته",money(glob.get("volume_24h"))),("تغییر ارزش بازار",pct(glob.get("market_cap_change_24h"))),("دامیننس BTC",pct(glob.get("btc_dominance")))]
    cols=st.columns(4)
    for c,(name,value) in zip(cols,cards):
        with c: st.markdown(f'<div class="metric"><div class="metric-title">{name}</div><div class="metric-value">{value}</div></div>',unsafe_allow_html=True)
    st.subheader("ارزهای اصلی")
    coin_rows=[]
    for key in ("bitcoin","ethereum","solana"):
        coin=(market.get("coins") or {}).get(key)
        if coin:coin_rows.append({"ارز":coin.get("name"),"قیمت":money(coin.get("price")),"تغییر ۲۴ ساعت":pct(coin.get("change_24h")),"تغییر ۷ روز":pct(coin.get("change_7d"))})
    if coin_rows:st.dataframe(pd.DataFrame(coin_rows),use_container_width=True,hide_index=True)
    st.subheader("تحلیل تکنیکال چندتایم‌فریمی")
    technical = report.get("technical") or {}
    if technical.get("available"):
        for asset_id in ("bitcoin", "ethereum", "solana"):
            asset = (technical.get("assets") or {}).get(asset_id) or {}
            if asset.get("score") is None:
                continue
            st.markdown(f"**{asset.get('name', asset_id)} — {asset.get('signal')} — امتیاز {asset['score']}/100**")
            rows = []
            for interval in ("1d", "4h", "1h"):
                item = (asset.get("timeframes") or {}).get(interval)
                if item:
                    rows.append({
                        "تایم‌فریم": interval,
                        "وضعیت": item.get("signal"),
                        "RSI": round(item["rsi14"], 1) if item.get("rsi14") is not None else "ناموجود",
                        "EMA 20": round(item["ema20"], 2),
                        "EMA 50": round(item["ema50"], 2),
                        "EMA 200": round(item["ema200"], 2),
                        "ATR 14": round(item["atr14"], 2) if item.get("atr14") is not None else "ناموجود",
                        "نسبت حجم": round(item["volume_ratio"], 2) if item.get("volume_ratio") is not None else "ناموجود",
                    })
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("داده تکنیکال کافی از صرافی دریافت نشد؛ تحلیل تکنیکال موقتاً در دسترس نیست.")

    st.subheader("بک‌تست استراتژی تاریخی")
    st.caption("این آزمایش روی کندل‌های بسته‌شده انجام می‌شود؛ ورود در بازشدن کندل بعدی است و کارمزد و لغزش قیمت لحاظ می‌شوند.")
    bt1, bt2, bt3 = st.columns(3)
    with bt1:
        bt_symbol = st.selectbox("دارایی", ["BTCUSDT", "ETHUSDT", "SOLUSDT"], key="bt_symbol")
    with bt2:
        bt_interval = st.selectbox("تایم‌فریم", ["1h", "4h", "1d"], index=1, key="bt_interval")
    with bt3:
        bt_fee = st.number_input("کارمزد هر سمت (%)", min_value=0.0, max_value=1.0, value=0.1, step=0.01, key="bt_fee")
    if st.button("اجرای بک‌تست", key="run_backtest"):
        try:
            with st.spinner("دریافت کندل‌های تاریخی و اجرای بک‌تست..."):
                bt = run_market_backtest(
                    symbol=bt_symbol,
                    interval=bt_interval,
                    limit=1000,
                    fee_rate=bt_fee / 100,
                    slippage_rate=0.05 / 100,
                )
            st.markdown(f"**{bt_symbol} | {bt_interval} | {bt['candles']} کندل بسته‌شده**")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("بازده استراتژی", f"{bt['return_pct']:+.2f}%")
            m2.metric("بازده خرید و نگهداری", f"{bt['buy_hold_return_pct']:+.2f}%")
            m3.metric("بیشترین افت سرمایه", f"{bt['max_drawdown_pct']:.2f}%")
            m4.metric("تعداد معاملات", str(bt["trades"]))
            m5, m6, m7 = st.columns(3)
            m5.metric("درصد معاملات سودده", f"{bt['win_rate_pct']:.1f}%")
            pf = bt["profit_factor"]
            m6.metric("Profit Factor", "∞" if pf == float("inf") else f"{pf:.2f}" if pf is not None else "—")
            m7.metric("سرمایه نهایی", money(bt["final_balance"]))
            curve = pd.DataFrame(bt["equity_curve"])
            if not curve.empty:
                curve["زمان"] = pd.to_datetime(curve["time"], unit="ms", utc=True)
                st.line_chart(curve.set_index("زمان")["equity"])
            if bt["trades_detail"]:
                trades_df = pd.DataFrame(bt["trades_detail"])
                trades_df["نتیجه"] = trades_df["pnl"].map(lambda x: "سود" if x > 0 else "ضرر" if x < 0 else "سر به سر")
                st.dataframe(trades_df[["entry_price", "exit_price", "pnl", "return_pct", "reason", "نتیجه"]], use_container_width=True, hide_index=True)
            else:
                st.info("در بازه انتخاب‌شده هیچ معامله‌ای مطابق شرایط استراتژی ایجاد نشد.")
            st.caption("فرض‌ها: استراتژی خرید نقدی و بدون اهرم؛ کارمزد و لغزش در ورود و خروج؛ اگر حد ضرر و هدف در یک کندل لمس شوند، حد ضرر مقدم است. عملکرد گذشته تضمین آینده نیست.")
        except Exception as bt_exc:
            st.error("بک‌تست اجرا نشد: " + str(bt_exc))

    st.subheader("شاخص‌های تحلیل")
    for f in report.get("factors",[]):
        st.markdown(f'**{f["name"]}** — امتیاز: {f["score"] if f["score"] is not None else "بدون داده"}')
        st.write(f["detail"])
    a,b=st.columns(2)
    with a:
        st.subheader("ترس و طمع")
        fg=market.get("fear_greed")
        if fg:st.metric("Fear & Greed",f'{fg["value"]}/100',fg.get("interpretation",fg.get("label","")))
        else:st.info("داده ترس و طمع در دسترس نیست.")
        st.subheader("عرضه استیبل‌کوین‌ها")
        stable=market.get("stablecoins")
        if stable:st.write(f'۷ روز: {pct(stable.get("change_7d"))} | ۳۰ روز: {pct(stable.get("change_30d"))}')
        else:st.info("داده عرضه استیبل‌کوین در دسترس نیست.")
    with b:
        st.subheader("TVL دیفای")
        tvl=market.get("defi_tvl")
        if tvl:st.write(f'۷ روز: {pct(tvl.get("change_7d"))} | ۳۰ روز: {pct(tvl.get("change_30d"))}')
        else:st.info("داده TVL در دسترس نیست.")
        st.subheader("جریان ETF")
        etf=market.get("etf_flows") or {}
        if etf.get("available"):
            st.caption(f'منبع: {etf.get("source", "نامشخص")} | به‌روزرسانی: {etf.get("updated_at", "نامشخص")}')
            for sym,flow in (etf.get("assets") or {}).items():
                if flow:st.write(f'{sym} ({flow.get("date", "بدون تاریخ")}): روزانه {flow["daily_usd_m"]:+.1f}M USD | هفت‌روزه {flow["weekly_usd_m"]:+.1f}M USD')
        else:st.info("جریان ETF دریافت نشده است.")
    st.subheader("آنچین بیت‌کوین")
    for name,key in (("تراکنش‌ها","n-transactions"),("هش‌ریت","hash-rate")):
        item=(report.get("network") or {}).get(key)
        if item:
            st.write(f'{name}: تغییر ۷ روزه {pct(item.get("change_7d"))} | آخرین داده: {item.get("latest", "ناموجود")} | تاریخ: {item.get("latest_date", "نامشخص")}')
        else:
            st.write(f'{name}: داده موجود نیست')
    st.subheader("خبرهای مهم ۴۸ ساعت اخیر")
    news=report.get("news") or {}
    st.caption(f'منابع خبری پاسخ‌داده: {news.get("feeds_ok", 0)} از {news.get("feeds_total", 0)} | بررسی: {news.get("checked_at", "نامشخص")}')
    if not news.get("available"):st.warning("دریافت از منابع خبری ناموفق بود؛ نبود خبر مهم قابل نتیجه‌گیری نیست.")
    elif report.get("important_news"):
        for item in report["important_news"]:
            st.markdown(f'**{item["level"]} | {item["category"]} | {item["title"]}**')
            st.caption(item.get("source",""))
            st.markdown(f'[مشاهده خبر]({item["url"]})')
            st.divider()
    else:st.info("خبر مهمی با معیارهای فعلی شناسایی نشد.")
    if market.get("errors"):
        with st.expander("خطاها و منابع ناموفق"):
            for err in market["errors"]:st.write("• "+str(err))
except Exception as exc:
    st.error("اجرای تحلیل با خطا مواجه شد.")
    st.exception(exc)
st.caption("CryptoScope AI | تحلیل سناریویی است و توصیه خرید یا فروش محسوب نمی‌شود.")
