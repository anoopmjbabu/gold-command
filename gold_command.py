"""
GOLD COMMAND — XAU/USD Market Intelligence Terminal
A Streamlit-powered dashboard with live data, volume-spike detection,
news correlation, three-tier analysis, and computed intelligence panels.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
# Plotly chart removed — TradingView handles all charting
import feedparser
import requests
from datetime import datetime, timedelta
import json
import re
from html import escape as html_escape
from urllib.parse import urlparse
import time
import sys
import os

# Add current directory to path for signal_engine import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_engine import fetch_multi_timeframe, generate_signals, format_signal_for_beginner

import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("gold_command")

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="GOLD COMMAND — XAU/USD Intelligence | by Anoop B.",
    page_icon="🥇",
    layout="wide",
    initial_sidebar_state="collapsed",
)

GOLD_TICKER = "GC=F"
CORRELATED = {
    "DXY": "DX-Y.NYB",
    "US 10Y": "^TNX",
    "VIX": "^VIX",
    "Crude Oil": "CL=F",
    "S&P 500": "^GSPC",
    "EUR/USD": "EURUSD=X",
    "Silver": "SI=F",
    "BTC/USD": "BTC-USD",
}

# S/R levels now computed dynamically by signal_engine.py

# ═══════════════════════════════════════════════════════════════
# CUSTOM CSS
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ═══ Global Reset ═══ */
.stApp { background: #060a12; }
section[data-testid="stSidebar"] { background: #0b1022; }
h1,h2,h3,h4,h5,h6,p,span,div,li { font-family: 'Inter', sans-serif !important; }
code, .stMetricValue { font-family: 'JetBrains Mono', monospace !important; }

/* ═══ Custom Scrollbar ═══ */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #060a12; }
::-webkit-scrollbar-thumb { background: #1e2745; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2a3558; }

/* ═══ Header ═══ */
.gold-header {
    background: linear-gradient(135deg, #0b1022 0%, #151d38 50%, #1a2442 100%);
    border: 1px solid rgba(240,185,11,0.15);
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 20px;
    display: flex; justify-content: space-between; align-items: center;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(240,185,11,0.05);
    position: relative;
    overflow: hidden;
}
.gold-header::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(240,185,11,0.3), transparent);
}
.gold-header h1 {
    color: #f0b90b;
    font-size: 26px; font-weight: 900; letter-spacing: 2px; margin: 0;
    text-shadow: 0 0 20px rgba(240,185,11,0.15);
}
.gold-header .sub { color: #5a6a8a; font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase; margin-top: 2px; }
.live-badge {
    background: rgba(16,185,129,0.08); color: #10b981;
    border: 1px solid rgba(16,185,129,0.2);
    padding: 5px 14px; border-radius: 20px; font-size: 10px; font-weight: 700;
    display: inline-flex; align-items: center; gap: 6px;
    letter-spacing: 1px; text-transform: uppercase;
}
.live-dot {
    width: 6px; height: 6px; border-radius: 50%; background: #10b981;
    animation: pulse-glow 1.4s infinite; display: inline-block;
    box-shadow: 0 0 6px rgba(16,185,129,0.4);
}
@keyframes pulse-glow {
    0%,100% { opacity:1; box-shadow: 0 0 6px rgba(16,185,129,0.4); }
    50% { opacity:0.3; box-shadow: 0 0 2px rgba(16,185,129,0.1); }
}

/* ═══ KPI Cards ═══ */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}
@media (max-width: 768px) {
    .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .kpi-value { font-size: 16px !important; word-break: keep-all; white-space: nowrap; }
    .kpi-label { font-size: 8px; }
    .kpi-card { padding: 10px 12px; }
    .gold-header h1 { font-size: 20px !important; }
    .gold-header .sub { font-size: 9px; }
    .section-header h2 { font-size: 14px !important; }
}
@media (max-width: 480px) {
    .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 6px; }
    .kpi-value { font-size: 14px !important; }
    .kpi-card { padding: 8px 10px; }
}
.kpi-card {
    background: linear-gradient(145deg, #0b1022, #0f1528);
    border: 1px solid #1a2240;
    border-radius: 10px;
    padding: 14px 16px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
    min-width: 0;
}
.kpi-card:hover {
    border-color: rgba(240,185,11,0.2);
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}
.kpi-card::after {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, var(--kpi-accent, #1e2745), transparent);
    opacity: 0.5;
}
.kpi-label {
    font-size: 9px; font-weight: 700; color: #5a6a8a;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;
}
.kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px; font-weight: 700; color: #e8ecf4;
    line-height: 1.2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.kpi-delta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; font-weight: 600; margin-top: 4px;
    display: inline-flex; align-items: center; gap: 4px;
    padding: 2px 6px; border-radius: 4px;
}
.kpi-delta.up { color: #10b981; background: rgba(16,185,129,0.08); }
.kpi-delta.down { color: #ef4444; background: rgba(239,68,68,0.08); }
.kpi-delta.neutral { color: #5a6a8a; background: rgba(90,106,138,0.08); }

/* ═══ Section Headers ═══ */
.section-header {
    background: linear-gradient(135deg, #0b1022 0%, #111830 100%);
    border: 1px solid #1a2240;
    border-radius: 10px;
    padding: 14px 22px;
    margin-bottom: 12px;
    display: flex; justify-content: space-between; align-items: center;
    position: relative;
    overflow: hidden;
}
.section-header::before {
    content: '';
    position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    background: var(--section-accent, #f0b90b);
    border-radius: 0 2px 2px 0;
}
.section-title {
    font-size: 11px; font-weight: 800; text-transform: uppercase;
    letter-spacing: 1.2px; color: #c8d0e4;
}
.pill {
    font-size: 8px; font-weight: 800; padding: 3px 8px; border-radius: 4px;
    text-transform: uppercase; letter-spacing: 0.8px;
}
.pill-live { background: rgba(16,185,129,0.1); color: #10b981; border: 1px solid rgba(16,185,129,0.15); }
.pill-model { background: rgba(168,85,247,0.1); color: #a855f7; border: 1px solid rgba(168,85,247,0.15); }
.pill-data { background: rgba(59,130,246,0.1); color: #3b82f6; border: 1px solid rgba(59,130,246,0.15); }

/* ═══ Intel Cards ═══ */
.intel-card {
    background: linear-gradient(145deg, #0b1022, #0f1528);
    border: 1px solid #1a2240;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 12px;
    transition: border-color 0.3s ease;
}
.intel-card:hover { border-color: #263054; }
.intel-card h3 {
    font-size: 11px; font-weight: 800; text-transform: uppercase;
    letter-spacing: 1px; color: #8892ab;
    margin-bottom: 12px;
    display: flex; justify-content: space-between; align-items: center;
}

/* ═══ Level Rows ═══ */
.level-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 5px 2px;
    font-size: 12px;
    border-bottom: 1px solid rgba(26,34,64,0.5);
    transition: background 0.2s ease;
}
.level-row:last-child { border-bottom: none; }
.level-row:hover { background: rgba(240,185,11,0.02); }

/* ═══ Driver Rows ═══ */
.driver-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 7px 2px;
    border-bottom: 1px solid rgba(26,34,64,0.5);
    font-size: 12px;
    transition: background 0.2s ease;
}
.driver-row:last-child { border-bottom: none; }
.driver-row:hover { background: rgba(240,185,11,0.02); }
.tag-bull { background: rgba(16,185,129,0.1); color: #10b981; padding: 2px 8px; border-radius: 4px; font-size: 9px; font-weight: 700; border: 1px solid rgba(16,185,129,0.15); }
.tag-bear { background: rgba(239,68,68,0.1); color: #ef4444; padding: 2px 8px; border-radius: 4px; font-size: 9px; font-weight: 700; border: 1px solid rgba(239,68,68,0.15); }
.tag-mixed { background: rgba(245,158,11,0.1); color: #f59e0b; padding: 2px 8px; border-radius: 4px; font-size: 9px; font-weight: 700; border: 1px solid rgba(245,158,11,0.15); }

/* ═══ Spike Cards ═══ */
.spike-card {
    background: linear-gradient(145deg, #0d1326, #111830);
    border: 1px solid #1a2240; border-radius: 8px;
    padding: 14px; margin-bottom: 8px;
    transition: border-color 0.2s ease;
}
.spike-card:hover { border-color: #263054; }
.spike-header { display: flex; justify-content: space-between; margin-bottom: 6px; }
.spike-date { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #8892ab; }
.spike-vol { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; }
.spike-up { background: rgba(16,185,129,0.1); color: #10b981; border: 1px solid rgba(16,185,129,0.12); }
.spike-down { background: rgba(239,68,68,0.1); color: #ef4444; border: 1px solid rgba(239,68,68,0.12); }

/* ═══ Analysis Tiers ═══ */
.tier-tab {
    padding: 14px 18px; border-radius: 8px; margin-bottom: 6px;
    font-size: 12px; line-height: 1.7;
    border: 1px solid transparent;
}
.tier-beginner { background: rgba(59,130,246,0.05); border-left: 3px solid #3b82f6; border-color: rgba(59,130,246,0.08); }
.tier-intermediate { background: rgba(245,158,11,0.05); border-left: 3px solid #f59e0b; border-color: rgba(245,158,11,0.08); }
.tier-pro { background: rgba(168,85,247,0.05); border-left: 3px solid #a855f7; border-color: rgba(168,85,247,0.08); }
.tier-label { font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }

/* ═══ KPI Metric Override (fallback for st.metric) ═══ */
[data-testid="stMetricValue"] { font-size: 20px !important; }
[data-testid="stMetricDelta"] { font-size: 12px !important; }

/* ═══ Probability Bars ═══ */
.prob-row { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; font-size: 11px; }
.prob-bar { flex: 1; height: 6px; background: #111830; border-radius: 3px; overflow: hidden; }
.prob-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }

/* ═══ Correlation Cells ═══ */
.corr-cell {
    text-align: center; padding: 8px; border-radius: 4px; margin: 2px;
    font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600;
}

/* ═══ TradingView Embed ═══ */
.tv-chart-wrap {
    border: 1px solid #1a2240; border-radius: 10px; overflow: hidden;
    margin-bottom: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}

/* ═══ Signal Cards ═══ */
.signal-card {
    background: linear-gradient(145deg, #0b1022 0%, #0f1528 100%);
    border: 1px solid #1a2240; border-radius: 12px;
    padding: 20px; margin-bottom: 12px;
    position: relative; overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.3s ease;
}
.signal-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.signal-card.buy { border-left: 4px solid #10b981; }
.signal-card.buy:hover { border-color: rgba(16,185,129,0.3); border-left-color: #10b981; }
.signal-card.sell { border-left: 4px solid #ef4444; }
.signal-card.sell:hover { border-color: rgba(239,68,68,0.3); border-left-color: #ef4444; }
.signal-card.wait { border-left: 4px solid #f59e0b; }
.signal-badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 20px; font-weight: 900; font-family: 'JetBrains Mono', monospace;
    letter-spacing: 2px;
}
.signal-badge.buy { color: #10b981; text-shadow: 0 0 12px rgba(16,185,129,0.2); }
.signal-badge.sell { color: #ef4444; text-shadow: 0 0 12px rgba(239,68,68,0.2); }
.signal-badge.wait { color: #f59e0b; }
.signal-conf {
    font-size: 9px; font-weight: 800; padding: 3px 10px; border-radius: 4px;
    text-transform: uppercase; letter-spacing: 1px; display: inline-block; margin-left: 10px;
}
.conf-high { background: rgba(16,185,129,0.1); color: #10b981; border: 1px solid rgba(16,185,129,0.15); }
.conf-med { background: rgba(245,158,11,0.1); color: #f59e0b; border: 1px solid rgba(245,158,11,0.15); }
.conf-low { background: rgba(107,122,153,0.1); color: #6b7a99; border: 1px solid rgba(107,122,153,0.15); }
.signal-score-ring {
    width: 52px; height: 52px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: 'JetBrains Mono', monospace; font-size: 16px; font-weight: 900;
    position: absolute; top: 16px; right: 18px;
    box-shadow: 0 0 12px rgba(0,0,0,0.2);
}
.signal-explanation { font-size: 12px; color: #8892ab; line-height: 1.7; margin: 12px 0; }
.signal-levels {
    display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 10px;
    margin-top: 14px; padding-top: 14px;
    border-top: 1px solid rgba(26,34,64,0.6);
}
.signal-level-item { text-align: center; }
.signal-level-label { font-size: 8px; color: #5a6a8a; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 700; }
.signal-level-value { font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 700; margin-top: 3px; }
.signal-reasons { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 6px; }
.signal-reason-tag {
    font-size: 9px; font-weight: 600; padding: 3px 10px; border-radius: 12px;
    background: rgba(240,185,11,0.06); color: #f0b90b;
    border: 1px solid rgba(240,185,11,0.12);
    transition: background 0.2s ease;
}
.signal-reason-tag:hover { background: rgba(240,185,11,0.12); }
.signal-empty {
    text-align: center; padding: 40px; color: #5a6a8a; font-size: 13px;
    background: linear-gradient(145deg, #0b1022, #0f1528);
    border: 1px dashed #1a2240; border-radius: 12px;
}
.signal-trend-badge {
    font-size: 10px; font-weight: 800; padding: 4px 12px; border-radius: 4px;
    display: inline-block; margin-bottom: 8px; letter-spacing: 0.5px;
}

/* ═══ Range Cards ═══ */
.range-card {
    background: linear-gradient(145deg, #0b1022, #0f1528);
    border: 1px solid #1a2240;
    border-radius: 10px;
    padding: 14px 16px;
    transition: border-color 0.3s ease;
}
.range-card:hover { border-color: #263054; }

/* ═══ Force Dark on Streamlit elements ═══ */
.stApp, .main, .block-container, section[data-testid="stMain"],
[data-testid="stAppViewContainer"], [data-testid="stHeader"],
[data-testid="stToolbar"], .element-container { background-color: #060a12 !important; }
section[data-testid="stSidebar"] > div { background: #0b1022 !important; }
[data-testid="stExpander"] { background: #0b1022 !important; border-color: #1a2240 !important; }
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #0b1022, #0f1528) !important;
    border: 1px solid #1a2240 !important;
    border-radius: 10px !important;
    padding: 12px !important;
}
[data-testid="stMetricValue"] { color: #e8ecf4 !important; }
[data-testid="stMetricLabel"] { color: #5a6a8a !important; font-size: 9px !important; text-transform: uppercase !important; letter-spacing: 1px !important; }
.stRadio label { color: #8892ab !important; }
.stRadio [data-baseweb="radio"] { border-color: #1a2240 !important; }
div[data-baseweb="select"] { background: #0b1022 !important; }
p, span, li, div { color: #e8ecf4; }
strong, b { color: #f0b90b !important; }
a { color: #3b82f6 !important; }
hr { border-color: #1a2240 !important; opacity: 0.5 !important; }

/* ═══ Hide Streamlit chrome ═══ */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ═══ Global padding adjustment ═══ */
.block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }

/* ═══ Daily Brief Card ═══ */
.daily-brief {
    background: linear-gradient(135deg, #0d1326 0%, #131b38 50%, #0f1730 100%);
    border: 1px solid rgba(240,185,11,0.2);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}
.daily-brief::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, rgba(240,185,11,0.4), rgba(16,185,129,0.3), transparent);
}
.daily-brief-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 12px;
}
.daily-brief-title {
    font-size: 10px; font-weight: 800; color: #f0b90b;
    text-transform: uppercase; letter-spacing: 1.5px;
    display: flex; align-items: center; gap: 8px;
}
.daily-brief-body {
    font-size: 13px; line-height: 1.8; color: #c8d0e4;
}
.daily-brief-body b { color: #f0b90b !important; }
.daily-brief-body .highlight-up { color: #10b981; font-weight: 600; }
.daily-brief-body .highlight-down { color: #ef4444; font-weight: 600; }
.daily-brief-body .highlight-neutral { color: #f59e0b; font-weight: 600; }
.brief-bias-badge {
    font-size: 10px; font-weight: 800; padding: 4px 14px; border-radius: 20px;
    letter-spacing: 0.8px; text-transform: uppercase;
}
@media (max-width: 768px) {
    .daily-brief { padding: 14px 16px; }
    .daily-brief-body { font-size: 12px; line-height: 1.7; }
}

/* ═══ Divider ═══ */
.section-divider {
    height: 1px; margin: 24px 0;
    background: linear-gradient(90deg, transparent, #1a2240, transparent);
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# DATA FUNCTIONS
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=600)
def fetch_gold_data(period="6mo", interval="1d"):
    """Fetch OHLCV data for gold with retry logic for rate limits."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            ticker = yf.Ticker(GOLD_TICKER)
            df = ticker.history(period=period, interval=interval)
            df.index = df.index.tz_localize(None) if df.index.tz else df.index
            return df
        except Exception as e:
            err_name = type(e).__name__
            logger.warning(f"fetch_gold_data attempt {attempt+1}/{max_retries} failed: {err_name}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s backoff
            else:
                logger.error(f"All {max_retries} attempts failed for fetch_gold_data")
                return pd.DataFrame()


@st.cache_data(ttl=600)
def fetch_correlated_data(period="3mo"):
    """Fetch data for all correlated instruments with rate-limit handling."""
    data = {}
    for name, ticker_sym in CORRELATED.items():
        for attempt in range(2):
            try:
                t = yf.Ticker(ticker_sym)
                df = t.history(period=period)
                df.index = df.index.tz_localize(None) if df.index.tz else df.index
                if len(df) > 0:
                    data[name] = df
                break
            except Exception as e:
                logger.warning(f"Failed to fetch {name} ({ticker_sym}) attempt {attempt+1}: {e}")
                if attempt == 0:
                    time.sleep(1)
    return data


@st.cache_data(ttl=600)
def fetch_gold_news():
    """Fetch breaking news that drives gold: geopolitics, Fed, wars, macro events."""
    feeds = [
        # Direct gold news (broad — catches most gold-related headlines)
        "https://news.google.com/rss/search?q=gold+price&hl=en-US&gl=US&ceid=US:en&when=1d",
        "https://news.google.com/rss/search?q=gold+market+today&hl=en-US&gl=US&ceid=US:en&when=1d",
        "https://news.google.com/rss/search?q=XAU+USD&hl=en-US&gl=US&ceid=US:en&when=1d",
        # Geopolitical events that move gold (no gold keyword required — these ARE the catalysts)
        "https://news.google.com/rss/search?q=Iran+war+OR+Iran+nuclear+OR+Iran+attack&hl=en-US&gl=US&ceid=US:en&when=1d",
        "https://news.google.com/rss/search?q=Middle+East+war+OR+Israel+strike+OR+nuclear+facility&hl=en-US&gl=US&ceid=US:en&when=1d",
        "https://news.google.com/rss/search?q=tariff+trade+war+OR+sanctions+OR+geopolitical+crisis&hl=en-US&gl=US&ceid=US:en&when=1d",
        # Macro catalysts
        "https://news.google.com/rss/search?q=Federal+Reserve+rate+OR+Fed+interest+rate&hl=en-US&gl=US&ceid=US:en&when=1d",
        "https://news.google.com/rss/search?q=inflation+CPI+OR+treasury+yields+OR+dollar+DXY&hl=en-US&gl=US&ceid=US:en&when=1d",
        # Central bank gold
        "https://news.google.com/rss/search?q=central+bank+gold+OR+gold+reserves+OR+PBOC+gold&hl=en-US&gl=US&ceid=US:en&when=1d",
    ]
    feeds = [url.replace('http://', 'https://') for url in feeds]

    # Blacklist — remove forecast spam and irrelevant noise
    NOISE_WORDS = [
        'forecast', 'prediction', 'price target', 'where will gold',
        'what will gold', 'gold price for 202', 'price forecast',
        'price prediction', 'elliott wave', 'polymarket', 'litefinance',
        'should you buy', 'is gold a good investment', 'fxempire',
        'daily horoscope', 'astrology', 'crypto airdrop',
    ]

    articles = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.get('title', '')
                title = html_escape(title)
                title_lower = title.lower()
                if any(noise in title_lower for noise in NOISE_WORDS):
                    continue

                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except (TypeError, ValueError):
                        pub_date = None
                articles.append({
                    'title': title,
                    'link': entry.get('link', ''),
                    'source': entry.get('source', {}).get('title', '') if hasattr(entry, 'source') else '',
                    'published': pub_date,
                })
        except Exception:
            pass

    # Deduplicate by title
    seen = set()
    unique = []
    for a in articles:
        key = a['title'][:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)

    unique.sort(key=lambda x: x['published'] or datetime.min, reverse=True)
    return unique[:30]


# ═══════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════
def compute_indicators(df):
    """Compute technical indicators."""
    df = df.copy()
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    df['EMA_12'] = df['Close'].ewm(span=12).mean()
    df['EMA_26'] = df['Close'].ewm(span=26).mean()

    # Bollinger Bands
    df['BB_mid'] = df['Close'].rolling(20).mean()
    df['BB_std'] = df['Close'].rolling(20).std()
    df['BB_upper'] = df['BB_mid'] + 2 * df['BB_std']
    df['BB_lower'] = df['BB_mid'] - 2 * df['BB_std']

    # RSI (Wilder's smoothing — matches TradingView/MT4)
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(alpha=1.0/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)  # Prevent division by zero
    df['RSI'] = (100 - (100 / (1 + rs))).fillna(50)  # Default to 50 if NaN

    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']

    # ATR
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(14).mean()

    # Volume analysis
    df['Vol_SMA_20'] = df['Volume'].rolling(20).mean()
    df['Vol_ratio'] = df['Volume'] / df['Vol_SMA_20']

    return df


def detect_volume_spikes(df, threshold=1.5):
    """Detect candles with abnormally high volume."""
    df = df.copy()
    spikes = df[df['Vol_ratio'] >= threshold].copy()
    spikes['change'] = spikes['Close'] - spikes['Open']
    spikes['change_pct'] = (spikes['change'] / spikes['Open']) * 100
    spikes['direction'] = spikes['change'].apply(lambda x: 'UP' if x >= 0 else 'DOWN')
    return spikes.sort_index(ascending=False)


def correlate_news_to_spikes(spikes, news):
    """Match news articles to volume spike dates."""
    correlated = []
    for idx, spike in spikes.iterrows():
        spike_date = idx.date() if hasattr(idx, 'date') else idx
        matched_news = []
        for article in news:
            if article['published']:
                news_date = article['published'].date()
                # Match if news is same day or day before
                diff = (spike_date - news_date).days
                if 0 <= diff <= 1:
                    matched_news.append(article)
        correlated.append({
            'date': spike_date,
            'open': spike['Open'],
            'high': spike['High'],
            'low': spike['Low'],
            'close': spike['Close'],
            'volume': spike['Volume'],
            'vol_ratio': spike['Vol_ratio'],
            'change': spike['change'],
            'change_pct': spike['change_pct'],
            'direction': spike['direction'],
            'news': matched_news[:3],
        })
    return correlated


def compute_correlations(gold_df, corr_data, window=30):
    """Compute rolling correlations between gold and other instruments."""
    results = {}
    gold_returns = gold_df['Close'].pct_change().tail(window)
    for name, df in corr_data.items():
        try:
            other_returns = df['Close'].pct_change().tail(window)
            # Align indices
            common = gold_returns.index.intersection(other_returns.index)
            if len(common) > 10:
                corr = gold_returns.loc[common].corr(other_returns.loc[common])
                if not np.isnan(corr):
                    results[name] = round(corr, 2)
        except Exception:
            pass
    return results


def compute_ranges(df):
    """Compute daily, weekly, monthly ranges and ATR-based expected ranges."""
    current = df['Close'].iloc[-1]
    atr = df['ATR_14'].iloc[-1]

    # Today's range
    today_high = df['High'].iloc[-1]
    today_low = df['Low'].iloc[-1]
    today_range = today_high - today_low

    # Weekly range (last 5 trading days)
    week_data = df.tail(5)
    week_high = week_data['High'].max()
    week_low = week_data['Low'].min()
    week_range = week_high - week_low

    # Monthly range (last 22 trading days)
    month_data = df.tail(22)
    month_high = month_data['High'].max()
    month_low = month_data['Low'].min()
    month_range = month_high - month_low

    # Average ranges (historical)
    daily_ranges = (df['High'] - df['Low']).tail(20)
    avg_daily_range = daily_ranges.mean()

    # Weekly avg: group last 60 days into ~12 weeks
    weekly_highs = df['High'].tail(60).resample('W').max()
    weekly_lows = df['Low'].tail(60).resample('W').min()
    avg_weekly_range = (weekly_highs - weekly_lows).mean() if len(weekly_highs) > 2 else avg_daily_range * 3

    # Monthly avg
    monthly_highs = df['High'].tail(120).resample('ME').max()
    monthly_lows = df['Low'].tail(120).resample('ME').min()
    avg_monthly_range = (monthly_highs - monthly_lows).mean() if len(monthly_highs) > 2 else avg_daily_range * 8

    # ATR-based expected ranges
    expected_daily = atr  # 1-day ATR
    expected_weekly = atr * np.sqrt(5)  # Scale by sqrt of days
    expected_monthly = atr * np.sqrt(22)

    # Range utilization (how much of expected range has been used)
    daily_util = (today_range / expected_daily * 100) if expected_daily > 0 else 0
    weekly_util = (week_range / expected_weekly * 100) if expected_weekly > 0 else 0
    monthly_util = (month_range / expected_monthly * 100) if expected_monthly > 0 else 0

    return {
        'today': {'high': today_high, 'low': today_low, 'range': today_range,
                  'avg': avg_daily_range, 'expected': expected_daily, 'util': daily_util},
        'week': {'high': week_high, 'low': week_low, 'range': week_range,
                 'avg': avg_weekly_range, 'expected': expected_weekly, 'util': weekly_util},
        'month': {'high': month_high, 'low': month_low, 'range': month_range,
                  'avg': avg_monthly_range, 'expected': expected_monthly, 'util': monthly_util},
    }


def compute_probability_targets(df, days=30):
    """Compute probability of reaching price targets based on ATR and historical vol."""
    current = df['Close'].iloc[-1]
    atr = df['ATR_14'].iloc[-1]
    daily_vol = df['Close'].pct_change().std()
    period_vol = daily_vol * np.sqrt(days)

    targets_up = [current * 1.02, current * 1.05, current * 1.10, current * 1.15]
    targets_down = [current * 0.98, current * 0.95, current * 0.90, current * 0.85]

    def prob_of_reaching(target):
        """Simple probability based on normal distribution."""
        move_needed = (target - current) / current
        z = abs(move_needed) / period_vol if period_vol > 0 else 10
        try:
            if z < 1.5:
                prob = max(0.02, np.exp(-0.5 * z * z) * 0.85)
            elif z < 3:
                prob = max(0.02, 0.5 * np.exp(-z))
            else:
                prob = 0.02
        except (OverflowError, FloatingPointError):
            prob = 0.02
        return min(0.95, max(0.02, float(prob)))

    up_probs = [(round(t, 0), round(prob_of_reaching(t) * 100, 0)) for t in targets_up]
    down_probs = [(round(t, 0), round(prob_of_reaching(t) * 100, 0)) for t in targets_down]

    return up_probs, down_probs


def compute_pivot_levels(df):
    """Compute Fibonacci pivot points from previous day data."""
    if len(df) < 2:
        return {'PP': 0, 'R1': 0, 'R2': 0, 'R3': 0, 'S1': 0, 'S2': 0, 'S3': 0}
    last = df.iloc[-1]
    pp = (last['High'] + last['Low'] + last['Close']) / 3
    r = last['High'] - last['Low']  # Previous range
    r1 = pp + 0.382 * r
    r2 = pp + 0.618 * r
    r3 = pp + 1.000 * r
    s1 = pp - 0.382 * r
    s2 = pp - 0.618 * r
    s3 = pp - 1.000 * r
    return {
        'PP': round(pp, 2), 'R1': round(r1, 2), 'R2': round(r2, 2), 'R3': round(r3, 2),
        'S1': round(s1, 2), 'S2': round(s2, 2), 'S3': round(s3, 2),
    }


def compute_daily_key_levels(df, corr_data, signal_sr_levels=None):
    """
    Compute the complete Daily Key Levels package:
    - Previous Day High / Low / Close (PDH/PDL/PDC)
    - Weekly Open, Monthly Open
    - Signal engine S/R zones (from 4H swing points)
    - Key psychological round numbers near price
    - DXY and 10Y yield snapshot
    """
    if len(df) < 2:
        return {
            'current': 0, 'today_open': 0, 'today_high': 0, 'today_low': 0,
            'pdh': 0, 'pdl': 0, 'pdc': 0, 'weekly_open': 0, 'monthly_open': 0,
            'round_numbers': [], 'dxy': {'value': None, 'change_pct': None},
            'tny': {'value': None, 'change': None}, 'sr_zones': [],
        }
    current = df['Close'].iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]

    pdh = round(prev['High'], 2)
    pdl = round(prev['Low'], 2)
    pdc = round(prev['Close'], 2)

    today_high = round(df['High'].iloc[-1], 2)
    today_low = round(df['Low'].iloc[-1], 2)
    today_open = round(df['Open'].iloc[-1], 2)

    try:
        week_start = df.index[-1] - pd.Timedelta(days=df.index[-1].weekday())
        week_data = df[df.index >= week_start]
        weekly_open = round(week_data['Open'].iloc[0], 2) if len(week_data) > 0 else today_open
    except Exception:
        weekly_open = today_open

    try:
        month_start = df.index[-1].replace(day=1)
        month_data = df[df.index >= month_start]
        monthly_open = round(month_data['Open'].iloc[0], 2) if len(month_data) > 0 else today_open
    except Exception:
        monthly_open = today_open

    base = int(current / 50) * 50
    round_numbers = sorted(set([base - 100, base - 50, base, base + 50, base + 100, base + 150]))
    round_numbers = [r for r in round_numbers if abs(r - current) / current < 0.03]

    dxy_val, dxy_chg, tny_val, tny_chg = None, None, None, None
    if 'DXY' in corr_data and len(corr_data['DXY']) >= 2:
        dxy = corr_data['DXY']
        dxy_val = round(dxy['Close'].iloc[-1], 2)
        dxy_chg = round(((dxy['Close'].iloc[-1] / dxy['Close'].iloc[-2]) - 1) * 100, 2)
    if 'US 10Y' in corr_data and len(corr_data['US 10Y']) >= 2:
        tny = corr_data['US 10Y']
        tny_val = round(tny['Close'].iloc[-1], 2)
        tny_chg = round(tny['Close'].iloc[-1] - tny['Close'].iloc[-2], 2)

    sr_zones = []
    if signal_sr_levels:
        for lvl in signal_sr_levels:
            sr_zones.append({'price': lvl['price'], 'type': lvl['type'], 'touches': lvl['touches'], 'strength': lvl['strength']})

    return {
        'current': current, 'today_open': today_open, 'today_high': today_high, 'today_low': today_low,
        'pdh': pdh, 'pdl': pdl, 'pdc': pdc,
        'weekly_open': weekly_open, 'monthly_open': monthly_open,
        'round_numbers': round_numbers,
        'dxy': {'value': dxy_val, 'change_pct': dxy_chg},
        'tny': {'value': tny_val, 'change': tny_chg},
        'sr_zones': sr_zones,
    }


