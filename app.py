import streamlit as st
import time
import pandas as pd
import pyotp
from SmartApi import SmartConnect   # ✅ CORRECT IMPORT

# ===============================
# STREAMLIT CONFIG
# ===============================
st.set_page_config(page_title="Live PCR Dashboard", layout="wide")
st.title("📊 LIVE PCR ANALYSIS – Angel One SmartAPI")
st.caption("🔄 Auto-refresh every 30 seconds")

# ===============================
# AUTO REFRESH (NATIVE)
# ===============================
REFRESH_INTERVAL = 30

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > REFRESH_INTERVAL:
    st.session_state.last_refresh = time.time()
    st.rerun()

# ===============================
# CREDENTIALS (USE SECRETS IN PROD)
# ===============================
API_KEY = "YOUR_API_KEY"
CLIENT_ID = "YOUR_CLIENT_ID"
PASSWORD = "YOUR_PASSWORD"
TOTP_SECRET = "YOUR_TOTP_SECRET"

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
    params = {
        "exchange": "NFO",
        "symbol": symbol,
        "expiry": expiry
    }
    res = smartApi.getOptionChain(params)

    if not res.get("status"):
        st.error(res.get("message", "API Error"))
        return pd.DataFrame()

    return pd.DataFrame(res["data"])

# ===============================
# PCR CALCULATIONS
# ===============================
def calculate_pcr(df):
    ce = df[df.optionType == "CE"]
    pe = df[df.optionType == "PE"]

    call_oi = ce.openInterest.sum()
    put_oi = pe.openInterest.sum()

    call_chg = ce.changeinOpenInterest.sum()
    put_chg = pe.changeinOpenInterest.sum()

    pcr = round(put_oi / call_oi, 2) if call_oi else 0
    pcr_chg = round(put_chg / call_chg, 2) if call_chg else 0

    return pcr, pcr_chg

# ===============================
# STRIKE-WISE PCR
# ===============================
def strike_pcr(df):
    ce = df[df.optionType == "CE"][["strikePrice", "openInterest", "changeinOpenInterest"]]
    pe = df[df.optionType == "PE"][["strikePrice", "openInterest", "changeinOpenInterest"]]

    merged = ce.merge(pe, on="strikePrice", suffixes=("_CE", "_PE"))
    merged["PCR"] = (merged.openInterest_PE / merged.openInterest_CE).round(2)
    merged["PCR_OI_Change"] = (
        merged.changeinOpenInterest_PE / merged.changeinOpenInterest_CE
    ).round(2)

    return merged.sort_values("strikePrice")

# ===============================
# SIGNAL LOGIC
# ===============================
def signal_logic(pcr, pcr_chg):
    if pcr > 1.1 and pcr_chg > 1:
        return "🟢 STRONG BULLISH"
    elif pcr < 0.9 and pcr_chg < 1:
        return "🔴 STRONG BEARISH"
    else:
        return "🟡 RANGE / NEUTRAL"

# ===============================
# UI INPUTS
# ===============================
symbol = st.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
expiry = st.text_input("Expiry (YYYY-MM-DD)", "2026-01-30")

df = fetch_option_chain(symbol, expiry)

if not df.empty:
    pcr, pcr_chg = calculate_pcr(df)
    signal = signal_logic(pcr, pcr_chg)

    c1, c2, c3 = st.columns(3)
    c1.metric("📈 PCR (Total OI)", pcr)
    c2.metric("📉 PCR (OI Change)", pcr_chg)
    c3.metric("🤖 Signal", signal)

    st.subheader("📊 Strike-wise PCR (Smart Money View)")
    st.dataframe(strike_pcr(df), use_container_width=True)
else:
    st.warning("Waiting for option chain data...")
