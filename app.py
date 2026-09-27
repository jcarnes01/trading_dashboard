import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SPX Morning Playbook", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for clean mobile viewing
st.markdown("""
    
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_macro_data():
    tickers = {
        "SPY": "SPY",
        "RSP": "RSP",
        "VIX": "^VIX",
        "10Y": "^TNX",
        "DXY": "DX-Y.NYB",
        "Gold": "GC=F"
    }
    raw = yf.download(list(tickers.values()), period="5d", interval="1d", progress=False)['Close']
    
    current = {k: raw[v].iloc[-1] for k, v in raw.items()}
    prev = {k: raw[v].iloc[-2] for k, v in raw.items()}
    changes = {k: ((current[k] - prev[k]) / prev[k]) * 100 for k in current}
    
    # 5-day RSP/SPY trend
    ratio_series = raw[tickers["RSP"]] / raw[tickers["SPY"]]
    ratio_slope = (ratio_series.iloc[-1] - ratio_series.iloc[0]) / ratio_series.iloc[0]
    
    return current, changes, ratio_slope

@st.cache_data(ttl=600)
def fetch_options_structure():
    spx = yf.Ticker("^SPX")
    hist = spx.history(period="2d")
    spot = hist['Close'].iloc[-1]
    
    # Analyze nearest expiration
    expirations = spx.options
    if not expirations:
        return spot, 0, 0, 0
        
    nearest_exp = expirations[0]
    chain = spx.option_chain(nearest_exp)
    calls, puts = chain.calls, chain.puts
    
    # Put / Call Walls by Open Interest
    call_wall = calls.loc[calls['openInterest'].idxmax()]['strike'] if not calls.empty else spot * 1.01
    put_wall = puts.loc[puts['openInterest'].idxmax()]['strike'] if not puts.empty else spot * 0.99
    
    # Expected Move (ATM Straddle)
    atm_call = calls.iloc[(calls['strike'] - spot).abs().argsort()[:1]]
    atm_put = puts.iloc[(puts['strike'] - spot).abs().argsort()[:1]]
    straddle = (atm_call['lastPrice'].values[0] if not atm_call.empty else 0) + \
               (atm_put['lastPrice'].values[0] if not atm_put.empty else 0)
    
    return spot, call_wall, put_wall, straddle

# App Layout
st.title("SPX Morning Brief")
st.caption(f"Refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M ET')}")

spot, call_wall, put_wall, straddle = fetch_options_structure()
macro, changes, ratio_slope = fetch_macro_data()

# Compute Direction Score
score = 0
score += 1 if ratio_slope > 0 else -1
score += 1 if changes["10Y"] < 0 else -1
score += 1 if changes["DXY"] < 0 else -1
score += 1 if changes["VIX"] < 0 else -1

# Display Squeeze Signal
if score >= 2:
    st.success(f"🟢 **Directional Bias: BULLISH (Score: +{score}/4)** — Look for Bull Put Spreads + 7/14 DTE Long Calls.")
elif score <= -2:
    st.error(f"🔴 **Directional Bias: BEARISH (Score: {score}/4)** — Look for Bear Call Spreads + 7/14 DTE Long Puts.")
else:
    st.info(f"⚪ **Directional Bias: NEUTRAL (Score: {score}/4)** — Market rangebound. Favor pure OTM credit spreads.")

st.markdown("---")

# Key Strike Barriers
st.subheader("SPX Structural Levels")
c1, c2, c3 = st.columns(3)
c1.metric("SPX Spot", f"{spot:,.1f}")
c2.metric("Put Wall (Support)", f"{put_wall:,.0f}")
c3.metric("Call Wall (Resistance)", f"{call_wall:,.0f}")

st.write(f"**Est. Daily Expected Move:** \(\\pm\){straddle:.1f} pts (Range: {spot-straddle:,.0f} — {spot+straddle:,.0f})")

st.markdown("---")

# Macro Grid
st.subheader("Macro Intermarket Matrix")
m1, m2 = st.columns(2)
m1.metric("VIX", f"{macro['VIX']:.2f}", f"{changes['VIX']:+.2f}%", delta_color="inverse")
m2.metric("10Y Yield", f"{macro['10Y']:.3f}%", f"{changes['10Y']:+.2f}%", delta_color="inverse")

m3, m4 = st.columns(2)
m3.metric("DXY (USD)", f"{macro['DXY']:.2f}", f"{changes['DXY']:+.2f}%", delta_color="inverse")
m4.metric("Gold", f"${macro['Gold']:,.1f}", f"{changes['Gold']:+.2f}%")

m5, m6 = st.columns(2)
m5.metric("RSP/SPY 5D Trend", f"{ratio_slope*100:+.2f}%", delta_color="normal")
