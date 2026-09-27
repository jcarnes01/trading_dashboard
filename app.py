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
    
    current = {}
    changes = {}
    
    # Download each ticker individually to avoid MultiIndex parsing issues and silent NaN fails
    history_data = {}
    for label, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            df = t.history(period="7d")
            if not df.empty and len(df) >= 2:
                # Drop rows where Close is NaN
                df = df.dropna(subset=['Close'])
                history_data[label] = df['Close']
                curr_val = float(df['Close'].iloc[-1])
                prev_val = float(df['Close'].iloc[-2])
                current[label] = curr_val
                changes[label] = ((curr_val - prev_val) / prev_val) * 100
            else:
                current[label] = 0.0
                changes[label] = 0.0
        except Exception:
            current[label] = 0.0
            changes[label] = 0.0

    # Calculate 5-day RSP/SPY ratio trend
    ratio_slope = 0.0
    if "RSP" in history_data and "SPY" in history_data:
        rsp_close = history_data["RSP"]
        spy_close = history_data["SPY"]
        common_idx = rsp_close.index.intersection(spy_close.index)
        if len(common_idx) >= 2:
            ratio_series = rsp_close.loc[common_idx] / spy_close.loc[common_idx]
            ratio_slope = float((ratio_series.iloc[-1] - ratio_series.iloc[0]) / ratio_series.iloc[0])

    return current, changes, ratio_slope

@st.cache_data(ttl=600)
def fetch_options_structure():
    spx = yf.Ticker("^SPX")
    hist = spx.history(period="5d")
    
    if hist.empty:
        # Fallback to SPY scaled x10 if SPX index feed is delayed
        spy = yf.Ticker("SPY")
        hist = spy.history(period="5d")
        spot = float(hist['Close'].iloc[-1]) * 10 if not hist.empty else 5000.0
    else:
        spot = float(hist['Close'].iloc[-1])
    
    expirations = spx.options
    if not expirations:
        # Fallback approximation: ~0.8% daily expected move
        return spot, spot * 1.01, spot * 0.99, spot * 0.008

    try:
        nearest_exp = expirations[0]
        chain = spx.option_chain(nearest_exp)
        calls, puts = chain.calls, chain.puts

        call_wall = float(calls.loc[calls['openInterest'].idxmax()]['strike']) if not calls.empty and calls['openInterest'].sum() > 0 else spot * 1.01
        put_wall = float(puts.loc[puts['openInterest'].idxmax()]['strike']) if not puts.empty and puts['openInterest'].sum() > 0 else spot * 0.99

        # ATM Straddle
        atm_call = calls.iloc[(calls['strike'] - spot).abs().argsort()[:1]]
        atm_put = puts.iloc[(puts['strike'] - spot).abs().argsort()[:1]]
        call_price = float(atm_call['lastPrice'].values[0]) if not atm_call.empty else 0.0
        put_price = float(atm_put['lastPrice'].values[0]) if not atm_put.empty else 0.0
        straddle = call_price + put_price if (call_price + put_price) > 0 else spot * 0.008
    except Exception:
        call_wall = spot * 1.01
        put_wall = spot * 0.99
        straddle = spot * 0.008

    return spot, call_wall, put_wall, straddle

# App Layout
st.title("SPX Morning Brief")
st.caption(f"Refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M ET')}")

spot, call_wall, put_wall, straddle = fetch_options_structure()
macro, changes, ratio_slope = fetch_macro_data()

# Directional Scoring
score = 0
if ratio_slope > 0: score += 1
elif ratio_slope < 0: score -= 1

if changes.get("10Y", 0) < 0: score += 1
elif changes.get("10Y", 0) > 0: score -= 1

if changes.get("DXY", 0) < 0: score += 1
elif changes.get("DXY", 0) > 0: score -= 1

if changes.get("VIX", 0) < 0: score += 1
elif changes.get("VIX", 0) > 0: score -= 1

# Display Signal
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
m1.metric("VIX", f"{macro.get('VIX', 0):.2f}", f"{changes.get('VIX', 0):+.2f}%", delta_color="inverse")
m2.metric("10Y Yield", f"{macro.get('10Y', 0):.3f}%", f"{changes.get('10Y', 0):+.2f}%", delta_color="inverse")

m3, m4 = st.columns(2)
m3.metric("DXY (USD)", f"{macro.get('DXY', 0):.2f}", f"{changes.get('DXY', 0):+.2f}%", delta_color="inverse")
m4.metric("Gold", f"${macro.get('Gold', 0):,.1f}", f"{changes.get('Gold', 0):+.2f}%")

m5, m6 = st.columns(2)
m5.metric("RSP/SPY 5D Trend", f"{ratio_slope*100:+.2f}%", delta_color="normal")