def export_daily_brief_json(key_levels, pivots, ranges, drivers, trade_signals, signal_trend):
    """Export structured JSON for the gold-market-brief skill."""
    bull_count = sum(1 for d in drivers if d[2] == "BULLISH")
    bear_count = sum(1 for d in drivers if d[2] == "BEARISH")
    if bull_count > bear_count + 1:
        session_bias = "BULLISH"
    elif bear_count > bull_count + 1:
        session_bias = "BEARISH"
    else:
        session_bias = "NEUTRAL"

    signals_summary = []
    for s in trade_signals[:3]:
        signals_summary.append({
            'direction': s['direction'], 'pattern': s['pattern_name'],
            'entry': s['entry'], 'stop_loss': s['stop_loss'], 'take_profit': s['take_profit'],
            'confidence': s['confidence'], 'score': s['score'],
        })

    brief_data = {
        'generated_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'date': datetime.utcnow().strftime('%Y-%m-%d'),
        'spot_price': key_levels['current'],
        'intraday_range': {'high': key_levels['today_high'], 'low': key_levels['today_low']},
        'session_bias': session_bias,
        'daily_trend': signal_trend,
        'key_levels': {
            'resistance_3': pivots.get('R3'), 'resistance_2': pivots['R2'], 'resistance_1': pivots['R1'],
            'pivot': pivots['PP'],
            'support_1': pivots['S1'], 'support_2': pivots['S2'], 'support_3': pivots.get('S3'),
            'pdh': key_levels['pdh'], 'pdl': key_levels['pdl'], 'pdc': key_levels['pdc'],
            'weekly_open': key_levels['weekly_open'], 'monthly_open': key_levels['monthly_open'],
            'round_numbers': key_levels['round_numbers'],
            'signal_engine_sr': key_levels['sr_zones'],
        },
        'macro_snapshot': {'dxy': key_levels['dxy'], 'us_10y': key_levels['tny']},
        'drivers': [{'name': d[0], 'detail': d[1], 'impact': d[2], 'why': d[3]} for d in drivers],
        'ranges': {
            'daily': {'range': ranges['today']['range'], 'expected': ranges['today']['expected'], 'utilization_pct': ranges['today']['util']},
            'weekly': {'range': ranges['week']['range'], 'expected': ranges['week']['expected'], 'utilization_pct': ranges['week']['util']},
            'monthly': {'range': ranges['month']['range'], 'expected': ranges['month']['expected'], 'utilization_pct': ranges['month']['util']},
        },
        'active_signals': signals_summary,
    }

    try:
        brief_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'daily_brief_data.json')
        with open(brief_path, 'w') as f:
            json.dump(brief_data, f, indent=2, default=str)
    except Exception:
        pass

    return brief_data


