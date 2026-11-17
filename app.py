
import streamlit as st
import pandas as pd
from analysis import build_report

st.set_page_config(
    page_title="CryptoScope AI",
    page_icon="📡",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap');

html,body,[class*="css"] {
    font-family: Vazirmatn,sans-serif;
    direction: rtl;
}

.stApp {
    background: #080d18;
    color: #e5e7eb;
}

.block-container {
    max-width: 1450px;
}

.hero {
    padding: 25px;
    border-radius: 18px;
    background: linear-gradient(120deg,#14233c,#172554);
    border: 1px solid #26364f;
    margin-bottom: 20px;
}

.metric {
    background: #111d30;
    border: 1px solid #26364f;
    border-radius: 15px;
    padding: 18px;
    margin-bottom: 10px;
}

.metric-title {
    color: #9fb2cc;
    font-size: 13px;
}

.metric-value {
    font-size: 24px;
    font-weight: 800;
    color: white;
}

.panel {
    background: #101b2c;
    border: 1px solid #26364f;
    border-radius: 16px;
    padding: 18px;
    margin: 12px 0;
}

</style>
""", unsafe_allow_html=True)


def money(value):

    if value is None:
        return "ناموجود"

    if value >= 1e12:
        return f"${value / 1e12:.2f} T"

    if value >= 1e9:
        return f"${value / 1e9:.2f} B"

    if value >= 1e6:
        return f"${value / 1e6:.2f} M"

    return f"${value:,.2f}"


def percent(value):

    if value is None:
        return "ناموجود"

    return f"{value:+.2f}%"


st.markdown("""
<div class="hero">
<h1>📡 CryptoScope AI</h1>
<p>سامانه هوشمند تحلیل بازار رمزارزها</p>
</div>
""", unsafe_allow_html=True)

if st.button("🔄 به‌روزرسانی اطلاعات"):
    st.cache_data.clear()

try:

    with st.spinner("در حال دریافت اطلاعات بازار..."):

        market, direction, score, factors, headlines, high = build_report()

    st.markdown(
        f"""
        <div class="panel">
        <h2>جهت کلی بازار: {direction}</h2>
        <h3>امتیاز بازار: {score if score is not None else "ناموجود"} / 100</h3>
        </div>
        """,
        unsafe_allow_html=True
    )

    columns = st.columns(4)

    cards = [
        ("ارزش کل بازار", money(market.get("market_cap_usd"))),
        ("حجم معاملات", money(market.get("volume_24h_usd"))),
        ("تغییر بازار", percent(market.get("market_cap_change_24h_pct"))),
        ("دامیننس BTC", percent(market.get("btc_dominance")))
    ]

    for col, (title, value) in zip(columns, cards):

        with col:

            st.markdown(
                f"""
                <div class="metric">
                <div class="metric-title">{title}</div>
                <div class="metric-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown(
        '<div class="panel"><h3>🪙 ارزهای اصلی بازار</h3></div>',
        unsafe_allow_html=True
    )

    coin_rows = []

    for key in ["bitcoin", "ethereum", "cardano", "solana"]:

        coin = market.get("coins", {}).get(key)

        if coin:

            coin_rows.append({
                "ارز": coin["name"],
                "نماد": coin["symbol"],
                "قیمت": coin["price"],
                "تغییر ۱ ساعت": percent(coin.get("change_1h")),
                "تغییر ۲۴ ساعت": percent(coin.get("change_24h")),
                "تغییر ۷ روز": percent(coin.get("change_7d"))
            })

    if coin_rows:
        st.dataframe(
            pd.DataFrame(coin_rows),
            use_container_width=True,
            hide_index=True
        )

    left, right = st.columns(2)

    with left:

        st.markdown(
            '<div class="panel"><h3>📊 عوامل تحلیل بازار</h3></div>',
            unsafe_allow_html=True
        )

        for name, value, detail in factors:

            if value is None:
                status = "⚪ بدون داده"
            elif value >= 20:
                status = f"🟢 مثبت {value}"
            elif value <= -20:
                status = f"🔴 منفی {value}"
            else:
                status = f"🟡 خنثی {value}"

            st.markdown(
                f"""
                <div class="metric">
                <b>{name}</b>
                <p>{status}</p>
                <small>{detail}</small>
                </div>
                """,
                unsafe_allow_html=True
            )

    with right:

        st.markdown(
            '<div class="panel"><h3>😨 شاخص ترس و طمع</h3></div>',
            unsafe_allow_html=True
        )

        fg = market.get("fear_greed")

        if fg:

            st.metric(
                "Fear & Greed",
                f'{fg["value"]}/100',
                fg["label"]
            )

            st.progress(fg["value"])

        else:

            st.info("اطلاعات موجود نیست.")

        tech = market.get("technical", {})

        st.markdown(
            '<div class="panel"><h3>📈 تحلیل تکنیکال BTC</h3></div>',
            unsafe_allow_html=True
        )

        st.metric("RSI 14", tech.get("rsi_14", "ناموجود"))

        st.metric(
            "میانگین ۷ روزه",
            money(tech.get("sma_7"))
        )

    st.markdown(
        '<div class="panel"><h3>🚨 اخبار مهم بازار</h3></div>',
        unsafe_allow_html=True
    )

    if headlines:

        for item in headlines[:15]:

            st.markdown(
                f'**{item["score"]}/100 — {item["title"]}**'
            )

            st.markdown(
                f'[مشاهده خبر]({item["url"]})'
            )

            st.divider()

    else:

        st.info("خبری دریافت نشد.")

    if market.get("errors"):

        with st.expander("⚠️ خطاهای دریافت اطلاعات"):

            for error in market["errors"]:
                st.write(error)

except Exception as error:

    st.error(f"خطا در اجرای تحلیل: {error}")

st.caption("CryptoScope AI | این اطلاعات توصیه خرید یا فروش نیست.")
