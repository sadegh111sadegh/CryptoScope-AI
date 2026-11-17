import streamlit as st
from analysis import build_report

st.set_page_config(
    page_title="CryptoScope AI",
    page_icon="📡"
)

st.title("📡 CryptoScope AI")
st.caption("Crypto Market Intelligence")

try:
    market, direction, score, rows, headlines, high = build_report()

    st.header("Overall Market")
    st.metric("Market Direction", direction, score)

    st.metric(
        "24H Market Change",
        f"{market.get('market_cap_change_24h_pct')}%"
    )

    st.metric(
        "BTC Dominance",
        f"{market.get('btc_dominance')}%"
    )

    st.header("Market Factors")

    for name, value in rows:
        st.write(f"**{name}** — {value}")

    st.header("Important News")

    for item in headlines[:15]:
        st.write(f"**{item['score']}/100**")
        st.write(item["title"])
        st.markdown(f"[Read source]({item['url']})")

except Exception as error:
    st.error(f"Data error: {error}")