def assess_macro_drivers(gold_df, corr_data):
    """Auto-assess macro drivers based on recent data movements.
    All drivers show: current value + 5D % change for consistency.
    """
    drivers = []

    def _arrow(chg):
        return "↑" if chg > 0 else "↓"

    # DXY
    if 'DXY' in corr_data and len(corr_data['DXY']) >= 5:
        dxy = corr_data['DXY']
        dxy_val = dxy['Close'].iloc[-1]
        dxy_chg = ((dxy_val / dxy['Close'].iloc[-5]) - 1) * 100
        impact = "BEARISH" if dxy_chg > 0.3 else "BULLISH" if dxy_chg < -0.3 else "NEUTRAL"
        why = "Strong $ = gold headwind" if impact == "BEARISH" else "Weak $ = gold tailwind" if impact == "BULLISH" else ""
        drivers.append(("USD (DXY)", f"{dxy_val:.1f} ({_arrow(dxy_chg)} {abs(dxy_chg):.1f}% 5D)", impact, why))

    # US 10Y
    if 'US 10Y' in corr_data and len(corr_data['US 10Y']) >= 5:
        tny = corr_data['US 10Y']
        tny_val = tny['Close'].iloc[-1]
        tny_chg_pct = ((tny_val / tny['Close'].iloc[-5]) - 1) * 100
        impact = "BEARISH" if tny_chg_pct > 1 else "BULLISH" if tny_chg_pct < -1 else "NEUTRAL"
        why = "Rising yields = opportunity cost" if impact == "BEARISH" else "Falling yields = gold supportive" if impact == "BULLISH" else ""
        drivers.append(("US 10Y Yield", f"{tny_val:.2f}% ({_arrow(tny_chg_pct)} {abs(tny_chg_pct):.1f}% 5D)", impact, why))

    # VIX
    if 'VIX' in corr_data and len(corr_data['VIX']) >= 5:
        vix = corr_data['VIX']
        vix_val = vix['Close'].iloc[-1]
        vix_chg = ((vix_val / vix['Close'].iloc[-5]) - 1) * 100
        impact = "BULLISH" if vix_val > 20 else "NEUTRAL"
        why = "High fear = safe haven demand" if impact == "BULLISH" else ""
        drivers.append(("VIX (Fear Index)", f"{vix_val:.1f} ({_arrow(vix_chg)} {abs(vix_chg):.1f}% 5D)", impact, why))

    # Oil
    if 'Crude Oil' in corr_data and len(corr_data['Crude Oil']) >= 5:
        oil = corr_data['Crude Oil']
        oil_val = oil['Close'].iloc[-1]
        oil_chg = ((oil_val / oil['Close'].iloc[-5]) - 1) * 100
        impact = "BULLISH" if oil_chg > 2 else "BEARISH" if oil_chg < -2 else "NEUTRAL"
        why = "Oil up = inflation fear = gold bid" if impact == "BULLISH" else "Oil down = deflation risk" if impact == "BEARISH" else ""
        drivers.append(("Crude Oil", f"${oil_val:.2f} ({_arrow(oil_chg)} {abs(oil_chg):.1f}% 5D)", impact, why))

    # S&P 500
    if 'S&P 500' in corr_data and len(corr_data['S&P 500']) >= 5:
        spx = corr_data['S&P 500']
        spx_val = spx['Close'].iloc[-1]
        spx_chg = ((spx_val / spx['Close'].iloc[-5]) - 1) * 100
        impact = "BULLISH" if spx_chg < -1 else "BEARISH" if spx_chg > 1 else "NEUTRAL"
        why = "Equities falling = risk-off gold bid" if impact == "BULLISH" else "Risk-on = less gold demand" if impact == "BEARISH" else ""
        drivers.append(("S&P 500", f"{spx_val:,.0f} ({_arrow(spx_chg)} {abs(spx_chg):.1f}% 5D)", impact, why))

    # Gold trend
    gold_sma20 = gold_df['SMA_20'].iloc[-1]
    gold_sma50 = gold_df['SMA_50'].iloc[-1] if not pd.isna(gold_df['SMA_50'].iloc[-1]) else gold_sma20
    current = gold_df['Close'].iloc[-1]
    pos = "above" if current > gold_sma20 else "below"
    trend = "BEARISH" if current < gold_sma20 and current < gold_sma50 else "BULLISH" if current > gold_sma20 else "NEUTRAL"
    why = f"Price {pos} key moving averages"
    drivers.append(("Gold Trend (SMA 20/50)", f"Price {pos} 20-SMA (${gold_sma20:,.0f})", trend, why))

    return drivers


