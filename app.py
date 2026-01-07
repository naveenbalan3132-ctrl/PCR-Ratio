import streamlit as st
from streamlit_autorefresh import st_autorefresh
from smartapi import SmartConnect
import pyotp
import pandas as pd

# ===============================
# AUTO REFRESH EVERY 30 SECONDS
# ===============================
st_autorefresh(interval=30 * 1000, key="pcr_refresh")

st.set_page_config(page_title="Live PCR Dashboard", layout="wide")

# ===============================
# ANGEL ONE CREDENTIALS
# ===============================
API_KEY = "YOUR_API_KEY"
CLIENT_ID = "YOUR_CLIENT_ID"
PASSWORD = "YOUR_PASSWORD"
TOTP_SECRET = "YOUR_TOTP_SECRET"

# ===============================
# LOGIN FUNCTION
# ===============================
@st.cache_resource
def angel_login():
    smartApi = SmartConnect(api_key=API_KEY)
    totp = pyotp.TOTP(TOTP_SECRET).now()
    smartApi.generateSession(CLIENT_ID, PASSWORD, totp)
    return smartApi

smartApi = angel_login()

# ===============================
# OPTION CHAIN FETCH
# ===============================
def fetch_option_chain(symbol, expiry):
    params = {
        "exchange": "NFO",
        "symbol": symbol,
        "expiry": expiry
    }
    response = smartApi.getOptionChain(params)
    if not response["status"]:
        st.error(response["message"])
        return pd.DataFrame()
    return pd.DataFrame(response["data"])

# ===============================
# PCR CALCULATIONS
# ===============================
def calculate_pcr(df):
    call_oi = df[df.optionType == "CE"]["openInterest"].sum()
    put_oi  = df[df.optionType == "PE"]["openInterest"].sum()

    call_oi_chg = df[df.optionType == "CE"]["changeinOpenInterest"].sum()
    put_oi_chg  = df[df.optionType == "PE"]["changeinOpenInterest"].sum()

    pcr = round(put_oi / call_oi, 2) if call_oi else 0
    pcr_oi_change = round(put_oi_chg / call_oi_chg, 2) if call_oi_chg else 0

    return pcr, pcr_oi_change

# ===============================
# STRIKE WISE PCR
# ===============================
def strike_pcr(df):
    ce = df[df.optionType == "CE"][["strikePrice", "openInterest", "changeinOpenInterest"]]
    pe = df[df.optionType == "PE"][["strikePrice", "openInterest", "changeinOpenInterest"]]

    merged = ce.merge(pe, on="strikePrice", suffixes=("_CE", "_PE"))
    merged["PCR"] = round(merged["openInterest_PE"] / merged["openInterest_CE"], 2)
    merged["PCR_OI_Change"] = round(
        merged["changeinOpenInterest_PE"] / merged["changeinOpenInterest_CE"], 2
    )

    return merged.sort_values("strikePrice")

# ===============================
# SIGNAL LOGIC
# ===============================
def trading_signal(pcr, pcr_oi):
    if pcr > 1.1 and pcr_oi > 1:
        return "🟢 STRONG BULLISH"
    elif pcr < 0.9 and pcr_oi < 1:
        return "🔴 STRONG BEARISH"
    else:
        return "🟡 NEUTRAL / RANGE"

# ===============================
# STREAMLIT UI
# ===============================
st.title("📊 LIVE PCR ANALYSIS – Angel One SmartAPI")

symbol = st.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
expiry = st.text_input("Expiry (YYYY-MM-DD)", "2026-01-30")

df = fetch_option_chain(symbol, expiry)

if not df.empty:
    pcr, pcr_oi = calculate_pcr(df)
    signal = trading_signal(pcr, pcr_oi)

    col1, col2, col3 = st.columns(3)

    col1.metric("📈 PCR (Total OI)", pcr)
    col2.metric("📉 PCR (OI Change)", pcr_oi)
    col3.metric("🤖 Market Signal", signal)

    st.subheader("📊 Strike-wise PCR (Smart Money View)")
    strike_df = strike_pcr(df)
    st.dataframe(strike_df, use_container_width=True)

    st.caption("🔄 Auto-refresh every 30 seconds | Source: Angel One SmartAPI")
else:
    st.warning("Waiting for option chain data...")
