import streamlit as st
import time
import pandas as pd
import pyotp
from SmartApi import SmartConnect

# ===============================
# STREAMLIT CONFIG
# ===============================
st.set_page_config(page_title="Live PCR Dashboard", layout="wide")
st.title("📊 LIVE PCR ANALYSIS – Angel One SmartAPI")
st.caption("🔄 Auto-refresh every 30 seconds")

# ===============================
# AUTO REFRESH (SAFE)
# ===============================
REFRESH_INTERVAL = 30
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > REFRESH_INTERVAL:
    st.session_state.last_refresh = time.time()
    st.rerun()

# ===============================
# CREDENTIALS (MOVE TO SECRETS IN PROD)
# ===============================
API_KEY = st.secrets["API_KEY"]
CLIENT_ID = st.secrets["CLIENT_ID"]
PASSWORD = st.secrets["PASSWORD"]
TOTP_SECRET = st.secrets["TOTP_SECRET"]

# ===============================
# LOGIN (CACHED)
# ===============================
@st.cache_resource
def angel_login():
    obj = SmartConnect(api_key=API_KEY)
    totp = pyotp.TOTP(TOTP_SECRET).now()
    obj.generateSession(CLIENT_ID, PASSWORD, totp)
    return obj

smartApi = angel_login()

# ===============================
# FETCH OPTION CHAIN
# ===============================
def fetch_option_chain(symbol, expiry):
    res = smartApi.getOptionChain({
        "exchange": "NFO",
        "symbol": symbol,
        "expiry": expiry
    })
    if not res.get("status"):
        st.error(res.get("message", "Angel API Error"))
        return pd.DataFrame()
    return pd.DataFrame(res["data"])

# ===============================
# PCR CALCULATIONS
# ===============================
def calculate_pcr(df):
    ce = df[df.optionType == "CE"]
    pe = df[df.optionType == "PE"]

    pcr = round(pe.openInterest.sum() / ce.openInterest.sum(), 2)
    pcr_chg = round(
        pe.changeinOpenInterest.sum() / ce.changeinOpenInterest.sum(), 2
    )

    return pcr, pcr_chg

# ===============================
# STRIKE PCR
# ===============================
def strike_pcr(df):
    ce = df[df.optionType == "CE"][["strikePrice", "openInterest", "changeinOpenInterest"]]
    pe = df[df.optionType == "PE"][["strikePrice", "openInterest", "changeinOpenInterest"]]
    df = ce.merge(pe, on="strikePrice", suffixes=("_CE", "_PE"))
    df["PCR"] = (df.openInterest_PE / df.openInterest_CE).round(2)
    df["PCR_OI_Change"] = (
        df.changeinOpenInterest_PE / df.changeinOpenInterest_CE
    ).round(2)
    return df.sort_values("strikePrice")

# ===============================
# SIGNAL ENGINE
# ===============================
def signal(pcr, pcr_chg):
    if pcr > 1.1 and pcr_chg > 1:
        return "🟢 STRONG BULLISH"
    elif pcr < 0.9 and pcr_chg < 1:
        return "🔴 STRONG BEARISH"
    else:
        return "🟡 RANGE / NEUTRAL"

# ===============================
# UI
# ===============================
symbol = st.selectbox("Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
expiry = st.text_input("Expiry (YYYY-MM-DD)", "2026-01-30")

df = fetch_option_chain(symbol, expiry)

if not df.empty:
    pcr, pcr_chg = calculate_pcr(df)
    st.metric("📈 PCR", pcr)
    st.metric("📉 OI PCR", pcr_chg)
    st.metric("🤖 Signal", signal(pcr, pcr_chg))
    st.dataframe(strike_pcr(df), use_container_width=True)