def generate_three_tier_analysis(df, spikes_correlated, drivers):
    """Generate beginner, intermediate, and pro analysis."""
    current = df['Close'].iloc[-1]
    prev = df['Close'].iloc[-2]
    daily_chg = current - prev
    daily_pct = (daily_chg / prev) * 100
    rsi = df['RSI'].iloc[-1]
    atr = df['ATR_14'].iloc[-1]
    sma20 = df['SMA_20'].iloc[-1]
    sma50 = df['SMA_50'].iloc[-1] if not pd.isna(df['SMA_50'].iloc[-1]) else None
    bb_upper = df['BB_upper'].iloc[-1]
    bb_lower = df['BB_lower'].iloc[-1]
    macd = df['MACD'].iloc[-1]
    macd_sig = df['MACD_signal'].iloc[-1]

    # Count bullish/bearish drivers
    bull_count = sum(1 for d in drivers if d[2] == "BULLISH")
    bear_count = sum(1 for d in drivers if d[2] == "BEARISH")

    direction = "up" if daily_chg >= 0 else "down"
    trend_word = "rising" if current > sma20 else "falling"

    # Recent spike context
    spike_context = ""
    if spikes_correlated:
        last_spike = spikes_correlated[0]
        spike_news = last_spike['news'][0]['title'] if last_spike['news'] else "No specific catalyst identified"
        spike_context = f"The most recent volume spike was on {last_spike['date']} ({last_spike['direction']}, {last_spike['vol_ratio']:.1f}x avg volume). Likely catalyst: {spike_news}"

    # ─── BEGINNER ─── (using HTML tags to avoid markdown $ rendering issues)
    rsi_text = f'The RSI is at {rsi:.0f}, which means gold is <b>oversold</b> (potentially due for a bounce).' if rsi < 30 else f'The RSI is at {rsi:.0f}, which means gold is <b>overbought</b> (may pull back soon).' if rsi > 70 else f'The RSI is at {rsi:.0f}, in neutral territory.'

    beginner = f"""<p>Gold is currently at <b>${current:,.2f}</b>, {'up' if daily_chg >=0 else 'down'} <b>${abs(daily_chg):,.2f}</b> today ({daily_pct:+.2f}%).</p>

<p>The price is <b>{'above' if current > sma20 else 'below'}</b> its 20-day average (${sma20:,.2f}), which suggests the short-term trend is <b>{'positive' if current > sma20 else 'negative'}</b>.</p>

<p>{rsi_text}</p>

<p><b>What's driving gold right now:</b> {bull_count} factors are pushing gold higher (like geopolitical tensions and market fear), while {bear_count} factors are pushing it lower (like a stronger dollar or higher interest rates).</p>

<p style="font-size:11px;color:#a8b2c8;border-top:1px solid #1e2745;padding-top:8px;margin-top:8px;">{spike_context}</p>"""

    # ─── INTERMEDIATE ───
    bb_position = "near upper band" if current > bb_upper * 0.99 else "near lower band" if current < bb_lower * 1.01 else "mid-range"
    macd_signal = "bullish crossover" if macd > macd_sig else "bearish crossover"

    intermediate = f"""<p><b>Price:</b> ${current:,.2f} ({daily_pct:+.2f}%) &nbsp;|&nbsp; <b>Trend:</b> {'Bullish' if current > sma20 else 'Bearish'} below {'20 &amp; 50 SMA' if sma50 and current < sma50 else '20 SMA'}</p>

<p><b>Technical Setup:</b></p>
<ul style="margin:4px 0;padding-left:18px;font-size:12px;">
<li>RSI(14): {rsi:.1f} {'⚠️ Oversold' if rsi < 30 else '⚠️ Overbought' if rsi > 70 else ''}</li>
<li>MACD: {macd_signal} (MACD {macd:.2f} vs Signal {macd_sig:.2f})</li>
<li>Bollinger Bands: {bb_position} (${bb_lower:,.0f} — ${bb_upper:,.0f})</li>
<li>ATR(14): ${atr:,.2f} (expected daily range)</li>
<li>Volume: {'Above' if df['Vol_ratio'].iloc[-1] > 1 else 'Below'} average ({df['Vol_ratio'].iloc[-1]:.1f}x)</li>
</ul>

<p><b>Key levels to watch:</b> Support at ${sma20:,.0f} (20 SMA){', $' + f'{sma50:,.0f}' + ' (50 SMA)' if sma50 else ''}. Resistance at ${bb_upper:,.0f} (upper BB).</p>

<p style="font-size:11px;color:#a8b2c8;border-top:1px solid #1e2745;padding-top:8px;margin-top:8px;">{spike_context}</p>"""

    # ─── PRO ───
    vol_regime = "high" if df['Close'].pct_change().tail(20).std() > df['Close'].pct_change().tail(60).std() else "low"

    pro = f"""<p><b>Regime:</b> {vol_regime.upper()} volatility | ATR ${atr:,.2f} | 20D realized vol: {df['Close'].pct_change().tail(20).std()*100*np.sqrt(252):.1f}% annualized</p>

<p><b>Momentum:</b> RSI {rsi:.1f} | MACD histogram {'expanding' if abs(df['MACD_hist'].iloc[-1]) > abs(df['MACD_hist'].iloc[-2]) else 'contracting'} ({df['MACD_hist'].iloc[-1]:+.2f}) | Price {'compressed within' if (bb_upper - bb_lower) / current < 0.04 else 'wide'} BB ({((bb_upper-bb_lower)/current)*100:.1f}% width)</p>

<p><b>Cross-asset snapshot:</b> {'Negative DXY correlation in play — ' if any(d[0] == 'USD (DXY)' and d[2] == 'BEARISH' for d in drivers) else ''}{'Yields rising = headwind — ' if any('10Y' in d[0] and d[2] == 'BEARISH' for d in drivers) else ''}{'VIX elevated = risk-off bid — ' if any('VIX' in d[0] and d[2] == 'BULLISH' for d in drivers) else ''}{'Equities weak = safe haven flow' if any('S&P' in d[0] and d[2] == 'BULLISH' for d in drivers) else ''}</p>

<p><b>Volume profile:</b> Last session {df['Vol_ratio'].iloc[-1]:.1f}x avg. {len([s for s in spikes_correlated if s['vol_ratio'] > 2]) if spikes_correlated else 0} sessions with &gt;2x volume in past month.</p>

<p><b>Positioning note:</b> Monitor COT report (Fridays) for net speculative positioning changes. Current macro mix ({bull_count}B/{bear_count}B) suggests a choppy range environment.</p>

{spike_context}"""

    return beginner, intermediate, pro


