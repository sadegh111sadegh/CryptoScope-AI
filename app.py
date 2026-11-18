import streamlit as st
import pandas as pd
from analysis import build_report

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
    st.markdown(f'<div class="panel"><h2>جهت بازار: {report["direction"]}</h2><h3>امتیاز: {report["score"] if report["score"] is not None else "ناموجود"} از ۱۰۰</h3><p>اطمینان: {report["confidence"]}</p><p>{report["horizon"]}</p></div>',unsafe_allow_html=True)
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
            for sym,flow in (etf.get("assets") or {}).items():
                if flow:st.write(f'{sym}: روزانه {flow["daily_usd_m"]:+.1f}M USD | هفت‌روزه {flow["weekly_usd_m"]:+.1f}M USD')
        else:st.info("جریان ETF دریافت نشده است.")
    st.subheader("آنچین بیت‌کوین")
    for name,key in (("تراکنش‌ها","n-transactions"),("هش‌ریت","hash-rate")):
        item=(report.get("network") or {}).get(key)
        st.write(f'{name}: تغییر ۷ روزه {pct(item.get("change_7d"))}' if item else f'{name}: داده موجود نیست')
    st.subheader("خبرهای مهم ۴۸ ساعت اخیر")
    news=report.get("news") or {}
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
