from smartapi import SmartConnect
import pandas as pd
import pyotp

# -------- LOGIN -------- #
API_KEY = "YOUR_API_KEY"
CLIENT_ID = "YOUR_CLIENT_ID"
PASSWORD = "YOUR_PASSWORD"
TOTP_SECRET = "YOUR_TOTP_SECRET"

obj = SmartConnect(api_key=API_KEY)

totp = pyotp.TOTP(TOTP_SECRET).now()

session = obj.generateSession(
    CLIENT_ID,
    PASSWORD,
    totp
)

# -------- FETCH OPTION CHAIN -------- #
params = {
    "exchange": "NFO",
    "symboltoken": "26000",   # NIFTY token (example)
    "interval": "5MIN"
}

option_chain = obj.optionGreek(params)

df = pd.DataFrame(option_chain['data'])

# -------- PCR CALCULATION -------- #
total_put_oi = df[df['optionType'] == 'PE']['openInterest'].sum()
total_call_oi = df[df['optionType'] == 'CE']['openInterest'].sum()

pcr = round(total_put_oi / total_call_oi, 2)

print("Put OI:", total_put_oi)
print("Call OI:", total_call_oi)
print("PCR:", pcr)

# -------- TRADING SIGNAL -------- #
if pcr > 1.1:
    signal = "BUY (Bullish Market)"
elif pcr < 0.9:
    signal = "SELL (Bearish Market)"
else:
    signal = "NO TRADE (Sideways)"

print("Trading Signal:", signal)