def generate_daily_brief_text(current, daily_chg, daily_pct, rsi, atr, drivers, trade_signals, signal_trend, ranges, pivots, key_levels):
    """Generate a plain-English daily brief summary for the top of the dashboard."""
    # Direction
    direction = "up" if daily_chg >= 0 else "down"
    dir_class = "highlight-up" if daily_chg >= 0 else "highlight-down"

    # Session bias from drivers
    bull_count = sum(1 for d in drivers if d[2] == "BULLISH")
    bear_count = sum(1 for d in drivers if d[2] == "BEARISH")
    if bull_count > bear_count + 1:
        bias = "BULLISH"
        bias_color = "#10b981"
        bias_bg = "rgba(16,185,129,0.12)"
        bias_word = "bullish"
    elif bear_count > bull_count + 1:
        bias = "BEARISH"
        bias_color = "#ef4444"
        bias_bg = "rgba(239,68,68,0.12)"
        bias_word = "bearish"
    else:
        bias = "NEUTRAL"
        bias_color = "#f59e0b"
        bias_bg = "rgba(245,158,11,0.12)"
        bias_word = "mixed"

    # Key driver (most impactful)
    key_drivers_text = []
    for d in drivers:
        name, detail, impact = d[0], d[1], d[2]
        if impact != "NEUTRAL":
            key_drivers_text.append(f"{name} ({detail})")
    top_drivers = ", ".join(key_drivers_text[:3]) if key_drivers_text else "no strong macro catalysts"

    # RSI context
    if rsi < 30:
        rsi_text = f'RSI at <span class="highlight-down">{rsi:.0f} (oversold)</span> — bounce potential'
    elif rsi > 70:
        rsi_text = f'RSI at <span class="highlight-up">{rsi:.0f} (overbought)</span> — pullback risk'
    else:
        rsi_text = f"RSI at {rsi:.0f} (neutral zone)"

    # Range context
    daily_util = ranges['today']['util']
    if daily_util > 100:
        range_text = f"Today's range has <b>exceeded</b> the ATR-expected move ({daily_util:.0f}% utilized) — extended conditions."
    elif daily_util > 70:
        range_text = f"Today's range is nearing the expected daily move ({daily_util:.0f}% of ATR used)."
    else:
        range_text = f"Today's range has room to expand ({daily_util:.0f}% of expected ATR used)."

    # Signal summary
    if trade_signals:
        top_sig = trade_signals[0]
        sig_text = (f'The signal engine has detected a <b>{top_sig["direction"]}</b> setup '
                   f'({top_sig["confidence"]} confidence, score {top_sig["score"]}) '
                   f'based on a {top_sig["pattern_name"]} at ${top_sig["level_price"]:,.2f}.')
    else:
        sig_text = "No active trade signals right now — the engine is scanning for setups at key levels."

    # Key levels to watch
    nearest_support = pivots['S1']
    nearest_resistance = pivots['R1']
    levels_text = (f'Key levels: support at <span class="highlight-up">${nearest_support:,.0f}</span>, '
                  f'resistance at <span class="highlight-down">${nearest_resistance:,.0f}</span> (Fibonacci pivots).')

    # Compose the brief
    brief_html = (
        f'<p>Gold is trading at <b>${current:,.2f}</b>, '
        f'<span class="{dir_class}">{direction} ${abs(daily_chg):,.2f} ({daily_pct:+.2f}%)</span> on the session. '
        f'The daily trend is <b>{signal_trend.replace("_", " ").lower()}</b> and macro conditions are <b>{bias_word}</b> — '
        f'driven by {top_drivers}.</p>'
        f'<p>{rsi_text}. {range_text}</p>'
        f'<p>{sig_text}</p>'
        f'<p>{levels_text}</p>'
    )

    return brief_html, bias, bias_color, bias_bg


# ═══════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════
def main():
    # ── Header ──
    st.markdown("""
    <div class="gold-header">
        <div>
            <h1 style="margin:0;">GOLD COMMAND</h1>
            <span class="sub">XAU/USD Market Intelligence Terminal</span>
            <div style="font-size:9px;color:#5a6a8a;margin-top:3px;letter-spacing:0.5px;">Developed by <span style="color:#f0b90b;">Anoop B.</span></div>
        </div>
        <div style="display:flex; align-items:center; gap:16px;">
            <span class="live-badge"><span class="live-dot"></span>LIVE DATA</span>
            <span style="font-family:'JetBrains Mono'; font-size:11px; color:#6b7a99;">""" +
    datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC') + """</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Auto-Refresh Controls ──
    with st.sidebar:
        st.markdown("### Auto-Refresh")
        auto_refresh = st.toggle("Enable auto-refresh", value=True)
        refresh_interval = st.select_slider(
            "Refresh interval",
            options=[5, 10, 15, 30, 60],
            value=15,
            format_func=lambda x: f"{x} min"
        )
        if st.button("Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        # Show last refresh and next refresh time
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = time.time()

        elapsed = time.time() - st.session_state.last_refresh
        next_in = max(0, refresh_interval * 60 - elapsed)
        st.markdown(f"""<div style="font-size:11px;color:#6b7a99;margin-top:8px;">
            Last refresh: {int(elapsed)}s ago<br>
            Next refresh: {int(next_in)}s
        </div>""", unsafe_allow_html=True)

    # Auto-refresh trigger
    if auto_refresh:
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = time.time()
        elapsed = time.time() - st.session_state.last_refresh
        if elapsed >= refresh_interval * 60:
            st.session_state.last_refresh = time.time()
            st.cache_data.clear()
            st.rerun()

    # ── Fetch all data ──
    with st.spinner("Fetching market data..."):
        try:
            gold_df = fetch_gold_data(period="6mo", interval="1d")
        except Exception as e:
            gold_df = pd.DataFrame()
            logger.error(f"Unhandled error fetching gold data: {e}")
        try:
            corr_data = fetch_correlated_data(period="3mo")
        except Exception as e:
            corr_data = {}
            logger.error(f"Unhandled error fetching correlated data: {e}")
        try:
            news = fetch_gold_news()
        except Exception as e:
            news = []
            logger.error(f"Unhandled error fetching news: {e}")

    if gold_df.empty:
        st.error("⚠️ Market data temporarily unavailable — Yahoo Finance rate limit hit. This usually resolves in 1-2 minutes.")
        st.info("Click the **Rerun** button in the top-right corner or wait for auto-refresh.")
        return

    # ── Compute everything ──
    gold_df = compute_indicators(gold_df)
    spikes = detect_volume_spikes(gold_df, threshold=1.5)
    spikes_correlated = correlate_news_to_spikes(spikes, news)
    correlations = compute_correlations(gold_df, corr_data)
    up_probs, down_probs = compute_probability_targets(gold_df)
    pivots = compute_pivot_levels(gold_df)
    ranges = compute_ranges(gold_df)
    drivers = assess_macro_drivers(gold_df, corr_data)
    beginner, intermediate, pro = generate_three_tier_analysis(gold_df, spikes_correlated, drivers)

    current = gold_df['Close'].iloc[-1]
    prev = gold_df['Close'].iloc[-2]
    daily_chg = current - prev
    daily_pct = (daily_chg / prev) * 100
    high_52w = gold_df['High'].max()
    low_52w = gold_df['Low'].min()

    # ── Signal Engine (cached — 5 min TTL) ──
    @st.cache_data(ttl=600)
    def _run_signal_engine():
        _signals, _trend, _sr = [], "NEUTRAL", []
        try:
            mtf_data = fetch_multi_timeframe(GOLD_TICKER)
            if mtf_data:
                _signals = generate_signals(mtf_data, max_signals=5)
                if 'daily' in mtf_data:
                    from signal_engine import detect_trend
                    _trend, _, _ = detect_trend(mtf_data['daily'])
                if '4h' in mtf_data:
                    from signal_engine import find_sr_levels
                    _sr = find_sr_levels(mtf_data['4h'], lookback=5, merge_threshold_pct=0.4)
        except Exception:
            pass
        return _signals, _trend, _sr

    with st.spinner("Running signal engine..."):
        trade_signals, signal_trend, signal_sr_levels = _run_signal_engine()

    # ── Daily Key Levels + JSON export ──
    key_levels = compute_daily_key_levels(gold_df, corr_data, signal_sr_levels)
    brief_data = export_daily_brief_json(key_levels, pivots, ranges, drivers, trade_signals, signal_trend)

    # ══════════════════════════════════════════════════
    # DAILY BRIEF — Quick Summary Card
    # ══════════════════════════════════════════════════
    rsi_val = gold_df['RSI'].iloc[-1]
    brief_text, brief_bias, brief_bias_color, brief_bias_bg = generate_daily_brief_text(
        current, daily_chg, daily_pct, rsi_val,
        gold_df['ATR_14'].iloc[-1], drivers, trade_signals,
        signal_trend, ranges, pivots, key_levels
    )

    brief_date = datetime.utcnow().strftime('%B %d, %Y')
    brief_card_html = (
        f'<div class="daily-brief">'
        f'<div class="daily-brief-header">'
        f'<div class="daily-brief-title">'
        f'<span style="font-size:16px;">&#9889;</span> Daily Brief '
        f'<span style="font-size:9px;color:#6b7a99;font-weight:400;letter-spacing:0.5px;">'
        f'{brief_date} &middot; Auto-generated from live data</span>'
        f'</div>'
        f'<span class="brief-bias-badge" style="background:{brief_bias_bg};color:{brief_bias_color};border:1px solid {brief_bias_color}33;">'
        f'{brief_bias}</span>'
        f'</div>'
        f'<div class="daily-brief-body">{brief_text}</div>'
        f'</div>'
    )
    st.markdown(brief_card_html, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # TOP KPI ROW — Custom HTML Cards
    # ══════════════════════════════════════════════════
    rsi_status = "OVERSOLD" if rsi_val < 30 else "OVERBOUGHT" if rsi_val > 70 else "NEUTRAL"
    rsi_color = "#ef4444" if rsi_val < 30 else "#f59e0b" if rsi_val > 70 else "#10b981"
    vol_r = gold_df['Vol_ratio'].iloc[-1]
    vol_status = "HIGH" if vol_r > 1.5 else "LOW" if vol_r < 0.7 else "NORMAL"
    vol_color = "#f59e0b" if vol_r > 1.5 else "#5a6a8a" if vol_r < 0.7 else "#10b981"
    chg_color = "#10b981" if daily_chg >= 0 else "#ef4444"
    chg_arrow = "&#9650;" if daily_chg >= 0 else "&#9660;"

    # Session bias for KPI card (replaces volume card)
    bull_count = sum(1 for d in drivers if d[2] == "BULLISH")
    bear_count = sum(1 for d in drivers if d[2] == "BEARISH")
    bias_kpi_label = brief_bias
    bias_kpi_color = brief_bias_color
    bias_kpi_bg = brief_bias_bg

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card" style="--kpi-accent: #f0b90b;">
            <div class="kpi-label">Gold Price</div>
            <div class="kpi-value" style="color: #f0b90b;">${current:,.2f}</div>
            <div class="kpi-delta {'up' if daily_chg >= 0 else 'down'}">{chg_arrow} ${abs(daily_chg):,.2f} ({daily_pct:+.1f}%)</div>
        </div>
        <div class="kpi-card" style="--kpi-accent: {rsi_color};">
            <div class="kpi-label">RSI (14)</div>
            <div class="kpi-value">{rsi_val:.1f}</div>
            <div class="kpi-delta neutral" style="color:{rsi_color};background:rgba(0,0,0,0.2);">{rsi_status}</div>
        </div>
        <div class="kpi-card" style="--kpi-accent: #3b82f6;">
            <div class="kpi-label">ATR (14)</div>
            <div class="kpi-value">${gold_df['ATR_14'].iloc[-1]:,.0f}</div>
            <div class="kpi-delta neutral">Daily Range</div>
        </div>
        <div class="kpi-card" style="--kpi-accent: #ef4444;">
            <div class="kpi-label">6M High</div>
            <div class="kpi-value">${high_52w:,.0f}</div>
            <div class="kpi-delta {'down' if current < high_52w else 'up'}">{((current/high_52w)-1)*100:+.1f}%</div>
        </div>
        <div class="kpi-card" style="--kpi-accent: #10b981;">
            <div class="kpi-label">6M Low</div>
            <div class="kpi-value">${low_52w:,.0f}</div>
            <div class="kpi-delta up">{((current/low_52w)-1)*100:+.1f}%</div>
        </div>
        <div class="kpi-card" style="--kpi-accent: {bias_kpi_color};">
            <div class="kpi-label">Session Bias</div>
            <div class="kpi-value" style="color:{bias_kpi_color};font-size:18px;">{bias_kpi_label}</div>
            <div class="kpi-delta neutral" style="color:{bias_kpi_color};background:rgba(0,0,0,0.2);">{bull_count}B / {bear_count}B drivers</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # RANGE ANALYSIS ROW
    # ══════════════════════════════════════════════════
    st.markdown("""<div class="section-header" style="--section-accent: #3b82f6;">
        <span class="section-title">Price Ranges</span>
        <span class="pill pill-data">DAILY / WEEKLY / MONTHLY</span>
    </div>""", unsafe_allow_html=True)

    rc1, rc2, rc3 = st.columns(3)

    for col, label, key in [(rc1, "Today", "today"), (rc2, "This Week (5D)", "week"), (rc3, "This Month (22D)", "month")]:
        r = ranges[key]
        util_color = "#10b981" if r['util'] < 80 else "#f59e0b" if r['util'] < 120 else "#ef4444"
        bar_width = min(r['util'], 150)  # cap at 150% for display
        with col:
            st.markdown(f"""<div class="range-card">
                <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                    <span style="font-size:11px;font-weight:700;color:#a8b2c8;text-transform:uppercase;letter-spacing:0.5px;">{label}</span>
                    <span style="font-size:10px;font-weight:700;color:{util_color};">{r['util']:.0f}% of expected</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-family:JetBrains Mono;font-size:13px;margin-bottom:4px;">
                    <span style="color:#10b981;">L: ${r['low']:,.2f}</span>
                    <span style="color:#f0b90b;font-weight:700;">${r['range']:,.2f}</span>
                    <span style="color:#ef4444;">H: ${r['high']:,.2f}</span>
                </div>
                <div class="prob-bar" style="height:8px;margin:6px 0;">
                    <div class="prob-fill" style="width:{bar_width}%;background:linear-gradient(90deg,#10b981,{util_color});border-radius:3px;"></div>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:10px;color:#6b7a99;">
                    <span>Avg: ${r['avg']:,.2f}</span>
                    <span>ATR Expected: ${r['expected']:,.2f}</span>
                </div>
            </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # DAILY KEY LEVELS — The Game Plan
    # ══════════════════════════════════════════════════
    bull_d = sum(1 for d in drivers if d[2] == "BULLISH")
    bear_d = sum(1 for d in drivers if d[2] == "BEARISH")
    if bull_d > bear_d + 1:
        bias_label, bias_color, bias_bg = "BULLISH", "#10b981", "rgba(16,185,129,0.12)"
    elif bear_d > bull_d + 1:
        bias_label, bias_color, bias_bg = "BEARISH", "#ef4444", "rgba(239,68,68,0.12)"
    else:
        bias_label, bias_color, bias_bg = "NEUTRAL", "#f59e0b", "rgba(245,158,11,0.12)"

    st.markdown(f"""<div class="section-header" style="--section-accent: #f0b90b;">
        <div>
            <span class="section-title">Daily Key Levels</span>
            <div style="display:flex;align-items:center;gap:10px;margin-top:6px;">
                <span style="font-size:10px;font-weight:800;padding:4px 12px;border-radius:4px;background:{bias_bg};color:{bias_color};letter-spacing:0.5px;">
                    Session Bias: {bias_label}</span>
                <span style="font-size:9px;color:#5a6a8a;letter-spacing:0.5px;">
                    Shared with Gold Intel Daily Brief</span>
            </div>
        </div>
        <span class="pill pill-live">GAME PLAN</span>
    </div>""", unsafe_allow_html=True)

    lv1, lv2, lv3, lv4 = st.columns(4)

    with lv1:
        st.markdown(f"""<div class="intel-card" style="padding:12px 14px;">
            <div style="font-size:10px;font-weight:700;color:#a8b2c8;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Session Levels</div>
            <div class="level-row"><span style="color:#6b7a99;font-size:10px;">Today Open</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#e8ecf4;">${key_levels['today_open']:,.2f}</span></div>
            <div class="level-row"><span style="color:#6b7a99;font-size:10px;">Today High</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#10b981;">${key_levels['today_high']:,.2f}</span></div>
            <div class="level-row"><span style="color:#6b7a99;font-size:10px;">Today Low</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#ef4444;">${key_levels['today_low']:,.2f}</span></div>
            <div style="border-top:1px solid #1e2745;margin:6px 0;"></div>
            <div class="level-row"><span style="color:#f0b90b;font-size:10px;font-weight:600;">Prev Day High</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#f0b90b;">${key_levels['pdh']:,.2f}</span></div>
            <div class="level-row"><span style="color:#f0b90b;font-size:10px;font-weight:600;">Prev Day Low</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#f0b90b;">${key_levels['pdl']:,.2f}</span></div>
            <div class="level-row"><span style="color:#f0b90b;font-size:10px;font-weight:600;">Prev Day Close</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#f0b90b;">${key_levels['pdc']:,.2f}</span></div>
        </div>""", unsafe_allow_html=True)

    with lv2:
        st.markdown(f"""<div class="intel-card" style="padding:12px 14px;">
            <div style="font-size:10px;font-weight:700;color:#a8b2c8;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Pivot Points</div>
            <div class="level-row"><span style="color:#ef4444;font-size:10px;">R3</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#ef4444;">${pivots['R3']:,.2f}</span></div>
            <div class="level-row"><span style="color:#ef4444;font-size:10px;">R2</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#ef4444;">${pivots['R2']:,.2f}</span></div>
            <div class="level-row"><span style="color:#ef4444;font-size:10px;">R1</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#ef4444;">${pivots['R1']:,.2f}</span></div>
            <div class="level-row" style="background:rgba(240,185,11,0.08);border-radius:4px;padding:4px 6px;">
                <span style="color:#f0b90b;font-size:10px;font-weight:700;">PIVOT</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#f0b90b;font-weight:700;">${pivots['PP']:,.2f}</span></div>
            <div class="level-row"><span style="color:#10b981;font-size:10px;">S1</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#10b981;">${pivots['S1']:,.2f}</span></div>
            <div class="level-row"><span style="color:#10b981;font-size:10px;">S2</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#10b981;">${pivots['S2']:,.2f}</span></div>
            <div class="level-row"><span style="color:#10b981;font-size:10px;">S3</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#10b981;">${pivots['S3']:,.2f}</span></div>
        </div>""", unsafe_allow_html=True)

    with lv3:
        sr_html = ""
        if signal_sr_levels:
            for lvl in sorted(signal_sr_levels, key=lambda x: x['price'], reverse=True)[:6]:
                lvl_color = "#ef4444" if lvl['type'] == 'resistance' else "#10b981"
                lvl_icon = "R" if lvl['type'] == 'resistance' else "S"
                sr_html += f"""<div class="level-row">
                    <span style="color:{lvl_color};font-size:10px;">{lvl_icon} ({lvl['touches']}x)</span>
                    <span style="font-family:JetBrains Mono;font-size:12px;color:{lvl_color};">${lvl['price']:,.2f}</span>
                </div>"""
        else:
            sr_html = '<div style="font-size:11px;color:#6b7a99;padding:6px 0;">No S/R zones computed</div>'

        round_html = ""
        for rn in key_levels['round_numbers']:
            round_html += f"""<div class="level-row">
                <span style="color:#a855f7;font-size:10px;">Psych</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#a855f7;">${rn:,.0f}</span>
            </div>"""

        st.markdown(f"""<div class="intel-card" style="padding:12px 14px;">
            <div style="font-size:10px;font-weight:700;color:#a8b2c8;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">4H S/R Zones (Signal Engine)</div>
            {sr_html}
            <div style="border-top:1px solid #1e2745;margin:6px 0;"></div>
            <div style="font-size:10px;font-weight:700;color:#a8b2c8;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Round Numbers</div>
            {round_html}
        </div>""", unsafe_allow_html=True)

    with lv4:
        dxy_info = f"${key_levels['dxy']['value']}" if key_levels['dxy']['value'] else "N/A"
        dxy_delta = f"({key_levels['dxy']['change_pct']:+.2f}%)" if key_levels['dxy']['change_pct'] else ""
        tny_info = f"{key_levels['tny']['value']}%" if key_levels['tny']['value'] else "N/A"
        tny_delta = f"({key_levels['tny']['change']:+.2f})" if key_levels['tny']['change'] else ""

        st.markdown(f"""<div class="intel-card" style="padding:12px 14px;">
            <div style="font-size:10px;font-weight:700;color:#a8b2c8;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Anchors</div>
            <div class="level-row"><span style="color:#3b82f6;font-size:10px;">Weekly Open</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#3b82f6;">${key_levels['weekly_open']:,.2f}</span></div>
            <div class="level-row"><span style="color:#3b82f6;font-size:10px;">Monthly Open</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#3b82f6;">${key_levels['monthly_open']:,.2f}</span></div>
            <div style="border-top:1px solid #1e2745;margin:6px 0;"></div>
            <div style="font-size:10px;font-weight:700;color:#a8b2c8;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Macro Snapshot</div>
            <div class="level-row"><span style="color:#6b7a99;font-size:10px;">DXY</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#e8ecf4;">{dxy_info} <span style="font-size:10px;color:#6b7a99;">{dxy_delta}</span></span></div>
            <div class="level-row"><span style="color:#6b7a99;font-size:10px;">US 10Y Yield</span>
                <span style="font-family:JetBrains Mono;font-size:12px;color:#e8ecf4;">{tny_info} <span style="font-size:10px;color:#6b7a99;">{tny_delta}</span></span></div>
            <div style="border-top:1px solid #1e2745;margin:6px 0;"></div>
            <div style="font-size:9px;color:#6b7a99;line-height:1.5;">
                Data exported to <b style="color:#a8b2c8;">daily_brief_data.json</b><br>
                Gold Intel Daily skill reads this file.
            </div>
        </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # SIGNAL ENGINE — Trade Signals
    # ══════════════════════════════════════════════════
    trend_color_map = {
        "BULLISH": ("#10b981", "rgba(16,185,129,0.12)"),
        "WEAK_BULLISH": ("#10b981", "rgba(16,185,129,0.08)"),
        "BEARISH": ("#ef4444", "rgba(239,68,68,0.12)"),
        "WEAK_BEARISH": ("#ef4444", "rgba(239,68,68,0.08)"),
        "NEUTRAL": ("#f59e0b", "rgba(245,158,11,0.12)"),
    }
    tc, tbg = trend_color_map.get(signal_trend, ("#f59e0b", "rgba(245,158,11,0.12)"))
    trend_label = signal_trend.replace("_", " ")

    st.markdown(f"""<div class="section-header" style="--section-accent: {tc};">
        <div>
            <span class="section-title">Trade Signals</span>
            <div style="display:flex;align-items:center;gap:10px;margin-top:6px;">
                <span class="signal-trend-badge" style="background:{tbg};color:{tc};letter-spacing:0.5px;">Daily Trend: {trend_label}</span>
                <span style="font-size:9px;color:#5a6a8a;">Multi-timeframe: Daily &gt; 4H zones &gt; 15m entry patterns</span>
            </div>
        </div>
        <span class="pill pill-live">SIGNAL ENGINE</span>
    </div>""", unsafe_allow_html=True)

    if trade_signals:
        sig_cols = st.columns(min(len(trade_signals), 3))
        for i, signal in enumerate(trade_signals[:6]):
            formatted = format_signal_for_beginner(signal)
            col = sig_cols[i % min(len(trade_signals), 3)]

            direction = signal['direction'].lower()
            conf = signal.get('confidence', 'LOW')
            conf_class = 'conf-high' if conf == 'HIGH' else 'conf-med' if conf == 'MEDIUM' else 'conf-low'
            score = signal.get('score', 0)

            if score >= 80:
                ring_bg, ring_border, ring_color = "rgba(16,185,129,0.15)", "#10b981", "#10b981"
            elif score >= 65:
                ring_bg, ring_border, ring_color = "rgba(245,158,11,0.15)", "#f59e0b", "#f59e0b"
            else:
                ring_bg, ring_border, ring_color = "rgba(107,122,153,0.15)", "#6b7a99", "#6b7a99"

            reasons_html = ""
            for reason in formatted.get('reasons', []):
                reasons_html += f'<span class="signal-reason-tag">{reason}</span>'

            levels_html = ""
            if formatted.get('entry'):
                levels_html = f"""<div class="signal-levels">
                    <div class="signal-level-item">
                        <div class="signal-level-label">Entry</div>
                        <div class="signal-level-value" style="color:#e8ecf4;">{formatted['entry']}</div>
                    </div>
                    <div class="signal-level-item">
                        <div class="signal-level-label">Stop Loss</div>
                        <div class="signal-level-value" style="color:#ef4444;">${signal['stop_loss']:,.2f}</div>
                    </div>
                    <div class="signal-level-item">
                        <div class="signal-level-label">Take Profit</div>
                        <div class="signal-level-value" style="color:#10b981;">${signal['take_profit']:,.2f}</div>
                    </div>
                    <div class="signal-level-item">
                        <div class="signal-level-label">Risk:Reward</div>
                        <div class="signal-level-value" style="color:#f0b90b;">{formatted.get('rr', 'N/A')}</div>
                    </div>
                </div>"""

            time_str = signal['time'].strftime('%b %d, %H:%M') if hasattr(signal['time'], 'strftime') else str(signal['time'])[:16]

            with col:
                st.markdown(f"""<div class="signal-card {direction}">
                    <div class="signal-score-ring" style="background:{ring_bg};border:2px solid {ring_border};color:{ring_color};">
                        {score}
                    </div>
                    <div class="signal-badge {direction}">{formatted['emoji']} {signal['direction']}</div>
                    <span class="signal-conf {conf_class}">{conf} confidence</span>
                    <div style="font-size:10px;color:#6b7a99;margin-top:4px;">{time_str} · {signal['timeframe']} · {signal['pattern_name']}</div>
                    <div class="signal-explanation">{formatted['explanation']}</div>
                    {levels_html}
                    <div class="signal-reasons">{reasons_html}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="signal-empty">
            <div style="font-size:24px;margin-bottom:8px;">&#9203;</div>
            <div style="font-weight:600;color:#a8b2c8;margin-bottom:4px;">No Active Signals</div>
            <div>No candle patterns detected at key support/resistance levels right now.<br>
            The engine scans 15-minute bars at 4H-derived S/R zones aligned with the daily trend.</div>
        </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # FULL-WIDTH TRADINGVIEW CHART
    # ══════════════════════════════════════════════════
    tv_html = """
    <html><head><style>
      *{margin:0;padding:0;} html,body{width:100%;height:100%;overflow:hidden;background:#0a0e17;}
      .tradingview-widget-container{width:100%;height:100%;}
      .tradingview-widget-container__widget{width:100%;height:100%;}
    </style></head><body>
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
      {
        "autosize":true,
        "symbol":"OANDA:XAUUSD",
        "interval":"15",
        "timezone":"Etc/UTC",
        "theme":"dark",
        "style":"1",
        "locale":"en",
        "backgroundColor":"rgba(10,14,23,1)",
        "gridColor":"rgba(30,39,69,0.4)",
        "withdateranges":true,
        "hide_side_toolbar":false,
        "allow_symbol_change":true,
        "details":false,
        "hotlist":false,
        "calendar":false,
        "studies":["BB@tv-basicstudies","Volume@tv-basicstudies"],
        "support_host":"https://www.tradingview.com"
      }
      </script>
    </div>
    </body></html>
    """
    st.components.v1.html(tv_html, height=650)

    # ══════════════════════════════════════════════════
    # INTELLIGENCE GRID — 3 columns below chart
    # ══════════════════════════════════════════════════
    col_analysis, col_drivers, col_data = st.columns([2, 1, 1])

    with col_analysis:
        # ── 3-TIER ANALYSIS ──
        st.markdown("""<div class="section-header" style="--section-accent: #a855f7;">
            <span class="section-title">Analysis</span>
            <span class="pill pill-model">3-TIER</span>
        </div>""", unsafe_allow_html=True)

        tier = st.radio("Perspective", ["Beginner", "Intermediate", "Pro"], horizontal=True, label_visibility="collapsed")

        if tier == "Beginner":
            st.markdown(f'<div class="tier-tab tier-beginner"><div class="tier-label" style="color:#3b82f6;">Beginner View</div>{beginner}</div>', unsafe_allow_html=True)
        elif tier == "Intermediate":
            st.markdown(f'<div class="tier-tab tier-intermediate"><div class="tier-label" style="color:#f59e0b;">Intermediate View</div>{intermediate}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="tier-tab tier-pro"><div class="tier-label" style="color:#a855f7;">Pro View</div>{pro}</div>', unsafe_allow_html=True)

    with col_drivers:
        # ── MACRO DRIVERS ──
        st.markdown("""<div class="intel-card"><h3 style="margin-bottom:14px;">Macro Drivers
            <span class="pill pill-data">AUTO-COMPUTED</span></h3>""", unsafe_allow_html=True)
        for d in drivers:
            name, detail, impact, why = d[0], d[1], d[2], d[3]
            tag_class = "tag-bull" if impact == "BULLISH" else "tag-bear" if impact == "BEARISH" else "tag-mixed"
            why_html = f'<br><small style="color:#8892ab;font-style:italic;">{why}</small>' if why else ''
            st.markdown(f"""<div class="driver-row">
                <span>{name}<br><small style="color:#6b7a99">{detail}</small>{why_html}</span>
                <span class="{tag_class}">{impact}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── CORRELATIONS ──
        st.markdown("""<div class="intel-card"><h3>30D Correlations
            <span class="pill pill-model">COMPUTED</span></h3>""", unsafe_allow_html=True)
        for name, val in correlations.items():
            color = "#10b981" if val > 0.3 else "#ef4444" if val < -0.3 else "#6b7a99"
            bg = "rgba(16,185,129,0.12)" if val > 0.3 else "rgba(239,68,68,0.12)" if val < -0.3 else "rgba(107,122,153,0.08)"
            st.markdown(f"""<div style="display:flex;justify-content:space-between;padding:4px 0;font-size:12px;">
                <span>{name}</span>
                <span class="corr-cell" style="background:{bg};color:{color};padding:2px 10px;border-radius:3px;min-width:55px;">{val:+.2f}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_data:
        # ── KEY LEVELS ──
        st.markdown("""<div class="intel-card"><h3>Key Levels
            <span class="pill pill-data">PIVOT + S/R</span></h3>""", unsafe_allow_html=True)
        pcol1, pcol2 = st.columns(2)
        with pcol1:
            st.markdown("<b style='color:#10b981;font-size:11px;'>Support</b>", unsafe_allow_html=True)
            for label, val in [("Pivot S1", pivots['S1']), ("Pivot S2", pivots['S2']), ("Pivot S3", pivots['S3'])]:
                st.markdown(f'<div class="level-row"><span style="color:#10b981;font-family:JetBrains Mono">${val:,.0f}</span><span style="font-size:9px;color:#6b7a99">{label}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="level-row"><span style="color:#10b981;font-family:JetBrains Mono">${gold_df["SMA_20"].iloc[-1]:,.0f}</span><span style="font-size:9px;color:#6b7a99">SMA 20</span></div>', unsafe_allow_html=True)
        with pcol2:
            st.markdown("<b style='color:#ef4444;font-size:11px;'>Resistance</b>", unsafe_allow_html=True)
            for label, val in [("Pivot R1", pivots['R1']), ("Pivot R2", pivots['R2']), ("Pivot R3", pivots['R3'])]:
                st.markdown(f'<div class="level-row"><span style="color:#ef4444;font-family:JetBrains Mono">${val:,.0f}</span><span style="font-size:9px;color:#6b7a99">{label}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="level-row"><span style="color:#ef4444;font-family:JetBrains Mono">${gold_df["BB_upper"].iloc[-1]:,.0f}</span><span style="font-size:9px;color:#6b7a99">BB Upper</span></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── PROBABILITY ──
        st.markdown("""<div class="intel-card"><h3>30-Day Targets
            <span class="pill pill-model">PROBABILITY</span></h3>""", unsafe_allow_html=True)
        st.markdown('<small style="color:#6b7a99">Based on ATR + historical volatility</small>', unsafe_allow_html=True)
        st.markdown("<b style='color:#10b981;font-size:10px;'>UPSIDE</b>", unsafe_allow_html=True)
        for price, prob in up_probs:
            st.markdown(f"""<div class="prob-row">
                <span style="width:60px;font-family:JetBrains Mono;color:#10b981;font-size:11px">${price:,.0f}</span>
                <div class="prob-bar"><div class="prob-fill" style="width:{prob}%;background:#10b981;"></div></div>
                <span style="width:35px;text-align:right;font-family:JetBrains Mono;color:#10b981;font-size:11px">{prob:.0f}%</span>
            </div>""", unsafe_allow_html=True)
        st.markdown("<b style='color:#ef4444;font-size:10px;margin-top:8px;display:block;'>DOWNSIDE</b>", unsafe_allow_html=True)
        for price, prob in down_probs:
            st.markdown(f"""<div class="prob-row">
                <span style="width:60px;font-family:JetBrains Mono;color:#ef4444;font-size:11px">${price:,.0f}</span>
                <div class="prob-bar"><div class="prob-fill" style="width:{prob}%;background:#ef4444;"></div></div>
                <span style="width:35px;text-align:right;font-family:JetBrains Mono;color:#ef4444;font-size:11px">{prob:.0f}%</span>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # VOLUME SPIKES + NEWS CORRELATION (Full Width)
    # ══════════════════════════════════════════════════
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown("""<div class="section-header" style="--section-accent: #a855f7;">
        <div>
            <span class="section-title">Volume Spike Detector</span>
            <div style="font-size:9px;color:#5a6a8a;margin-top:4px;">Candles with 1.5x+ average volume, matched to gold-related news within 1 day</div>
        </div>
        <span class="pill pill-model">NEWS MATCHED</span>
    </div>""", unsafe_allow_html=True)

    if spikes_correlated:
        for spike in spikes_correlated[:10]:
            dir_class = "spike-up" if spike['direction'] == 'UP' else "spike-down"
            dir_arrow = "▲" if spike['direction'] == 'UP' else "▼"

            st.markdown(f"""<div class="spike-card">
                <div class="spike-header">
                    <span class="spike-date">{spike['date']}</span>
                    <span>
                        <span class="spike-vol {dir_class}">{dir_arrow} {spike['direction']} ${abs(spike['change']):,.2f} ({spike['change_pct']:+.2f}%)</span>
                        &nbsp;
                        <span style="font-size:10px;color:#f0b90b;font-weight:600;">{spike['vol_ratio']:.1f}x VOL</span>
                    </span>
                </div>
                <div style="font-size:11px;color:#a8b2c8;">
                    O: ${spike['open']:,.2f} &nbsp; H: ${spike['high']:,.2f} &nbsp; L: ${spike['low']:,.2f} &nbsp; C: ${spike['close']:,.2f}
                </div>
            """, unsafe_allow_html=True)

            if spike['news']:
                st.markdown('<div style="margin-top:6px;padding-top:6px;border-top:1px solid #263054;">', unsafe_allow_html=True)
                for article in spike['news']:
                    source = f" — {article['source']}" if article['source'] else ""
                    safe_link = article['link'] if article['link'].startswith(('http://', 'https://')) else '#'
                    st.markdown(f"""<div style="font-size:11px;padding:3px 0;">
                        📰 <a href="{safe_link}" target="_blank" rel="noopener noreferrer" style="color:#3b82f6;text-decoration:none;">{html_escape(article['title'])}</a>
                        <span style="color:#6b7a99;font-size:9px;">{source}</span>
                    </div>""", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="font-size:11px;color:#6b7a99;margin-top:4px;">No matching news found for this date</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No significant volume spikes detected in recent data.")

    # ══════════════════════════════════════════════════
    # NEWS FEED (Full Width)
    # ══════════════════════════════════════════════════
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    news_col, cal_col = st.columns([1, 1])

    with news_col:
        st.markdown("""<div class="section-header" style="--section-accent: #ef4444;">
            <span class="section-title">Breaking News &amp; Gold Catalysts</span>
            <span class="pill pill-live">LIVE</span>
        </div>""", unsafe_allow_html=True)
        if news:
            for article in news[:20]:
                date_str = article['published'].strftime('%b %d, %H:%M') if article['published'] else ""
                source = f" — {article['source']}" if article['source'] else ""
                # Highlight geopolitical/breaking news
                title_lower = article['title'].lower()
                is_breaking = any(w in title_lower for w in ['war', 'attack', 'strike', 'nuclear', 'bomb', 'missile', 'invasion', 'crisis', 'emergency'])
                prefix = '<span style="color:#ef4444;font-weight:700;">BREAKING </span>' if is_breaking else ''
                safe_link = article['link'] if article['link'].startswith(('http://', 'https://')) else '#'
                st.markdown(f"""<div style="padding:6px 0;border-bottom:1px solid #1e2745;font-size:12px;">
                    {prefix}<a href="{safe_link}" target="_blank" rel="noopener noreferrer" style="color:#e8ecf4;text-decoration:none;">{article['title']}</a>
                    <div style="font-size:9px;color:#6b7a99;margin-top:2px;">{date_str}{source}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#6b7a99;font-size:12px;padding:8px;">No news available. Check internet connection.</div>', unsafe_allow_html=True)

    with cal_col:
        # Correlated instruments summary
        st.markdown("""<div class="section-header" style="--section-accent: #3b82f6;">
            <span class="section-title">Correlated Instruments</span>
            <span class="pill pill-data">SNAPSHOT</span>
        </div>""", unsafe_allow_html=True)
        for name, df in corr_data.items():
            if len(df) < 2:
                continue
            cur = df['Close'].iloc[-1]
            prv = df['Close'].iloc[-2]
            chg = ((cur / prv) - 1) * 100
            color = "#10b981" if chg >= 0 else "#ef4444"
            st.markdown(f"""<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1e2745;font-size:12px;">
                <span style="color:#a8b2c8">{name}</span>
                <span>
                    <span style="font-family:JetBrains Mono;color:#e8ecf4">{cur:,.2f}</span>
                    <span style="font-family:JetBrains Mono;color:{color};margin-left:8px">{chg:+.2f}%</span>
                </span>
            </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════
    st.markdown(f"""<div class="section-divider"></div>
    <div style="text-align:center;padding:16px 0;">
        <div style="font-size:10px;font-weight:700;color:#f0b90b;letter-spacing:2px;margin-bottom:4px;">GOLD COMMAND</div>
        <div style="font-size:9px;color:#8a94a8;margin-bottom:4px;">Developed by <span style="color:#f0b90b;font-weight:600;">Anoop B.</span></div>
        <div style="font-size:8px;color:#3d4b6b;letter-spacing:0.5px;">
            Market Intelligence Terminal&nbsp;&nbsp;|&nbsp;&nbsp;Data: Yahoo Finance, Google News RSS&nbsp;&nbsp;|&nbsp;&nbsp;Charts: TradingView<br>
            This is not financial advice. All data is delayed and for informational purposes only.
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Auto-refresh via JavaScript (works even when tab is in background) ──
    if auto_refresh:
        refresh_ms = refresh_interval * 60 * 1000
        st.components.v1.html(f"""
        <script>
            setTimeout(function() {{
                window.parent.location.reload();
            }}, {refresh_ms});
        </script>
        <div style="text-align:center;font-size:9px;color:#3d4b6b;padding:4px;">
            Auto-refresh: every {refresh_interval} minutes
        </div>
        """, height=25)


if __name__ == "__main__":
    main()
