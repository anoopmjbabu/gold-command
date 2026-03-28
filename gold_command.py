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
    page_title="GOLD COMMAND — XAU/USD Intelligence | by Capt. Gold",
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

# ETF tickers for flow tracking
GOLD_ETFS = {"GLD": "GLD", "IAU": "IAU"}

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

/* ═══ Animated Instrument Icons ═══ */
.icon-wrap { display: inline-flex; align-items: center; vertical-align: middle; margin-right: 6px; }
.icon-wrap svg { width: 18px; height: 18px; }
@keyframes shimmer { 0%,100%{opacity:0.7;} 50%{opacity:1;} }
@keyframes pulse-icon { 0%,100%{transform:scale(1);} 50%{transform:scale(1.12);} }
@keyframes flicker { 0%,100%{opacity:0.85;transform:scaleY(1);} 30%{opacity:1;transform:scaleY(1.08);} 60%{opacity:0.9;transform:scaleY(0.95);} }
@keyframes drip { 0%,100%{transform:translateY(0);} 50%{transform:translateY(1.5px);} }
@keyframes chart-draw { 0%{stroke-dashoffset:60;} 100%{stroke-dashoffset:0;} }
.icon-gold svg { animation: shimmer 2.5s ease-in-out infinite; }
.icon-dollar svg { animation: pulse-icon 2s ease-in-out infinite; }
.icon-bond svg { animation: shimmer 3s ease-in-out infinite; }
.icon-vix svg { animation: flicker 1.2s ease-in-out infinite; }
.icon-oil svg { animation: drip 2s ease-in-out infinite; }
.icon-spx svg { animation: shimmer 2.5s ease-in-out infinite; }
.icon-spx svg polyline { stroke-dasharray: 60; animation: chart-draw 2s ease-out forwards; }
.icon-trend-up svg { animation: pulse-icon 2s ease-in-out infinite; }
.icon-trend-down svg { animation: pulse-icon 2s ease-in-out infinite; }

/* ═══ Session Clock Bar ═══ */
.session-clock {
    background: linear-gradient(135deg, #0a0f1e 0%, #111829 100%);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 14px 20px;
    margin-bottom: 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
}
.session-clock-times {
    display: flex; gap: 20px; align-items: center;
}
.session-clock-zone {
    text-align: center;
}
.session-clock-zone .tz-label {
    font-size: 8px; color: #5a6a8a; text-transform: uppercase;
    letter-spacing: 1px; font-weight: 700;
}
.session-clock-zone .tz-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px; color: #e2e8f0; font-weight: 600;
}
.session-badges {
    display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
}
.session-badge {
    font-size: 9px; font-weight: 700; padding: 3px 10px;
    border-radius: 12px; letter-spacing: 0.6px;
    text-transform: uppercase;
}
.session-badge.active {
    background: rgba(16,185,129,0.15); color: #10b981;
    border: 1px solid rgba(16,185,129,0.3);
}
.session-badge.inactive {
    background: rgba(90,106,138,0.1); color: #4a5568;
    border: 1px solid rgba(90,106,138,0.15);
}
.session-badge.overlap {
    background: rgba(240,185,11,0.15); color: #f0b90b;
    border: 1px solid rgba(240,185,11,0.3);
    animation: pulse-glow 2s ease-in-out infinite;
}
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(240,185,11,0); }
    50% { box-shadow: 0 0 8px 2px rgba(240,185,11,0.15); }
}
@media (max-width: 768px) {
    .session-clock { flex-direction: column; align-items: flex-start; padding: 12px 14px; }
    .session-clock-times { gap: 14px; }
}

/* ═══ Macro Driver Cards ═══ */
.driver-grid {
    display: flex; gap: 8px; flex-wrap: wrap;
    margin: 14px 0 6px;
}
.driver-card {
    flex: 1; min-width: 120px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 8px;
    padding: 10px 12px;
    text-align: center;
}
.driver-card .dc-name {
    font-size: 8px; color: #5a6a8a; text-transform: uppercase;
    letter-spacing: 0.8px; font-weight: 700; margin-bottom: 4px;
}
.driver-card .dc-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px; font-weight: 700; color: #e2e8f0;
}
.driver-card .dc-change {
    font-size: 10px; font-weight: 600; margin-top: 2px;
}
.driver-card.bullish { border-left: 2px solid #10b981; }
.driver-card.bearish { border-left: 2px solid #ef4444; }
.driver-card.neutral { border-left: 2px solid #5a6a8a; }
@media (max-width: 768px) {
    .driver-grid { gap: 6px; }
    .driver-card { min-width: 90px; padding: 8px 10px; }
}

/* ═══ Market Regime Bar ═══ */
.regime-bar {
    background: linear-gradient(135deg, #0a0f1e 0%, #111829 100%);
    border-radius: 10px;
    padding: 12px 20px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
}
.regime-badge {
    font-size: 10px; font-weight: 800; padding: 4px 14px;
    border-radius: 20px; letter-spacing: 0.8px; text-transform: uppercase;
}
.regime-normal { background: rgba(16,185,129,0.12); color: #10b981; border: 1px solid rgba(16,185,129,0.25); }
.regime-elevated { background: rgba(245,158,11,0.12); color: #f59e0b; border: 1px solid rgba(245,158,11,0.25); }
.regime-high { background: rgba(239,68,68,0.12); color: #ef4444; border: 1px solid rgba(239,68,68,0.25); animation: pulse-glow 1.5s ease-in-out infinite; }
.regime-info {
    display: flex; gap: 16px; align-items: center; flex-wrap: wrap;
}
.regime-info-item {
    font-size: 10px; color: #8892ab;
    display: flex; align-items: center; gap: 4px;
}

/* ═══ TradingView Alert Cards ═══ */
.tv-alert-card {
    background: linear-gradient(145deg, #0d1326, #111830);
    border: 1px solid rgba(240,185,11,0.15);
    border-left: 3px solid #f0b90b;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 8px;
    transition: border-color 0.2s ease;
}
.tv-alert-card:hover { border-color: rgba(240,185,11,0.3); }
.tv-alert-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; color: #6b7a99;
}
.tv-alert-msg {
    font-size: 12px; color: #e8ecf4; font-weight: 600;
    margin-top: 4px;
}
.tv-alert-type {
    font-size: 8px; font-weight: 700; padding: 2px 6px;
    border-radius: 3px; text-transform: uppercase;
    background: rgba(240,185,11,0.1); color: #f0b90b;
    border: 1px solid rgba(240,185,11,0.15);
}

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

/* ═══ Beginner Tooltips ═══ */
.tt-wrap {
    position: relative; display: inline-flex; align-items: center; gap: 3px; cursor: help;
}
.tt-icon {
    display: inline-flex; align-items: center; justify-content: center;
    width: 14px; height: 14px; border-radius: 50%;
    background: rgba(240,185,11,0.12); color: #f0b90b;
    font-size: 9px; font-weight: 800; flex-shrink: 0;
    border: 1px solid rgba(240,185,11,0.2);
    transition: background 0.2s;
}
.tt-wrap:hover .tt-icon { background: rgba(240,185,11,0.25); }
.tt-bubble {
    visibility: hidden; opacity: 0; position: absolute;
    bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%);
    background: #1a2240; color: #c8d0e4; border: 1px solid rgba(240,185,11,0.2);
    border-radius: 8px; padding: 10px 14px; font-size: 11px; line-height: 1.5;
    width: 240px; z-index: 9999; pointer-events: none;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    transition: opacity 0.2s, visibility 0.2s;
    font-weight: 400; letter-spacing: 0; text-transform: none;
}
.tt-bubble::after {
    content: ''; position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
    border: 6px solid transparent; border-top-color: #1a2240;
}
.tt-wrap:hover .tt-bubble { visibility: visible; opacity: 1; }
@media (max-width: 768px) {
    .tt-bubble { width: 200px; font-size: 10px; padding: 8px 10px; }
}

/* ═══ Multi-TF Probability Bars ═══ */
.prob-row {
    display: flex; align-items: center; gap: 10px;
    padding: 6px 0; font-size: 12px;
}
.prob-label { color: #8892ab; min-width: 60px; font-weight: 600; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
.prob-track {
    flex: 1; height: 8px; background: rgba(255,255,255,0.04);
    border-radius: 4px; overflow: hidden; position: relative;
}
.prob-fill {
    height: 100%; border-radius: 4px; transition: width 0.5s ease;
}
.prob-val { color: #e8ecf4; font-family: 'JetBrains Mono', monospace; font-size: 11px; min-width: 40px; text-align: right; font-weight: 600; }

/* ═══ RSS Live Ticker ═══ */
.rss-ticker-wrap {
    background: linear-gradient(135deg, #0b1022, #0f1528);
    border: 1px solid #1a2240; border-radius: 10px;
    padding: 12px 16px; margin-bottom: 10px;
}
.rss-item {
    display: flex; justify-content: space-between; align-items: flex-start;
    padding: 8px 0; border-bottom: 1px solid rgba(26,34,64,0.5);
    font-size: 12px;
}
.rss-item:last-child { border-bottom: none; }
.rss-title { color: #c8d0e4; flex: 1; line-height: 1.4; }
.rss-title a { color: #c8d0e4; text-decoration: none; }
.rss-title a:hover { color: #f0b90b; }
.rss-impact-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px; }
.rss-tag {
    font-size: 8px; font-weight: 700; padding: 2px 6px; border-radius: 3px;
    text-transform: uppercase; letter-spacing: 0.5px;
}
.rss-tag-xau { background: rgba(240,185,11,0.15); color: #f0b90b; }
.rss-tag-usd { background: rgba(16,185,129,0.15); color: #10b981; }
.rss-tag-oil { background: rgba(139,92,246,0.15); color: #8b5cf6; }
.rss-tag-bond { background: rgba(59,130,246,0.15); color: #3b82f6; }
.rss-tag-geo { background: rgba(239,68,68,0.15); color: #ef4444; }
.rss-tag-spx { background: rgba(245,158,11,0.15); color: #f59e0b; }
.rss-breaking { border-left: 2px solid #ef4444; padding-left: 8px; }

/* ═══ Tab Styling ═══ */
.stTabs [data-baseweb="tab-list"] {
    background: linear-gradient(180deg, #0b1022, #0a0e17);
    border-bottom: 1px solid #1a2240;
    gap: 0;
    padding: 0 4px;
}
.stTabs [data-baseweb="tab"] {
    color: #5a6a8a !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px;
    padding: 10px 18px !important;
    border: none !important;
    background: transparent !important;
    transition: color 0.2s, background 0.2s;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #f0b90b !important;
    background: rgba(240,185,11,0.05) !important;
}
.stTabs [aria-selected="true"] {
    color: #f0b90b !important;
    border-bottom: 2px solid #f0b90b !important;
    background: rgba(240,185,11,0.08) !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background-color: #f0b90b !important;
}
.stTabs [data-baseweb="tab-border"] {
    display: none;
}
@media (max-width: 768px) {
    .stTabs [data-baseweb="tab"] {
        font-size: 10px !important;
        padding: 8px 10px !important;
    }
}
/* ── NEW: Fear & Greed, COT, ETF Flows, Patterns, Sentiment, Gold/Silver ── */
.fg-gauge { text-align: center; padding: 12px 0; }
.fg-score { font-size: 42px; font-weight: 900; line-height: 1; }
.fg-bar { height: 8px; background: linear-gradient(90deg,#ef4444,#f97316,#f59e0b,#22c55e,#10b981); border-radius: 4px; position: relative; margin-top: 2px; }
.new-feature-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0; }
@media (max-width: 768px) { .new-feature-row { grid-template-columns: 1fr; } }
.ratio-card { background: #111827; border: 1px solid #1e2745; border-radius: 10px; padding: 14px; }
.ratio-value { font-size: 28px; font-weight: 800; color: #f0b90b; font-family: 'JetBrains Mono'; }
.ratio-compare { font-size: 10px; color: #64748b; }
.pattern-chip { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; margin: 2px; }
.pattern-bull { background: rgba(16,185,129,0.1); color: #10b981; }
.pattern-bear { background: rgba(239,68,68,0.1); color: #ef4444; }
.pattern-neutral { background: rgba(245,158,11,0.1); color: #f59e0b; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# BEGINNER TOOLTIPS / GLOSSARY
# ═══════════════════════════════════════════════════════════════
GLOSSARY = {
    "RSI": "Relative Strength Index — measures how fast price is moving. Below 30 = oversold (may bounce up). Above 70 = overbought (may pull back). Think of it like a speedometer for gold.",
    "ATR": "Average True Range — shows how much gold typically moves in a day (in dollars). Higher ATR = more volatile/bigger swings. Useful for setting stop-losses.",
    "SMA": "Simple Moving Average — the average closing price over N days. SMA 20 = 20-day average. When price is above SMA, the trend is generally up.",
    "Support": "A price level where gold tends to stop falling and bounce back up — like a floor. The more times price bounces off it, the stronger the support.",
    "Resistance": "A price level where gold tends to stop rising and pull back — like a ceiling. Breakouts above resistance can signal new highs.",
    "DXY": "The US Dollar Index — tracks the dollar against 6 major currencies. Gold and the dollar usually move in opposite directions. Strong dollar = gold headwind.",
    "VIX": "The 'Fear Index' — measures expected stock market volatility. High VIX = fear → investors buy gold as a safe haven. VIX above 20 is elevated.",
    "Pivot": "A calculated price level from yesterday's high, low, and close. Traders use pivots as potential turning points. R1/R2/R3 = resistance levels, S1/S2/S3 = support levels.",
    "Fibonacci": "Levels based on the Fibonacci sequence (38.2%, 61.8%, etc.). These ratios often mark where price retraces or reverses. Widely watched by traders.",
    "Risk/Reward": "Compares potential profit to potential loss. A 1:2 R/R means you risk $1 to potentially make $2. Higher is better — pros aim for at least 1:1.5.",
    "Engulfing": "A strong reversal pattern where a candle completely 'engulfs' the previous one. Bullish engulfing at support = potential buy. Bearish engulfing at resistance = potential sell.",
    "Pin Bar": "A candle with a very long wick (shadow) and small body. The long wick shows rejection of a price level. Pin bars at support or resistance are powerful signals.",
    "Session Bias": "The overall directional lean based on macro factors. If most drivers are bullish (weak dollar, high VIX, oil up), the bias tilts bullish for gold.",
    "Correlation": "How closely two instruments move together. +1.0 = move in sync. -1.0 = move opposite. Gold typically has negative correlation with USD and positive with silver.",
    "Breakout": "When price moves decisively above resistance or below support. Breakouts often lead to strong moves. Volume confirmation makes breakouts more reliable.",
    "Yield": "The return on government bonds (US 10Y). Rising yields = bonds compete with gold for investment. Falling yields = gold becomes more attractive.",
    "Safe Haven": "Assets investors buy during uncertainty (wars, crashes, crises). Gold is the classic safe haven — demand rises when fear rises.",
    "Macro Drivers": "Big-picture economic forces that move gold: dollar strength, bond yields, inflation fears, geopolitical risk, stock market moves, oil prices.",
    "Daily Brief": "A plain-English summary of where gold stands right now — price action, key levels, macro alignment, and what to watch. Start here if you're new.",
    "6M High/Low": "The highest and lowest prices gold reached in the past 6 months. These are key reference points — price near the 6M high means we're testing major resistance.",
    "Probability": "The statistical likelihood of price reaching a target within a timeframe, based on historical volatility (ATR). Higher % = more likely based on past moves.",
    "Fear & Greed": "A composite index (0-100) measuring gold market sentiment. Combines RSI momentum, price vs moving averages, volume, VIX, dollar strength, macro drivers, and Bollinger position. Below 25 = Extreme Fear, above 75 = Extreme Greed.",
    "COT": "Commitments of Traders — weekly CFTC report showing how hedge funds (managed money) and producers are positioned in gold futures. Rising net longs = speculators are bullish.",
    "Gold/Silver Ratio": "Gold price divided by silver price. Above 80 = historically high (silver is cheap relative to gold). Below 65 = historically low. Used as an intermarket signal.",
    "ETF Flows": "Dollar volume flowing into gold ETFs (GLD, IAU) as a proxy for institutional buying/selling. Heavy inflows = institutional demand for gold exposure.",
}

def tooltip(term, label=None):
    """Return HTML for an inline tooltip. Label defaults to term name."""
    text = GLOSSARY.get(term, "")
    if not text:
        return label or term
    display = label or term
    return (f'<span class="tt-wrap">{display}'
            f'<span class="tt-icon">?</span>'
            f'<span class="tt-bubble"><b>{term}</b><br>{text}</span></span>')


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


@st.cache_data(ttl=3600)
def fetch_economic_calendar():
    """Fetch this week's economic calendar from ForexFactory (no API key needed).
    Primary source: ForexFactory JSON endpoint (real scheduled events with dates/times).
    Returns list of dicts: event_name, date, time_utc, actual, forecast, previous,
    impact (HIGH/MEDIUM/LOW), currency, gold_impact_direction, released."""

    FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

    # Impact mapping from ForexFactory terminology
    _ff_impact_map = {
        'High': 'HIGH', 'Medium': 'MEDIUM', 'Low': 'LOW',
        'Holiday': 'LOW', 'Non-Economic': 'LOW',
    }

    # Gold-relevant currencies (events in these currencies affect gold)
    _gold_currencies = {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'CNY'}

    events = []

    try:
        resp = requests.get(FF_URL, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; GoldCommand/2.0)'
        })
        resp.raise_for_status()
        ff_data = resp.json()

        now_utc = datetime.utcnow()
        today = now_utc.date()

        for evt in ff_data:
            try:
                title = evt.get('title', '')
                country = evt.get('country', '')
                impact_raw = evt.get('impact', 'Low')
                impact = _ff_impact_map.get(impact_raw, 'LOW')
                forecast = evt.get('forecast', '')
                previous = evt.get('previous', '')
                actual = evt.get('actual', '') if evt.get('actual') else None

                # Parse date — ForexFactory uses ISO format or similar
                date_str = evt.get('date', '')
                evt_date = None
                evt_time = None
                if date_str:
                    try:
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00').split('+')[0])
                        evt_date = dt.date()
                        evt_time = dt.strftime('%H:%M UTC')
                    except Exception:
                        try:
                            dt = datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S')
                            evt_date = dt.date()
                            evt_time = dt.strftime('%H:%M UTC')
                        except Exception:
                            pass

                if not evt_date:
                    continue

                # Only include events from today onward (or recent releases from past 2 days)
                days_diff = (evt_date - today).days
                if days_diff < -2 or days_diff > 7:
                    continue

                # Filter: only gold-relevant currencies
                if country.upper() not in _gold_currencies and impact != 'HIGH':
                    continue

                # Determine if released
                released = actual is not None and actual != ''

                # Gold impact direction for released events
                gold_impact_direction = None
                if released and forecast:
                    try:
                        act_val = float(re.sub(r'[^\d.\-]', '', str(actual)))
                        fct_val = float(re.sub(r'[^\d.\-]', '', str(forecast)))
                        title_lower = title.lower()
                        # Inflation above forecast = hawkish = bearish gold
                        if any(k in title_lower for k in ['cpi', 'pce', 'inflation', 'price index']):
                            gold_impact_direction = "BEARISH" if act_val > fct_val else "BULLISH"
                        # Jobs above forecast = hawkish = bearish gold
                        elif any(k in title_lower for k in ['nonfarm', 'payroll', 'employment change', 'jobs']):
                            gold_impact_direction = "BEARISH" if act_val > fct_val else "BULLISH"
                        # Unemployment above forecast = dovish = bullish gold
                        elif any(k in title_lower for k in ['unemployment', 'jobless']):
                            gold_impact_direction = "BULLISH" if act_val > fct_val else "BEARISH"
                    except Exception:
                        pass

                events.append({
                    'date': evt_date,
                    'title': title,
                    'event_name': title[:50],
                    'time_utc': evt_time,
                    'actual': actual,
                    'forecast': forecast if forecast else None,
                    'previous': previous if previous else None,
                    'impact': impact,
                    'instruments': ['USD'] if country.upper() == 'USD' else [country.upper()],
                    'currency': country.upper(),
                    'gold_impact_direction': gold_impact_direction,
                    'released': released,
                })
            except Exception:
                continue

        logger.info(f"ForexFactory calendar: fetched {len(events)} events")

    except Exception as e:
        logger.warning(f"ForexFactory calendar fetch failed ({e}), using fallback")
        # Fallback: no events rather than bad data from headlines
        events = []

    # Sort: today's events first, then by impact
    _impact_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    events.sort(key=lambda x: (x['date'], _impact_order.get(x['impact'], 2)))
    return events


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
        'top picks', 'best stocks', 'buy now', 'price will',
        'what is the price of', 'how much is gold', 'gold price today:',
        'chart and why it matters', 'what time is today',
        'here\'s what you need to know', 'things to know',
        'what investors should know', 'complete guide',
        'explained:', 'vs.', 'quiz', 'opinion:', 'editorial:',
    ]

    # Verified sources — only trust established financial/news outlets
    VERIFIED_SOURCES = [
        'reuters', 'bloomberg', 'cnbc', 'bbc', 'associated press', 'ap news',
        'financial times', 'wall street journal', 'wsj', 'the guardian',
        'new york times', 'nyt', 'washington post', 'cnn', 'al jazeera',
        'marketwatch', 'yahoo finance', 'investing.com', 'kitco',
        'the jerusalem post', 'times of israel', 'haaretz',
        'south china morning post', 'nikkei', 'the economist',
        'barron', 'forbes', 'business insider', 'axios', 'politico',
        'abc news', 'nbc news', 'cbs news', 'fox business', 'sky news',
        'the telegraph', 'independent', 'ft.com', 'mining.com',
        'world gold council', 'bullionvault', 'gold.org',
        'td economics', 'goldman sachs', 'jp morgan', 'ubs',
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
                source_name = entry.get('source', {}).get('title', '') if hasattr(entry, 'source') else ''
                # Filter: only include articles from verified sources
                source_lower = source_name.lower()
                is_verified = any(vs in source_lower for vs in VERIFIED_SOURCES)
                if not is_verified and source_name:
                    continue  # Skip unverified sources

                articles.append({
                    'title': title,
                    'link': entry.get('link', ''),
                    'source': source_name,
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


# ═══════════════════════════════════════════════════════════════
# NEW: COT POSITIONING DATA (CFTC free public domain data)
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=86400)  # Cache for 24 hours — COT updates weekly on Fridays
def fetch_cot_data():
    """Fetch Commitments of Traders data for gold futures from CFTC."""
    try:
        # CFTC Disaggregated Futures-Only report — gold contract code 088691
        url = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
        params = {
            "$where": "cftc_commodity_code='088691'",
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": 20,
        }
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return None
        records = resp.json()
        if not records:
            return None

        cot_list = []
        for r in records:
            try:
                date = r.get('report_date_as_yyyy_mm_dd', '')[:10]
                # Managed Money (hedge funds / speculators)
                mm_long = int(float(r.get('m_money_positions_long_all', 0)))
                mm_short = int(float(r.get('m_money_positions_short_all', 0)))
                mm_net = mm_long - mm_short
                # Producer/Merchant (commercials)
                prod_long = int(float(r.get('prod_merc_positions_long_all', 0)))
                prod_short = int(float(r.get('prod_merc_positions_short_all', 0)))
                prod_net = prod_long - prod_short
                # Swap Dealers
                swap_long = int(float(r.get('swap_positions_long_all', 0)))
                swap_short = int(float(r.get('swap__positions_short_all', 0)))
                swap_net = swap_long - swap_short
                # Open Interest
                oi = int(float(r.get('open_interest_all', 0)))

                cot_list.append({
                    'date': date,
                    'mm_long': mm_long, 'mm_short': mm_short, 'mm_net': mm_net,
                    'prod_long': prod_long, 'prod_short': prod_short, 'prod_net': prod_net,
                    'swap_long': swap_long, 'swap_short': swap_short, 'swap_net': swap_net,
                    'oi': oi,
                })
            except (ValueError, TypeError):
                continue
        return cot_list if cot_list else None
    except Exception as e:
        logger.warning(f"COT fetch failed: {e}")
        return None


def render_cot_html(cot_data):
    """Render COT positioning as an HTML card."""
    if not cot_data or len(cot_data) < 2:
        return '<div class="intel-card"><p style="color:#5a6a8a;font-size:12px;">COT data unavailable</p></div>'

    latest = cot_data[0]
    prev = cot_data[1]
    mm_chg = latest['mm_net'] - prev['mm_net']
    prod_chg = latest['prod_net'] - prev['prod_net']

    # Determine sentiment from managed money positioning
    if latest['mm_net'] > 0 and mm_chg > 0:
        mm_sentiment = "BULLISH"
        mm_color = "#10b981"
    elif latest['mm_net'] > 0 and mm_chg < 0:
        mm_sentiment = "REDUCING LONGS"
        mm_color = "#f59e0b"
    elif latest['mm_net'] < 0:
        mm_sentiment = "BEARISH"
        mm_color = "#ef4444"
    else:
        mm_sentiment = "NEUTRAL"
        mm_color = "#94a3b8"

    # Net position history (last 8 weeks) for mini sparkline
    hist_vals = [c['mm_net'] for c in cot_data[:8]][::-1]
    max_val = max(abs(v) for v in hist_vals) if hist_vals else 1
    bars_html = ""
    for v in hist_vals:
        h = max(3, abs(v) / max_val * 24)
        c = "#10b981" if v > 0 else "#ef4444"
        bars_html += f'<div style="width:8px;height:{h:.0f}px;background:{c};border-radius:2px;"></div>'

    html = f"""<div class="intel-card">
    <h3 style="display:flex;justify-content:space-between;align-items:center;">
        <span>COT Positioning <span class="pill pill-data">CFTC</span></span>
        <span style="font-size:9px;color:#5a6a8a;">Report: {latest['date']}</span>
    </h3>
    <div style="margin:8px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #1e2745;">
            <span style="font-size:11px;color:#94a3b8;">Managed Money (Specs)</span>
            <span style="font-weight:700;color:{mm_color};font-size:12px;">{mm_sentiment}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:11px;">
            <span style="color:#64748b;">Net Position</span>
            <span style="font-family:JetBrains Mono;color:#e2e8f0;">{latest['mm_net']:+,.0f}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:11px;">
            <span style="color:#64748b;">Weekly Change</span>
            <span style="font-family:JetBrains Mono;color:{'#10b981' if mm_chg > 0 else '#ef4444'};">{mm_chg:+,.0f}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:11px;border-bottom:1px solid #1e2745;">
            <span style="color:#64748b;">Long / Short</span>
            <span style="font-family:JetBrains Mono;font-size:10px;color:#94a3b8;">{latest['mm_long']:,.0f} / {latest['mm_short']:,.0f}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:11px;">
            <span style="color:#64748b;">Producers (Hedgers)</span>
            <span style="font-family:JetBrains Mono;color:#94a3b8;">{latest['prod_net']:+,.0f} <span style="color:{'#10b981' if prod_chg > 0 else '#ef4444'};font-size:10px;">({prod_chg:+,.0f})</span></span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:11px;">
            <span style="color:#64748b;">Open Interest</span>
            <span style="font-family:JetBrains Mono;color:#94a3b8;">{latest['oi']:,.0f}</span>
        </div>
    </div>
    <div style="margin-top:8px;padding-top:8px;border-top:1px solid #1e2745;">
        <span style="font-size:9px;color:#5a6a8a;display:block;margin-bottom:4px;">Managed Money Net — Last 8 Weeks</span>
        <div style="display:flex;align-items:flex-end;gap:3px;height:28px;">
            {bars_html}
        </div>
    </div>
    </div>"""
    return html


# ═══════════════════════════════════════════════════════════════
# NEW: GOLD ETF FLOW TRACKER
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=600)
def fetch_etf_flows():
    """Fetch GLD and IAU volume data as a proxy for institutional gold flows."""
    flows = {}
    for name, ticker in GOLD_ETFS.items():
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="3mo")
            df.index = df.index.tz_localize(None) if df.index.tz else df.index
            if len(df) > 20:
                latest_vol = df['Volume'].iloc[-1]
                avg_vol = df['Volume'].tail(20).mean()
                vol_ratio = latest_vol / avg_vol if avg_vol > 0 else 1.0
                price = df['Close'].iloc[-1]
                daily_chg = (df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100
                # Dollar volume as flow proxy
                dollar_vol = latest_vol * price
                avg_dollar_vol = (df['Volume'].tail(20) * df['Close'].tail(20)).mean()
                dollar_ratio = dollar_vol / avg_dollar_vol if avg_dollar_vol > 0 else 1.0
                # 5-day flow trend
                recent_ratios = []
                for i in range(-5, 0):
                    dv = df['Volume'].iloc[i] * df['Close'].iloc[i]
                    recent_ratios.append(dv / avg_dollar_vol if avg_dollar_vol > 0 else 1.0)

                flows[name] = {
                    'price': price, 'daily_chg': daily_chg,
                    'volume': latest_vol, 'avg_volume': avg_vol, 'vol_ratio': vol_ratio,
                    'dollar_vol': dollar_vol, 'dollar_ratio': dollar_ratio,
                    'recent_ratios': recent_ratios,
                }
        except Exception as e:
            logger.warning(f"ETF flow fetch failed for {name}: {e}")
    return flows


def render_etf_flows_html(flows):
    """Render ETF flow data as HTML card."""
    if not flows:
        return '<div class="intel-card"><p style="color:#5a6a8a;font-size:12px;">ETF flow data unavailable</p></div>'

    rows = ""
    aggregate_signal = 0
    for name, f in flows.items():
        flow_color = "#10b981" if f['dollar_ratio'] > 1.2 else "#ef4444" if f['dollar_ratio'] < 0.7 else "#94a3b8"
        flow_label = "HEAVY INFLOW" if f['dollar_ratio'] > 1.5 else "ABOVE AVG" if f['dollar_ratio'] > 1.2 else "LIGHT" if f['dollar_ratio'] < 0.7 else "NORMAL"
        aggregate_signal += f['dollar_ratio']

        # Mini 5-day flow bars
        bars = ""
        for r in f['recent_ratios']:
            h = max(3, min(20, r * 12))
            c = "#10b981" if r > 1.0 else "#ef4444"
            bars += f'<div style="width:6px;height:{h:.0f}px;background:{c};border-radius:1px;"></div>'

        rows += f"""<div style="padding:8px 0;border-bottom:1px solid #1e2745;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-weight:700;color:#e2e8f0;font-size:12px;">{name}</span>
                    <span style="font-size:10px;color:#64748b;margin-left:6px;">${f['price']:,.2f} ({f['daily_chg']:+.1f}%)</span>
                </div>
                <span style="font-size:10px;font-weight:700;color:{flow_color};">{flow_label}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;">
                <div style="font-size:10px;color:#64748b;">Vol: {f['vol_ratio']:.1f}x avg &nbsp;·&nbsp; ${f['dollar_vol']/1e6:,.0f}M dollar vol</div>
                <div style="display:flex;align-items:flex-end;gap:2px;height:20px;">{bars}</div>
            </div>
        </div>"""

    # Aggregate signal
    avg_ratio = aggregate_signal / len(flows) if flows else 1.0
    if avg_ratio > 1.3:
        agg_label, agg_color = "INSTITUTIONAL BUYING", "#10b981"
    elif avg_ratio < 0.7:
        agg_label, agg_color = "INSTITUTIONAL SELLING", "#ef4444"
    else:
        agg_label, agg_color = "NORMAL FLOW", "#94a3b8"

    return f"""<div class="intel-card">
    <h3 style="display:flex;justify-content:space-between;align-items:center;">
        <span>ETF Flows <span class="pill pill-data">GLD · IAU</span></span>
        <span style="font-size:10px;font-weight:700;color:{agg_color};">{agg_label}</span>
    </h3>
    {rows}
    </div>"""


# ═══════════════════════════════════════════════════════════════
# NEW: GOLD/SILVER RATIO MONITOR
# ═══════════════════════════════════════════════════════════════
def compute_gold_silver_ratio(gold_df, corr_data):
    """Compute gold/silver ratio and context."""
    if 'Silver' not in corr_data or corr_data['Silver'].empty or gold_df.empty:
        return None
    try:
        silver_df = corr_data['Silver']
        # Align on common dates
        common = gold_df.index.intersection(silver_df.index)
        if len(common) < 20:
            return None
        g = gold_df.loc[common, 'Close']
        s = silver_df.loc[common, 'Close']
        ratio = g / s
        current_ratio = ratio.iloc[-1]
        avg_20d = ratio.tail(20).mean()
        avg_50d = ratio.tail(50).mean() if len(ratio) >= 50 else avg_20d
        ratio_high = ratio.max()
        ratio_low = ratio.min()

        # Interpretation
        if current_ratio > 85:
            interp = "Historically elevated — silver may outperform"
            interp_color = "#f59e0b"
        elif current_ratio > 75:
            interp = "Above average — slight gold preference"
            interp_color = "#94a3b8"
        elif current_ratio > 65:
            interp = "Normal range — balanced precious metals"
            interp_color = "#10b981"
        else:
            interp = "Low ratio — gold may outperform silver"
            interp_color = "#3b82f6"

        # 5-day history for sparkline
        hist = ratio.tail(10).tolist()

        return {
            'current': current_ratio, 'avg_20d': avg_20d, 'avg_50d': avg_50d,
            'high': ratio_high, 'low': ratio_low,
            'interp': interp, 'interp_color': interp_color,
            'history': hist,
        }
    except Exception as e:
        logger.warning(f"Gold/Silver ratio calc failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# NEW: GOLD FEAR & GREED COMPOSITE INDEX
# ═══════════════════════════════════════════════════════════════
def compute_fear_greed_index(gold_df, corr_data, drivers):
    """Compute a gold-specific Fear & Greed index (0-100) from existing data."""
    scores = []

    # 1. RSI component (0-100 mapped: 30=0 fear, 70=100 greed)
    rsi = gold_df['RSI'].iloc[-1]
    rsi_score = max(0, min(100, (rsi - 30) * 2.5))  # 30→0, 70→100
    scores.append(('RSI Momentum', rsi_score, f'RSI at {rsi:.0f}'))

    # 2. Price vs SMA20 (distance from mean)
    current = gold_df['Close'].iloc[-1]
    sma20 = gold_df['SMA_20'].iloc[-1]
    dist_pct = ((current - sma20) / sma20) * 100
    sma_score = max(0, min(100, 50 + dist_pct * 10))  # +5% above = 100, -5% below = 0
    scores.append(('Price vs SMA20', sma_score, f'{dist_pct:+.1f}% from 20-day avg'))

    # 3. Volume conviction (high vol on up days = greed, high vol on down days = fear)
    vol_ratio = gold_df['Vol_ratio'].iloc[-1]
    daily_chg = current - gold_df['Close'].iloc[-2]
    if daily_chg >= 0:
        vol_score = min(100, 50 + vol_ratio * 20)  # Up day + high volume = greed
    else:
        vol_score = max(0, 50 - vol_ratio * 20)  # Down day + high volume = fear
    scores.append(('Volume Conviction', vol_score, f'{vol_ratio:.1f}x avg volume'))

    # 4. VIX component (inverted: high VIX = fear)
    if 'VIX' in corr_data and not corr_data['VIX'].empty:
        vix_val = corr_data['VIX']['Close'].iloc[-1]
        vix_score = max(0, min(100, 100 - (vix_val - 12) * 4))  # VIX 12=100, VIX 37=0
        scores.append(('Market Fear (VIX)', vix_score, f'VIX at {vix_val:.1f}'))

    # 5. Macro driver balance
    bull_count = sum(1 for d in drivers if d[2] == "BULLISH")
    bear_count = sum(1 for d in drivers if d[2] == "BEARISH")
    total = bull_count + bear_count if (bull_count + bear_count) > 0 else 1
    driver_score = (bull_count / total) * 100
    scores.append(('Macro Drivers', driver_score, f'{bull_count}B / {bear_count}B'))

    # 6. Bollinger Band position (where price sits within bands)
    bb_upper = gold_df['BB_upper'].iloc[-1]
    bb_lower = gold_df['BB_lower'].iloc[-1]
    bb_range = bb_upper - bb_lower if bb_upper != bb_lower else 1
    bb_score = max(0, min(100, ((current - bb_lower) / bb_range) * 100))
    scores.append(('Bollinger Position', bb_score, f'{"Upper" if bb_score > 70 else "Lower" if bb_score < 30 else "Mid"} band'))

    # 7. DXY inverse (weak dollar = greed for gold)
    if 'DXY' in corr_data and not corr_data['DXY'].empty:
        dxy = corr_data['DXY']['Close']
        dxy_chg = (dxy.iloc[-1] - dxy.iloc[-2]) / dxy.iloc[-2] * 100
        dxy_score = max(0, min(100, 50 - dxy_chg * 25))  # DXY down = greed for gold
        scores.append(('Dollar Weakness', dxy_score, f'DXY {dxy_chg:+.2f}%'))

    # Composite
    composite = sum(s[1] for s in scores) / len(scores) if scores else 50

    # Label
    if composite >= 80:
        label, color = "EXTREME GREED", "#10b981"
    elif composite >= 60:
        label, color = "GREED", "#22c55e"
    elif composite >= 45:
        label, color = "NEUTRAL", "#f59e0b"
    elif composite >= 25:
        label, color = "FEAR", "#f97316"
    else:
        label, color = "EXTREME FEAR", "#ef4444"

    return {'score': composite, 'label': label, 'color': color, 'components': scores}


def render_fear_greed_html(fg):
    """Render Fear & Greed index as HTML."""
    if not fg:
        return ''

    # Gauge visualization
    pct = fg['score']
    angle = (pct / 100) * 180  # 0=left (fear), 180=right (greed)

    # Component bars
    comp_html = ""
    for name, score, detail in fg['components']:
        bar_color = "#10b981" if score >= 60 else "#ef4444" if score < 40 else "#f59e0b"
        comp_html += f"""<div style="display:flex;align-items:center;gap:8px;padding:3px 0;font-size:11px;">
            <span style="width:120px;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</span>
            <div style="flex:1;height:6px;background:#1e2745;border-radius:3px;overflow:hidden;">
                <div style="width:{score:.0f}%;height:100%;background:{bar_color};border-radius:3px;"></div>
            </div>
            <span style="width:30px;text-align:right;font-family:JetBrains Mono;color:{bar_color};font-size:10px;">{score:.0f}</span>
        </div>"""

    return f"""<div class="intel-card" style="border-top:2px solid {fg['color']};">
    <h3 style="display:flex;justify-content:space-between;align-items:center;">
        <span>Gold Fear &amp; Greed</span>
        <span style="font-size:10px;font-weight:700;color:#5a6a8a;">COMPOSITE INDEX</span>
    </h3>
    <div style="text-align:center;padding:12px 0;">
        <div style="font-size:42px;font-weight:900;color:{fg['color']};line-height:1;">{fg['score']:.0f}</div>
        <div style="font-size:13px;font-weight:700;color:{fg['color']};letter-spacing:1px;margin-top:4px;">{fg['label']}</div>
        <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:9px;color:#5a6a8a;">
            <span>EXTREME FEAR</span><span>NEUTRAL</span><span>EXTREME GREED</span>
        </div>
        <div style="height:8px;background:linear-gradient(90deg,#ef4444,#f97316,#f59e0b,#22c55e,#10b981);border-radius:4px;position:relative;margin-top:2px;">
            <div style="position:absolute;left:{pct:.0f}%;top:-3px;width:3px;height:14px;background:#fff;border-radius:2px;transform:translateX(-50%);"></div>
        </div>
    </div>
    <div style="margin-top:8px;padding-top:8px;border-top:1px solid #1e2745;">
        <span style="font-size:9px;color:#5a6a8a;display:block;margin-bottom:6px;">COMPONENT BREAKDOWN</span>
        {comp_html}
    </div>
    </div>"""


# ═══════════════════════════════════════════════════════════════
# NEW: CANDLESTICK PATTERN RECOGNITION
# ═══════════════════════════════════════════════════════════════
def detect_candlestick_patterns(df):
    """Detect common candlestick patterns from OHLC data."""
    patterns = []
    if len(df) < 5:
        return patterns

    for i in range(-3, 0):  # Check last 3 candles
        try:
            o, h, l, c = df['Open'].iloc[i], df['High'].iloc[i], df['Low'].iloc[i], df['Close'].iloc[i]
            body = abs(c - o)
            total_range = h - l if h != l else 0.01
            upper_wick = h - max(o, c)
            lower_wick = min(o, c) - l
            date = df.index[i].strftime('%b %d') if hasattr(df.index[i], 'strftime') else str(df.index[i])[:10]

            # Previous candle for context
            po, pc = df['Open'].iloc[i - 1], df['Close'].iloc[i - 1]
            prev_body = abs(pc - po)
            prev_bullish = pc > po

            # Hammer / Hanging Man (long lower wick, small body at top)
            if lower_wick > body * 2 and upper_wick < body * 0.5 and body > 0:
                if c > o:
                    patterns.append({'date': date, 'name': 'Hammer', 'type': 'BULLISH',
                                     'desc': 'Long lower wick — buyers stepped in at lows', 'strength': 'STRONG'})
                else:
                    patterns.append({'date': date, 'name': 'Hanging Man', 'type': 'BEARISH',
                                     'desc': 'Selling pressure after up-move', 'strength': 'MODERATE'})

            # Shooting Star (long upper wick, small body at bottom)
            elif upper_wick > body * 2 and lower_wick < body * 0.5 and body > 0:
                patterns.append({'date': date, 'name': 'Shooting Star', 'type': 'BEARISH',
                                 'desc': 'Rejected at highs — sellers in control', 'strength': 'STRONG'})

            # Doji (tiny body, wicks both sides)
            elif body < total_range * 0.1 and total_range > 0:
                patterns.append({'date': date, 'name': 'Doji', 'type': 'NEUTRAL',
                                 'desc': 'Indecision — market at equilibrium', 'strength': 'MODERATE'})

            # Bullish Engulfing
            elif c > o and not prev_bullish and body > prev_body * 1.1 and c > po and o < pc:
                patterns.append({'date': date, 'name': 'Bullish Engulfing', 'type': 'BULLISH',
                                 'desc': 'Buyers overwhelmed prior selling — reversal signal', 'strength': 'STRONG'})

            # Bearish Engulfing
            elif c < o and prev_bullish and body > prev_body * 1.1 and c < po and o > pc:
                patterns.append({'date': date, 'name': 'Bearish Engulfing', 'type': 'BEARISH',
                                 'desc': 'Sellers overwhelmed prior buying — reversal signal', 'strength': 'STRONG'})

            # Marubozu (full body, very small wicks)
            elif body > total_range * 0.85:
                if c > o:
                    patterns.append({'date': date, 'name': 'Bullish Marubozu', 'type': 'BULLISH',
                                     'desc': 'Strong buying from open to close — conviction', 'strength': 'STRONG'})
                else:
                    patterns.append({'date': date, 'name': 'Bearish Marubozu', 'type': 'BEARISH',
                                     'desc': 'Strong selling from open to close — conviction', 'strength': 'STRONG'})

        except (IndexError, TypeError):
            continue

    return patterns


def render_patterns_html(patterns):
    """Render detected candlestick patterns."""
    if not patterns:
        return '<div style="font-size:11px;color:#5a6a8a;padding:4px 0;">No significant patterns in last 3 sessions</div>'

    html = ""
    for p in patterns[:4]:  # Max 4 patterns
        type_color = "#10b981" if p['type'] == 'BULLISH' else "#ef4444" if p['type'] == 'BEARISH' else "#f59e0b"
        strength_bg = "rgba(16,185,129,0.1)" if p['strength'] == 'STRONG' else "rgba(249,115,22,0.1)"
        html += f"""<div style="padding:6px 0;border-bottom:1px solid #1e274533;font-size:11px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="color:#e2e8f0;font-weight:600;">{p['name']}</span>
                <div style="display:flex;gap:4px;align-items:center;">
                    <span style="font-size:9px;background:{strength_bg};padding:1px 5px;border-radius:3px;color:{type_color};">{p['strength']}</span>
                    <span style="font-size:9px;font-weight:700;color:{type_color};">{p['type']}</span>
                </div>
            </div>
            <div style="color:#64748b;font-size:10px;margin-top:2px;">{p['date']} — {p['desc']}</div>
        </div>"""
    return html


# ═══════════════════════════════════════════════════════════════
# NEW: NEWS SENTIMENT SCORING (keyword-based fallback, no API key needed)
# ═══════════════════════════════════════════════════════════════
def compute_news_sentiment(news_articles):
    """Compute aggregate sentiment from news articles using keyword analysis."""
    if not news_articles:
        return None

    # Gold-specific sentiment keywords
    bullish_kw = {'surge', 'rally', 'soar', 'jump', 'climb', 'gain', 'rise', 'high', 'record',
                  'safe haven', 'buying', 'demand', 'bullish', 'upside', 'breakout', 'support',
                  'easing', 'dovish', 'cut', 'stimulus', 'uncertainty', 'fear', 'crisis',
                  'geopolitical', 'tension', 'war', 'inflation', 'weaker dollar'}
    bearish_kw = {'drop', 'fall', 'decline', 'slide', 'plunge', 'sell', 'loss', 'low', 'crash',
                  'bearish', 'downside', 'resistance', 'hawkish', 'hike', 'taper', 'strong dollar',
                  'risk-on', 'equities rally', 'yields rise', 'profit taking', 'correction'}

    bull_count = 0
    bear_count = 0
    neutral_count = 0
    scored_articles = []

    for article in news_articles[:30]:  # Score up to 30 articles
        title = article.get('title', '').lower()
        score = 0
        for kw in bullish_kw:
            if kw in title:
                score += 1
        for kw in bearish_kw:
            if kw in title:
                score -= 1

        if score > 0:
            bull_count += 1
            sentiment = "BULLISH"
        elif score < 0:
            bear_count += 1
            sentiment = "BEARISH"
        else:
            neutral_count += 1
            sentiment = "NEUTRAL"

        scored_articles.append({**article, '_sentiment': sentiment, '_score': score})

    total = bull_count + bear_count + neutral_count
    if total == 0:
        return None

    bull_pct = (bull_count / total) * 100
    bear_pct = (bear_count / total) * 100
    net_score = ((bull_count - bear_count) / total) * 100  # -100 to +100

    if net_score > 25:
        label, color = "BULLISH", "#10b981"
    elif net_score > 5:
        label, color = "LEAN BULLISH", "#22c55e"
    elif net_score > -5:
        label, color = "NEUTRAL", "#f59e0b"
    elif net_score > -25:
        label, color = "LEAN BEARISH", "#f97316"
    else:
        label, color = "BEARISH", "#ef4444"

    return {
        'bull_count': bull_count, 'bear_count': bear_count, 'neutral_count': neutral_count,
        'bull_pct': bull_pct, 'bear_pct': bear_pct, 'net_score': net_score,
        'label': label, 'color': color, 'articles': scored_articles,
    }


def render_sentiment_html(sentiment):
    """Render news sentiment gauge."""
    if not sentiment:
        return ''

    total = sentiment['bull_count'] + sentiment['bear_count'] + sentiment['neutral_count']

    return f"""<div style="background:#111827;border:1px solid #1e2745;border-radius:8px;padding:12px;margin-bottom:12px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="font-size:12px;font-weight:700;color:#e2e8f0;">News Sentiment</span>
        <span style="font-size:11px;font-weight:700;color:{sentiment['color']};">{sentiment['label']}</span>
    </div>
    <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;margin-bottom:6px;">
        <div style="width:{sentiment['bull_pct']:.0f}%;background:#10b981;"></div>
        <div style="width:{100 - sentiment['bull_pct'] - sentiment['bear_pct']:.0f}%;background:#f59e0b33;"></div>
        <div style="width:{sentiment['bear_pct']:.0f}%;background:#ef4444;"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:10px;color:#64748b;">
        <span style="color:#10b981;">{sentiment['bull_count']} Bullish ({sentiment['bull_pct']:.0f}%)</span>
        <span>{sentiment['neutral_count']} Neutral</span>
        <span style="color:#ef4444;">{sentiment['bear_count']} Bearish ({sentiment['bear_pct']:.0f}%)</span>
    </div>
    <div style="font-size:9px;color:#5a6a8a;margin-top:4px;">{total} articles analysed via keyword sentiment</div>
    </div>"""


# ═══════════════════════════════════════════════════════════════
# NEW: MULTI-TIMEFRAME RSI + FIBONACCI LEVELS
# ═══════════════════════════════════════════════════════════════
def _compute_rsi(series, period=14):
    """Compute RSI from a price series using Wilder's smoothing."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(alpha=1.0/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = (100 - (100 / (1 + rs))).fillna(50)
    return rsi


def _compute_fib_levels(high, low):
    """Compute Fibonacci retracement levels from a swing high and low."""
    diff = high - low
    return {
        '0.0% (High)': high,
        '23.6%': high - 0.236 * diff,
        '38.2%': high - 0.382 * diff,
        '50.0%': high - 0.500 * diff,
        '61.8%': high - 0.618 * diff,
        '78.6%': high - 0.786 * diff,
        '100.0% (Low)': low,
    }


@st.cache_data(ttl=300)
def fetch_multi_tf_data(symbol="GC=F"):
    """Fetch OHLCV data across 8 timeframes for RSI and Fibonacci calculation.
    Returns dict of {tf_label: DataFrame}.
    yfinance limits: intraday data up to 60 days for 15m+, 7 days for 1m.
    """
    timeframes = [
        ("Monthly", "5y", "1mo"),
        ("Weekly", "2y", "1wk"),
        ("Daily", "6mo", "1d"),
        ("4H", "60d", "1h"),      # Resample 1h → 4h
        ("1H", "30d", "1h"),
        ("30min", "30d", "30m"),
        ("15min", "60d", "15m"),
        ("5min", "5d", "5m"),
    ]

    data = {}
    for label, period, interval in timeframes:
        try:
            t = yf.Ticker(symbol)
            df = t.history(period=period, interval=interval)
            if df.index.tz:
                df.index = df.index.tz_localize(None)
            if len(df) < 15:
                continue

            # Resample 1h to 4h
            if label == "4H":
                df = df.resample('4h').agg({
                    'Open': 'first', 'High': 'max', 'Low': 'min',
                    'Close': 'last', 'Volume': 'sum'
                }).dropna()
                if len(df) < 15:
                    continue

            data[label] = df
        except Exception as e:
            logger.warning(f"MTF fetch failed for {label} ({period}/{interval}): {e}")
            continue

    return data


def compute_multi_tf_rsi(mtf_data):
    """Compute RSI(14) for each timeframe. Returns list of (label, rsi_value, trend_word)."""
    results = []
    tf_order = ["Monthly", "Weekly", "Daily", "4H", "1H", "30min", "15min", "5min"]

    for label in tf_order:
        if label not in mtf_data or mtf_data[label].empty:
            results.append((label, None, "N/A"))
            continue
        df = mtf_data[label]
        rsi_series = _compute_rsi(df['Close'], 14)
        rsi_val = rsi_series.iloc[-1]

        if rsi_val > 70:
            trend = "OVERBOUGHT"
        elif rsi_val > 60:
            trend = "BULLISH"
        elif rsi_val > 40:
            trend = "NEUTRAL"
        elif rsi_val > 30:
            trend = "BEARISH"
        else:
            trend = "OVERSOLD"

        results.append((label, rsi_val, trend))

    return results


def compute_multi_tf_fib(mtf_data):
    """Compute Fibonacci retracement levels for each timeframe using period high/low.
    Returns list of (label, fib_dict, current_price, nearest_level_name).
    """
    results = []
    tf_order = ["Monthly", "Weekly", "Daily", "4H", "1H", "30min", "15min", "5min"]

    for label in tf_order:
        if label not in mtf_data or mtf_data[label].empty:
            continue
        df = mtf_data[label]
        # Use full period swing high/low
        period_high = df['High'].max()
        period_low = df['Low'].min()
        current = df['Close'].iloc[-1]

        if period_high == period_low:
            continue

        fibs = _compute_fib_levels(period_high, period_low)

        # Find nearest Fib level
        nearest_name = ""
        nearest_dist = float('inf')
        for name, level in fibs.items():
            dist = abs(current - level)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_name = name

        results.append((label, fibs, current, nearest_name))

    return results


def render_mtf_rsi_html(rsi_data):
    """Render multi-timeframe RSI as a heatmap table."""
    if not rsi_data:
        return '<div style="color:#5a6a8a;font-size:12px;">Multi-TF RSI unavailable</div>'

    rows = ""
    for label, rsi_val, trend in rsi_data:
        if rsi_val is None:
            rows += f"""<tr>
                <td style="padding:5px 8px;font-size:11px;color:#94a3b8;border-bottom:1px solid #1e274533;">{label}</td>
                <td style="padding:5px 8px;text-align:center;color:#3d4b6b;font-size:11px;border-bottom:1px solid #1e274533;">—</td>
                <td style="padding:5px 8px;text-align:center;color:#3d4b6b;font-size:10px;border-bottom:1px solid #1e274533;">N/A</td>
                <td style="padding:5px 8px;border-bottom:1px solid #1e274533;"><div style="height:6px;background:#1e2745;border-radius:3px;"></div></td>
            </tr>"""
            continue

        # Color and bar
        if rsi_val > 70:
            color, bg = "#ef4444", "rgba(239,68,68,0.15)"
        elif rsi_val > 60:
            color, bg = "#10b981", "rgba(16,185,129,0.12)"
        elif rsi_val > 40:
            color, bg = "#f59e0b", "rgba(245,158,11,0.1)"
        elif rsi_val > 30:
            color, bg = "#f97316", "rgba(249,115,22,0.12)"
        else:
            color, bg = "#ef4444", "rgba(239,68,68,0.15)"

        bar_width = rsi_val
        # Highlight extreme zones
        trend_badge = ""
        if trend in ("OVERBOUGHT", "OVERSOLD"):
            trend_badge = f'<span style="font-size:8px;font-weight:700;color:{color};background:{bg};padding:1px 4px;border-radius:3px;margin-left:4px;">⚠️</span>'

        rows += f"""<tr style="background:{bg if trend in ('OVERBOUGHT','OVERSOLD') else 'transparent'};">
            <td style="padding:5px 8px;font-size:11px;font-weight:600;color:#e2e8f0;border-bottom:1px solid #1e274533;white-space:nowrap;">{label}</td>
            <td style="padding:5px 8px;text-align:center;font-family:JetBrains Mono;font-size:12px;font-weight:700;color:{color};border-bottom:1px solid #1e274533;">{rsi_val:.1f}</td>
            <td style="padding:5px 8px;text-align:center;font-size:10px;color:{color};border-bottom:1px solid #1e274533;white-space:nowrap;">{trend}{trend_badge}</td>
            <td style="padding:5px 8px;border-bottom:1px solid #1e274533;width:40%;">
                <div style="height:6px;background:#1e2745;border-radius:3px;overflow:hidden;position:relative;">
                    <div style="width:{bar_width:.0f}%;height:100%;background:{color};border-radius:3px;"></div>
                    <div style="position:absolute;left:30%;top:0;width:1px;height:100%;background:#ffffff22;"></div>
                    <div style="position:absolute;left:70%;top:0;width:1px;height:100%;background:#ffffff22;"></div>
                </div>
            </td>
        </tr>"""

    # Confluence detection: count how many TFs agree
    bullish_tfs = sum(1 for _, v, t in rsi_data if v is not None and v > 50)
    bearish_tfs = sum(1 for _, v, t in rsi_data if v is not None and v < 50)
    total_valid = sum(1 for _, v, _ in rsi_data if v is not None)

    if total_valid > 0:
        if bullish_tfs >= total_valid * 0.75:
            confluence = f'<span style="color:#10b981;font-weight:700;">BULLISH CONFLUENCE</span> — {bullish_tfs}/{total_valid} timeframes above 50'
        elif bearish_tfs >= total_valid * 0.75:
            confluence = f'<span style="color:#ef4444;font-weight:700;">BEARISH CONFLUENCE</span> — {bearish_tfs}/{total_valid} timeframes below 50'
        else:
            confluence = f'<span style="color:#f59e0b;font-weight:700;">MIXED</span> — {bullish_tfs} bullish, {bearish_tfs} bearish across {total_valid} timeframes'
    else:
        confluence = ""

    return f"""<div class="intel-card">
    <h3 style="display:flex;justify-content:space-between;align-items:center;">
        <span>Multi-TF RSI(14)</span>
        <span style="font-size:9px;color:#5a6a8a;">8 TIMEFRAMES</span>
    </h3>
    <table style="width:100%;border-collapse:collapse;margin:6px 0;">
        <tr>
            <th style="text-align:left;font-size:9px;color:#5a6a8a;padding:4px 8px;border-bottom:1px solid #1e2745;">TF</th>
            <th style="text-align:center;font-size:9px;color:#5a6a8a;padding:4px 8px;border-bottom:1px solid #1e2745;">RSI</th>
            <th style="text-align:center;font-size:9px;color:#5a6a8a;padding:4px 8px;border-bottom:1px solid #1e2745;">STATE</th>
            <th style="font-size:9px;color:#5a6a8a;padding:4px 8px;border-bottom:1px solid #1e2745;">30 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 70</th>
        </tr>
        {rows}
    </table>
    <div style="padding:8px;border-top:1px solid #1e2745;font-size:11px;margin-top:4px;">
        {confluence}
    </div>
    </div>"""


def render_mtf_fib_html(fib_data):
    """Render multi-timeframe Fibonacci levels."""
    if not fib_data:
        return '<div style="color:#5a6a8a;font-size:12px;">Fibonacci data unavailable</div>'

    # Show the most useful timeframes: Daily, 4H, 1H, 15min
    priority_tfs = ["Daily", "4H", "1H", "15min"]
    filtered = [f for f in fib_data if f[0] in priority_tfs]
    if not filtered:
        filtered = fib_data[:4]

    tabs_html = ""
    for i, (label, fibs, current, nearest) in enumerate(filtered):
        levels_html = ""
        for name, level in fibs.items():
            is_nearest = name == nearest
            dist_pct = ((current - level) / level) * 100 if level > 0 else 0

            # Color: support (below price) = green, resistance (above price) = red
            if level > current:
                lev_color = "#ef4444"
                lev_type = "R"
            elif level < current:
                lev_color = "#10b981"
                lev_type = "S"
            else:
                lev_color = "#f0b90b"
                lev_type = "="

            highlight = "background:rgba(240,185,11,0.08);font-weight:700;" if is_nearest else ""

            levels_html += f"""<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 6px;border-bottom:1px solid #1e274522;font-size:11px;{highlight}">
                <span style="color:#94a3b8;width:85px;">{name}</span>
                <span style="font-family:JetBrains Mono;color:{lev_color};font-weight:600;">${level:,.2f}</span>
                <span style="font-size:9px;color:#5a6a8a;width:55px;text-align:right;">{dist_pct:+.1f}%{' ◄' if is_nearest else ''}</span>
            </div>"""

        tabs_html += f"""<div style="margin-bottom:12px;">
            <div style="font-size:11px;font-weight:700;color:#f0b90b;margin-bottom:4px;letter-spacing:0.5px;">{label}</div>
            <div style="font-size:9px;color:#5a6a8a;margin-bottom:4px;">
                Swing: ${fibs['100.0% (Low)']:,.2f} → ${fibs['0.0% (High)']:,.2f} &nbsp;|&nbsp;
                Current: ${current:,.2f} near <span style="color:#f0b90b;">{nearest}</span>
            </div>
            {levels_html}
        </div>"""

    return f"""<div class="intel-card">
    <h3 style="display:flex;justify-content:space-between;align-items:center;">
        <span>Multi-TF Fibonacci</span>
        <span style="font-size:9px;color:#5a6a8a;">RETRACEMENT</span>
    </h3>
    {tabs_html}
    </div>"""


def detect_volume_spikes(df, threshold=1.5):
    """Detect significant market moves using BOTH volume AND price-change triggers.
    A $200 move on gold should always show up, even if yfinance volume data is spotty.
    """
    df = df.copy()

    # Compute price-based metrics
    df['change'] = df['Close'] - df['Open']
    df['change_pct'] = (df['change'] / df['Open']).abs() * 100
    df['daily_range'] = df['High'] - df['Low']
    df['range_vs_atr'] = df['daily_range'] / df['ATR_14'] if 'ATR_14' in df.columns else 1.0

    # Trigger 1: Volume spike (original — volume > threshold x 20-day avg)
    vol_mask = df['Vol_ratio'] >= threshold

    # Trigger 2: Price-change spike (close-to-close move > 1.5x ATR)
    if 'ATR_14' in df.columns:
        price_chg_abs = (df['Close'] - df['Close'].shift(1)).abs()
        price_mask = price_chg_abs > (df['ATR_14'] * 1.3)
    else:
        price_mask = df['change_pct'] > 1.5  # Fallback: >1.5% move

    # Trigger 3: Intraday range spike (daily high-low range > 1.5x ATR)
    if 'ATR_14' in df.columns:
        range_mask = df['daily_range'] > (df['ATR_14'] * 1.5)
    else:
        range_mask = pd.Series(False, index=df.index)

    # Combine: any trigger qualifies
    combined_mask = vol_mask | price_mask | range_mask
    spikes = df[combined_mask].copy()

    # Tag the trigger reason
    spikes['trigger'] = ''
    spikes.loc[vol_mask & combined_mask, 'trigger'] += 'volume '
    spikes.loc[price_mask & combined_mask, 'trigger'] += 'price-move '
    spikes.loc[range_mask & combined_mask, 'trigger'] += 'range '
    spikes['trigger'] = spikes['trigger'].str.strip()

    spikes['direction'] = spikes['change'].apply(lambda x: 'UP' if x >= 0 else 'DOWN')
    return spikes.sort_index(ascending=False)


def correlate_news_to_spikes(spikes, news, corr_data=None, econ_events=None):
    """Match news, correlated asset moves, and economic events to volume spike dates."""
    correlated = []
    for idx, spike in spikes.iterrows():
        spike_date = idx.date() if hasattr(idx, 'date') else idx
        matched_news = []
        for article in news:
            if article['published']:
                news_date = article['published'].date()
                diff = (spike_date - news_date).days
                if 0 <= diff <= 1:
                    matched_news.append(article)

        # ── Correlated asset snapshot for this spike date ──
        asset_moves = {}
        if corr_data:
            for name, df in corr_data.items():
                try:
                    # Find closest date match
                    date_matches = [d for d in df.index if d.date() == spike_date]
                    if date_matches:
                        row_idx = df.index.get_loc(date_matches[0])
                        if row_idx >= 1:
                            cur = df['Close'].iloc[row_idx]
                            prv = df['Close'].iloc[row_idx - 1]
                            chg_pct = ((cur / prv) - 1) * 100
                            asset_moves[name] = {'price': cur, 'change_pct': round(chg_pct, 2)}
                except Exception:
                    pass

        # ── Economic calendar event match ──
        matched_events = []
        if econ_events:
            for event in econ_events:
                ev_date = event.get('date')
                if ev_date and ev_date == spike_date:
                    matched_events.append(event)

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
            'asset_moves': asset_moves,
            'econ_events': matched_events[:3],
        })
    return correlated


def compute_correlations(gold_df, corr_data, window=30):
    """Compute rolling correlations between gold and other instruments."""
    results = {}
    gold_returns = gold_df['Close'].pct_change().tail(window)
    for name, df in corr_data.items():
        try:
            other_returns = df['Close'].pct_change().tail(window)
            common = gold_returns.index.intersection(other_returns.index)
            if len(common) > 10:
                corr = gold_returns.loc[common].corr(other_returns.loc[common])
                if not np.isnan(corr):
                    results[name] = round(corr, 2)
        except Exception:
            pass
    return results


def compute_multi_window_correlations(gold_df, corr_data):
    """Compute correlations across 7D, 30D, 90D windows."""
    return {
        '7D': compute_correlations(gold_df, corr_data, window=7),
        '30D': compute_correlations(gold_df, corr_data, window=30),
        '90D': compute_correlations(gold_df, corr_data, window=90),
    }


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


def compute_multi_tf_probability(df):
    """
    Compute directional probability for daily, weekly, and monthly timeframes.
    Returns dict with 'daily', 'weekly', 'monthly' keys, each containing:
      {'bullish': float, 'bearish': float, 'bias': str, 'rationale': str}
    """
    current = df['Close'].iloc[-1]
    results = {}

    # ── Daily probability (next 1-2 days) ──
    sma_5 = df['Close'].tail(5).mean()
    sma_20 = df['SMA_20'].iloc[-1] if 'SMA_20' in df.columns else df['Close'].tail(20).mean()
    rsi = df['RSI_14'].iloc[-1] if 'RSI_14' in df.columns else 50
    daily_bull = 50
    rationale_parts = []
    if current > sma_5:
        daily_bull += 8
        rationale_parts.append("above 5D avg")
    else:
        daily_bull -= 8
        rationale_parts.append("below 5D avg")
    if current > sma_20:
        daily_bull += 7
    else:
        daily_bull -= 7
    if rsi < 30:
        daily_bull += 12  # Oversold bounce probability
        rationale_parts.append("RSI oversold")
    elif rsi > 70:
        daily_bull -= 12  # Overbought pullback
        rationale_parts.append("RSI overbought")
    # Recent momentum — last 3 closes
    recent_3 = df['Close'].tail(3)
    up_days = sum(1 for i in range(1, len(recent_3)) if recent_3.iloc[i] > recent_3.iloc[i - 1])
    if up_days >= 2:
        daily_bull += 5
        rationale_parts.append("recent momentum up")
    elif up_days == 0:
        daily_bull -= 5
        rationale_parts.append("recent momentum down")
    daily_bull = max(15, min(85, daily_bull))
    results['daily'] = {
        'bullish': round(daily_bull), 'bearish': round(100 - daily_bull),
        'bias': 'BULLISH' if daily_bull > 55 else 'BEARISH' if daily_bull < 45 else 'NEUTRAL',
        'rationale': ", ".join(rationale_parts[:3]) if rationale_parts else "mixed signals",
    }

    # ── Weekly probability (next 5 days) ──
    sma_50 = df['SMA_50'].iloc[-1] if 'SMA_50' in df.columns else df['Close'].tail(50).mean()
    weekly_bull = 50
    w_parts = []
    if current > sma_20:
        weekly_bull += 10
        w_parts.append("above 20D MA")
    else:
        weekly_bull -= 10
        w_parts.append("below 20D MA")
    if current > sma_50:
        weekly_bull += 8
    else:
        weekly_bull -= 8
    # Weekly trend: 5D price change direction
    if len(df) >= 6:
        week_chg = (current - df['Close'].iloc[-6]) / df['Close'].iloc[-6] * 100
        if week_chg > 1:
            weekly_bull += 7
            w_parts.append(f"week up {week_chg:.1f}%")
        elif week_chg < -1:
            weekly_bull -= 7
            w_parts.append(f"week down {week_chg:.1f}%")
    weekly_bull = max(15, min(85, weekly_bull))
    results['weekly'] = {
        'bullish': round(weekly_bull), 'bearish': round(100 - weekly_bull),
        'bias': 'BULLISH' if weekly_bull > 55 else 'BEARISH' if weekly_bull < 45 else 'NEUTRAL',
        'rationale': ", ".join(w_parts[:3]) if w_parts else "mixed signals",
    }

    # ── Monthly probability (next 20 days) ──
    monthly_bull = 50
    m_parts = []
    if current > sma_50:
        monthly_bull += 12
        m_parts.append("above 50D MA")
    else:
        monthly_bull -= 12
        m_parts.append("below 50D MA")
    # Monthly trend: 20D price change
    if len(df) >= 21:
        month_chg = (current - df['Close'].iloc[-21]) / df['Close'].iloc[-21] * 100
        if month_chg > 3:
            monthly_bull += 10
            m_parts.append(f"month up {month_chg:.1f}%")
        elif month_chg < -3:
            monthly_bull -= 10
            m_parts.append(f"month down {month_chg:.1f}%")
        else:
            m_parts.append(f"month {month_chg:+.1f}%")
    # Volatility regime
    daily_vol = df['Close'].pct_change().tail(20).std()
    avg_vol = df['Close'].pct_change().tail(60).std() if len(df) >= 60 else daily_vol
    if daily_vol > avg_vol * 1.3:
        m_parts.append("high volatility")
    monthly_bull = max(15, min(85, monthly_bull))
    results['monthly'] = {
        'bullish': round(monthly_bull), 'bearish': round(100 - monthly_bull),
        'bias': 'BULLISH' if monthly_bull > 55 else 'BEARISH' if monthly_bull < 45 else 'NEUTRAL',
        'rationale': ", ".join(m_parts[:3]) if m_parts else "mixed signals",
    }

    return results


def compute_pivot_levels(df):
    """Compute Fibonacci pivot points from previous day data."""
    if len(df) < 2:
        return {'PP': 0, 'R1': 0, 'R2': 0, 'R3': 0, 'S1': 0, 'S2': 0, 'S3': 0}
    # Use the PREVIOUS completed day, not today's partial candle
    prev = df.iloc[-2]
    pp = (prev['High'] + prev['Low'] + prev['Close']) / 3
    r = prev['High'] - prev['Low']  # Previous day's range
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


def load_skill_brief():
    """Load the gold-market-brief skill output if available and fresh (today's date)."""
    try:
        skill_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'skill_brief.json')
        if not os.path.exists(skill_path):
            return None
        with open(skill_path, 'r') as f:
            data = json.load(f)
        # Only use if generated today
        brief_date = data.get('date', '')
        today = datetime.utcnow().strftime('%Y-%m-%d')
        if brief_date != today:
            return None
        return data
    except Exception:
        return None


def load_webhook_alerts():
    """Load TradingView webhook alerts from tv_alerts.json if file exists.
    JSON format: {"alerts": [{"time": "ISO datetime", "ticker": "XAUUSD", "message": "...", "type": "price_alert|indicator|custom"}]}
    Returns list of alert dicts sorted by time (newest first)."""
    try:
        alerts_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tv_alerts.json')
        if not os.path.exists(alerts_path):
            return []
        with open(alerts_path, 'r') as f:
            data = json.load(f)
        alerts = data.get('alerts', [])
        # Sort by time descending (newest first)
        alerts.sort(key=lambda x: x.get('time', ''), reverse=True)
        return alerts[:10]  # Return last 10 alerts
    except Exception:
        return []


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
    """Generate beginner, intermediate, and pro analysis with conviction-based content."""
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
    macd_hist = df['MACD_hist'].iloc[-1]
    macd_hist_prev = df['MACD_hist'].iloc[-2]
    vol_ratio = df['Vol_ratio'].iloc[-1]

    # ATR-based regime — SAME logic as regime bar for consistency
    atr_20day = df['ATR_14'].tail(20).mean()
    atr_ratio = atr / atr_20day if atr_20day > 0 else 1.0
    if atr_ratio > 1.5:
        vol_regime_label = "HIGH"
        vol_regime_desc = "high"
    elif atr_ratio > 1.2:
        vol_regime_label = "ELEVATED"
        vol_regime_desc = "elevated"
    else:
        vol_regime_label = "NORMAL"
        vol_regime_desc = "normal"

    # Count bullish/bearish drivers and extract specifics
    bull_count = sum(1 for d in drivers if d[2] == "BULLISH")
    bear_count = sum(1 for d in drivers if d[2] == "BEARISH")
    bull_drivers = [d for d in drivers if d[2] == "BULLISH"]
    bear_drivers = [d for d in drivers if d[2] == "BEARISH"]

    # Determine dominant force
    if bull_count > bear_count + 1:
        net_bias = "bullish"
        bias_strength = "strong" if bull_count >= bear_count + 3 else "moderate"
    elif bear_count > bull_count + 1:
        net_bias = "bearish"
        bias_strength = "strong" if bear_count >= bull_count + 3 else "moderate"
    else:
        net_bias = "mixed"
        bias_strength = "evenly balanced"

    # Trend assessment
    above_sma20 = current > sma20
    above_sma50 = sma50 is not None and current > sma50
    if above_sma20 and above_sma50:
        trend_state = "uptrend"
        trend_desc = "above both its 20-day and 50-day moving averages"
    elif above_sma20:
        trend_state = "recovering"
        trend_desc = "above its 20-day average but still working through the 50-day"
    elif sma50 and not above_sma20 and not above_sma50:
        trend_state = "downtrend"
        trend_desc = "below both its 20-day and 50-day moving averages"
    else:
        trend_state = "weakening"
        trend_desc = "below its 20-day average"

    # MACD momentum
    macd_expanding = abs(macd_hist) > abs(macd_hist_prev)
    macd_bullish = macd > macd_sig
    if macd_bullish and macd_expanding:
        macd_read = "bullish momentum is building"
    elif macd_bullish and not macd_expanding:
        macd_read = "bullish but momentum is fading"
    elif not macd_bullish and macd_expanding:
        macd_read = "bearish pressure is increasing"
    else:
        macd_read = "bearish but selling pressure is easing"

    # Bollinger context
    bb_width_pct = ((bb_upper - bb_lower) / current) * 100
    bb_compressed = bb_width_pct < 4.0
    if current > bb_upper * 0.99:
        bb_read = "pressing against the upper Bollinger Band — extended"
    elif current < bb_lower * 1.01:
        bb_read = "testing the lower Bollinger Band — stretched to the downside"
    elif bb_compressed:
        bb_read = "compressed within tight Bollinger Bands — a volatility expansion is likely"
    else:
        bb_read = "trading mid-range within the Bollinger Bands"

    # Distance from key MAs (for context)
    dist_sma20_pct = ((current - sma20) / sma20) * 100
    dist_sma50_pct = ((current - sma50) / sma50) * 100 if sma50 else 0

    # Recent spike context
    spike_context = ""
    if spikes_correlated:
        last_spike = spikes_correlated[0]
        spike_news = last_spike['news'][0]['title'] if last_spike['news'] else "No specific catalyst identified"
        spike_context = f"The most recent volume spike was on {last_spike['date']} ({last_spike['direction']}, {last_spike['vol_ratio']:.1f}x avg volume). Likely catalyst: {spike_news}"

    # Top driver names for narrative use
    top_bull = bull_drivers[0][0] if bull_drivers else None
    top_bear = bear_drivers[0][0] if bear_drivers else None

    # Annualized realized vol
    realized_vol_20d = df['Close'].pct_change().tail(20).std() * 100 * np.sqrt(252)

    # ─── BEGINNER ─── Narrative, not template
    if daily_pct >= 1.0:
        move_desc = f"a strong move higher of <b>${abs(daily_chg):,.2f}</b> ({daily_pct:+.2f}%)"
    elif daily_pct >= 0.3:
        move_desc = f"a solid gain of <b>${abs(daily_chg):,.2f}</b> ({daily_pct:+.2f}%)"
    elif daily_pct > 0:
        move_desc = f"a small gain of <b>${abs(daily_chg):,.2f}</b> ({daily_pct:+.2f}%)"
    elif daily_pct > -0.3:
        move_desc = f"a small dip of <b>${abs(daily_chg):,.2f}</b> ({daily_pct:+.2f}%)"
    elif daily_pct > -1.0:
        move_desc = f"a notable drop of <b>${abs(daily_chg):,.2f}</b> ({daily_pct:+.2f}%)"
    else:
        move_desc = f"a sharp sell-off of <b>${abs(daily_chg):,.2f}</b> ({daily_pct:+.2f}%)"

    # Beginner: what's happening + why + what it means
    beginner_bull_text = ""
    beginner_bear_text = ""
    if top_bull:
        why_bull = [d[3] for d in bull_drivers[:2] if len(d) > 3 and d[3]]
        beginner_bull_text = f"On the bullish side, {top_bull.lower()}" + (f" — {why_bull[0].lower()}" if why_bull else "") + "."
    if top_bear:
        why_bear = [d[3] for d in bear_drivers[:2] if len(d) > 3 and d[3]]
        beginner_bear_text = f"Working against gold: {top_bear.lower()}" + (f" — {why_bear[0].lower()}" if why_bear else "") + "."

    beginner_trend_read = f"The overall picture is <b>{net_bias}</b> right now — {'bulls are in control and the trend is on their side' if net_bias == 'bullish' and trend_state == 'uptrend' else 'sellers have the upper hand' if net_bias == 'bearish' else 'the market is pulling in both directions, so expect choppy price action'}."

    beginner = f"""<p>Gold is at <b>${current:,.2f}</b>, {move_desc} on the session.</p>

<p>The price is {trend_desc}, which tells us the short-term trend is <b>{'working in favour of buyers' if above_sma20 else 'under pressure'}</b>.</p>

<p>{beginner_bull_text} {beginner_bear_text}</p>

<p>{beginner_trend_read}</p>

<p style="font-size:11px;color:#a8b2c8;border-top:1px solid #1e2745;padding-top:8px;margin-top:8px;">{spike_context}</p>"""

    # ─── INTERMEDIATE ─── Actionable technicals with interpretation
    macd_signal_label = "bullish crossover" if macd_bullish else "bearish crossover"

    # Trend strength bar
    trend_signals = []
    if above_sma20: trend_signals.append("Price > 20 SMA ✓")
    else: trend_signals.append("Price < 20 SMA ✗")
    if above_sma50: trend_signals.append("Price > 50 SMA ✓")
    elif sma50: trend_signals.append("Price < 50 SMA ✗")
    if macd_bullish: trend_signals.append("MACD bullish ✓")
    else: trend_signals.append("MACD bearish ✗")
    if rsi > 50: trend_signals.append("RSI > 50 ✓")
    else: trend_signals.append("RSI < 50 ✗")
    bullish_checks = sum(1 for s in trend_signals if "✓" in s)
    trend_score = f"{bullish_checks}/{len(trend_signals)} bullish"

    intermediate = f"""<p><b>Price:</b> ${current:,.2f} ({daily_pct:+.2f}%) &nbsp;|&nbsp; <b>Trend Score:</b> {trend_score} {'🟢' if bullish_checks >= 3 else '🟡' if bullish_checks == 2 else '🔴'}</p>

<p style="font-size:11px;color:#94a3b8;margin:2px 0;">{' &nbsp;·&nbsp; '.join(trend_signals)}</p>

<p><b>Technical Setup:</b></p>
<ul style="margin:4px 0;padding-left:18px;font-size:12px;">
<li><b>RSI(14):</b> {rsi:.1f} — {'⚠️ Oversold territory, watch for a bounce' if rsi < 30 else '⚠️ Overbought, momentum may stall here' if rsi > 70 else 'neutral, no extreme reading'}</li>
<li><b>MACD:</b> {macd_signal_label} — {macd_read} (histogram {macd_hist:+.2f})</li>
<li><b>Bollinger Bands:</b> {bb_read} &nbsp;(${bb_lower:,.0f} — ${bb_upper:,.0f}, {bb_width_pct:.1f}% width)</li>
<li><b>ATR(14):</b> ${atr:,.2f} — volatility is <b>{vol_regime_desc}</b> ({atr_ratio:.1f}x 20-day avg)</li>
<li><b>Volume:</b> {vol_ratio:.1f}x average — {'above-average participation, confirms the move' if vol_ratio > 1.2 else 'average participation' if vol_ratio > 0.8 else 'thin volume — move lacks conviction'}</li>
</ul>

<p><b>Key levels:</b> Support at <b>${sma20:,.0f}</b> (20 SMA, {dist_sma20_pct:+.1f}% away){', <b>$' + f'{sma50:,.0f}' + '</b> (50 SMA)' if sma50 else ''}. Resistance at <b>${bb_upper:,.0f}</b> (upper BB).</p>

<p style="font-size:11px;color:#a8b2c8;border-top:1px solid #1e2745;padding-top:8px;margin-top:8px;">{spike_context}</p>"""

    # ─── PRO ─── Regime-aware, cross-asset coherent, conviction-based
    # Cross-asset narrative (not a list of fragments)
    cross_parts = []
    for d in drivers:
        name, _, impact = d[0], d[1], d[2]
        why = d[3] if len(d) > 3 else ""
        if 'DXY' in name or 'USD' in name:
            if impact == "BEARISH":
                cross_parts.append(f"DXY strength at {d[1]} is a headwind")
            else:
                cross_parts.append(f"Weak dollar ({d[1]}) supporting gold")
        elif '10Y' in name or 'yield' in name.lower():
            if impact == "BEARISH":
                cross_parts.append(f"10Y yields elevated — opportunity cost pressure")
            else:
                cross_parts.append(f"Falling yields reducing gold's carry disadvantage")
        elif 'VIX' in name:
            if impact == "BULLISH":
                cross_parts.append(f"VIX elevated — risk-off flows favour gold")
            else:
                cross_parts.append(f"VIX subdued — no panic bid")
        elif 'S&P' in name or 'equit' in name.lower():
            if impact == "BULLISH":
                cross_parts.append(f"Equity weakness driving safe-haven rotation")
            else:
                cross_parts.append(f"Risk-on in equities — competing for capital")
    cross_text = ". ".join(cross_parts[:4]) + "." if cross_parts else "No clear cross-asset signal today."

    # Divergence detection
    dxy_bearish = any(d[0] for d in drivers if ('DXY' in d[0] or 'USD' in d[0]) and d[2] == 'BEARISH')
    if dxy_bearish and daily_pct > 0:
        divergence_note = "<br><span style='color:#f0b90b;'>⚡ Gold rising despite dollar strength — safe-haven demand overriding normal inverse correlation.</span>"
    elif not dxy_bearish and daily_pct < 0:
        divergence_note = "<br><span style='color:#ef4444;'>⚡ Gold falling despite dollar weakness — selling pressure is dominant.</span>"
    else:
        divergence_note = ""

    # Conviction statement
    if net_bias == "bullish" and trend_state in ("uptrend", "recovering") and macd_bullish:
        conviction = f"Technicals and macro are aligned bullish. {bias_strength.title()} conviction on the long side while ${sma20:,.0f} holds."
    elif net_bias == "bearish" and trend_state in ("downtrend", "weakening") and not macd_bullish:
        conviction = f"Technicals and macro are aligned bearish. {bias_strength.title()} conviction on the short side while below ${sma20:,.0f}."
    elif net_bias == "bullish" and not macd_bullish:
        conviction = f"Macro tilts bullish ({bull_count}B/{bear_count}B) but momentum hasn't confirmed — wait for MACD crossover before adding."
    elif net_bias == "bearish" and macd_bullish:
        conviction = f"Macro tilts bearish ({bull_count}B/{bear_count}B) but price momentum is still positive — not a clean short setup."
    else:
        conviction = f"Macro mix is {bias_strength} ({bull_count}B/{bear_count}B). Range environment — trade the levels, not a directional bias."

    # Volume spike context for pro
    spike_count_2x = len([s for s in spikes_correlated if s['vol_ratio'] > 2]) if spikes_correlated else 0
    spike_summary = f"{spike_count_2x} sessions with &gt;2x volume in past month" + (f" — institutional participation is {'elevated' if spike_count_2x >= 3 else 'normal'}" if spike_count_2x else "") + "."

    pro = f"""<p><b>Regime:</b> <span style="color:{'#ef4444' if vol_regime_label == 'HIGH' else '#f59e0b' if vol_regime_label == 'ELEVATED' else '#10b981'};font-weight:700;">{vol_regime_label}</span> volatility ({atr_ratio:.2f}x ATR ratio) &nbsp;|&nbsp; ATR ${atr:,.2f} &nbsp;|&nbsp; 20D realized vol: {realized_vol_20d:.1f}% ann.</p>

<p><b>Momentum:</b> RSI {rsi:.1f} | MACD {macd_read} (hist {macd_hist:+.2f}) | {bb_read} ({bb_width_pct:.1f}% BB width)</p>

<p><b>Cross-asset:</b> {cross_text}{divergence_note}</p>

<p><b>Volume:</b> Last session {vol_ratio:.1f}x avg. {spike_summary}</p>

<p style="background:rgba(240,185,11,0.06);border-radius:6px;padding:8px 12px;border-left:2px solid #f0b90b;margin-top:8px;">
<span style="font-size:9px;font-weight:700;color:#f0b90b;letter-spacing:0.8px;">CONVICTION</span><br>
<span style="color:#e2e8f0;">{conviction}</span></p>

<p style="font-size:11px;color:#a8b2c8;border-top:1px solid #1e2745;padding-top:8px;margin-top:8px;">{spike_context}</p>"""

    return beginner, intermediate, pro


def get_instrument_icon(name):
    """Return animated SVG icon HTML for an instrument name."""
    icons = {
        # Gold bar with shimmer
        "Gold Price": '<span class="icon-wrap icon-gold"><svg viewBox="0 0 24 24" fill="none"><path d="M4 18L7 8h10l3 10H4z" fill="#f0b90b" opacity="0.9"/><path d="M7 8L9 4h6l2 4" fill="#f5d060"/><path d="M4 18h16" stroke="#b8860b" stroke-width="1"/><line x1="9" y1="8" x2="8" y2="14" stroke="#fff" stroke-width="0.5" opacity="0.4"/></svg></span>',
        # Dollar sign
        "USD (DXY)": '<span class="icon-wrap icon-dollar"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#10b981" stroke-width="1.5" opacity="0.3"/><text x="12" y="16.5" text-anchor="middle" font-size="13" font-weight="bold" fill="#10b981" font-family="Arial">$</text></svg></span>',
        # Bond / certificate
        "US 10Y Yield": '<span class="icon-wrap icon-bond"><svg viewBox="0 0 24 24" fill="none"><rect x="3" y="5" width="18" height="14" rx="2" stroke="#3b82f6" stroke-width="1.5" fill="none"/><line x1="7" y1="9" x2="17" y2="9" stroke="#3b82f6" stroke-width="1" opacity="0.5"/><line x1="7" y1="12" x2="14" y2="12" stroke="#3b82f6" stroke-width="1" opacity="0.4"/><line x1="7" y1="15" x2="11" y2="15" stroke="#3b82f6" stroke-width="1" opacity="0.3"/><circle cx="17" cy="14" r="2" stroke="#f0b90b" stroke-width="1" fill="none"/></svg></span>',
        # VIX flame
        "VIX (Fear Index)": '<span class="icon-wrap icon-vix"><svg viewBox="0 0 24 24" fill="none"><path d="M12 2C12 2 7 9 7 14c0 2.8 2.2 5 5 5s5-2.2 5-5C17 9 12 2 12 2z" fill="#ef4444" opacity="0.8"/><path d="M12 8c0 0-2.5 3.5-2.5 6c0 1.4 1.1 2.5 2.5 2.5s2.5-1.1 2.5-2.5C14.5 11.5 12 8 12 8z" fill="#f59e0b" opacity="0.9"/></svg></span>',
        # Oil droplet
        "Crude Oil": '<span class="icon-wrap icon-oil"><svg viewBox="0 0 24 24" fill="none"><path d="M12 3C12 3 6 11 6 15.5C6 18.5 8.7 21 12 21s6-2.5 6-5.5C18 11 12 3 12 3z" fill="#8b5cf6" opacity="0.8"/><ellipse cx="10" cy="14" rx="1.5" ry="2" fill="#a78bfa" opacity="0.5" transform="rotate(-15 10 14)"/></svg></span>',
        # S&P 500 chart line
        "S&P 500": '<span class="icon-wrap icon-spx"><svg viewBox="0 0 24 24" fill="none"><rect x="2" y="4" width="20" height="16" rx="2" stroke="#f59e0b" stroke-width="1" opacity="0.3" fill="none"/><polyline points="4,16 8,12 11,14 15,8 20,10" stroke="#f59e0b" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>',
        # Gold trend up arrow
        "Gold Trend (SMA 20/50)": '<span class="icon-wrap icon-trend-up"><svg viewBox="0 0 24 24" fill="none"><path d="M4 18L12 6l8 12" stroke="#f0b90b" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/><line x1="12" y1="6" x2="12" y2="14" stroke="#f0b90b" stroke-width="1.5" opacity="0.4"/></svg></span>',
        # KPI icons
        "RSI": '<span class="icon-wrap icon-bond"><svg viewBox="0 0 24 24" fill="none"><rect x="2" y="4" width="20" height="16" rx="2" stroke="#a855f7" stroke-width="1" opacity="0.3" fill="none"/><polyline points="4,14 8,10 11,13 14,8 17,11 20,7" stroke="#a855f7" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg></span>',
        "ATR": '<span class="icon-wrap icon-bond"><svg viewBox="0 0 24 24" fill="none"><line x1="4" y1="12" x2="20" y2="12" stroke="#3b82f6" stroke-width="1" opacity="0.3"/><line x1="12" y1="5" x2="12" y2="19" stroke="#3b82f6" stroke-width="1" opacity="0.3"/><path d="M6 16L10 8l4 10 4-12" stroke="#3b82f6" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>',
        "Session Bias": '<span class="icon-wrap icon-vix"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="#f0b90b" stroke-width="1.5" fill="none" opacity="0.4"/><path d="M12 7v5l3.5 3.5" stroke="#f0b90b" stroke-width="1.5" stroke-linecap="round"/></svg></span>',
    }
    # Alias mapping for short names used in correlations / corr_data
    _aliases = {
        "DXY": "USD (DXY)", "US 10Y": "US 10Y Yield", "VIX": "VIX (Fear Index)",
        "EUR/USD": "USD (DXY)", "Silver": "Gold Price", "BTC/USD": "S&P 500",
    }
    return icons.get(name, icons.get(_aliases.get(name, ''), ''))


def get_session_clock_html():
    """Generate a session clock bar with 12hr format, per-market open/close status, overlaps, and countdowns."""
    from datetime import timezone, timedelta
    now_utc = datetime.now(timezone.utc)
    h = now_utc.hour
    m = now_utc.minute
    total_mins = h * 60 + m

    # 12-hour format helper
    def fmt12(dt):
        return dt.strftime('%I:%M %p').lstrip('0')

    # Timezone clocks
    est = now_utc + timedelta(hours=-5)      # US Eastern
    gmt = now_utc                             # London/GMT
    ist = now_utc + timedelta(hours=5, minutes=30)  # India
    jst = now_utc + timedelta(hours=9)        # Tokyo
    aest = now_utc + timedelta(hours=11)      # Sydney (AEDT)

    # ── Market Sessions (all times in UTC minutes from midnight) ──
    # Gold/Forex markets: Sunday 22:00 UTC → Friday 21:00 UTC
    # Individual session windows:
    sessions = [
        {'name': 'Sydney',   'icon': '🇦🇺', 'start': 21*60, 'end': 6*60,   'wraps': True,  'tz': 'AEDT', 'offset': 11},
        {'name': 'Tokyo',    'icon': '🇯🇵', 'start': 0*60,  'end': 9*60,   'wraps': False, 'tz': 'JST',  'offset': 9},
        {'name': 'India',    'icon': '🇮🇳', 'start': 3*60+30, 'end': 11*60+30, 'wraps': False, 'tz': 'IST', 'offset': 5.5},
        {'name': 'London',   'icon': '🇬🇧', 'start': 7*60,  'end': 16*60,  'wraps': False, 'tz': 'GMT',  'offset': 0},
        {'name': 'New York', 'icon': '🇺🇸', 'start': 12*60, 'end': 21*60,  'wraps': False, 'tz': 'ET',   'offset': -5},
    ]

    weekday = now_utc.weekday()
    is_weekend = weekday >= 5

    # Check if a session is active (handles sessions that wrap past midnight)
    def is_active(s):
        if is_weekend:
            return False
        if s['wraps']:
            return total_mins >= s['start'] or total_mins < s['end']
        return s['start'] <= total_mins < s['end']

    # Countdown in minutes to a target time (in UTC minutes)
    def countdown_mins(target_mins):
        diff = target_mins - total_mins
        if diff <= 0:
            diff += 24 * 60
        return diff

    def fmt_countdown(mins):
        hrs = mins // 60
        rem = mins % 60
        if hrs > 0:
            return f"{hrs}h {rem}m"
        return f"{rem}m"

    # Build session status rows
    session_rows = ""
    if is_weekend:
        # Show when market reopens (Sunday 22:00 UTC)
        if weekday == 5:  # Saturday
            reopen_hrs = (24 - h - 1) + 22 + (60 - m) / 60
        else:  # Sunday
            reopen_mins = countdown_mins(22 * 60)
            reopen_hrs = reopen_mins / 60
        session_rows = (
            f'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">'
            f'<span class="session-badge inactive">Market Closed — Weekend</span>'
            f'<span style="font-size:9px;color:#5a6a8a;">Reopens Sunday 10:00 PM UTC ({int(reopen_hrs)}h)</span>'
            f'</div>'
        )
    else:
        active_sessions = []
        for s in sessions:
            active = is_active(s)
            if active:
                active_sessions.append(s['name'])
                # Countdown to close
                close_mins = countdown_mins(s['end'])
                local_time = now_utc + timedelta(hours=s['offset'])
                session_rows += (
                    f'<div style="display:flex;align-items:center;gap:8px;padding:3px 0;">'
                    f'<span class="session-badge active">{s["icon"]} {s["name"]}</span>'
                    f'<span style="font-size:9px;color:#10b981;font-weight:700;">OPEN</span>'
                    f'<span style="font-size:9px;color:#a8b2c8;">Closes in <b style="color:#f0b90b;">{fmt_countdown(close_mins)}</b></span>'
                    f'<span style="font-size:9px;color:#5a6a8a;">({fmt12(local_time)} {s["tz"]})</span>'
                    f'</div>'
                )
            else:
                # Countdown to open
                open_mins = countdown_mins(s['start'])
                session_rows += (
                    f'<div style="display:flex;align-items:center;gap:8px;padding:3px 0;">'
                    f'<span class="session-badge inactive">{s["icon"]} {s["name"]}</span>'
                    f'<span style="font-size:9px;color:#ef4444;font-weight:700;">CLOSED</span>'
                    f'<span style="font-size:9px;color:#5a6a8a;">Opens in {fmt_countdown(open_mins)}</span>'
                    f'</div>'
                )

        # ── Overlap detection with explicit UTC windows ──
        # Define all known overlaps with their UTC time ranges
        overlap_windows = [
            {'name': 'Sydney–Tokyo',               'start': 0*60,   'end': 6*60,   'wraps': False, 'note': 'Asia liquidity'},
            {'name': 'Tokyo–India',                 'start': 3*60+30,'end': 9*60,   'wraps': False, 'note': 'Asia crossover'},
            {'name': 'India–London',                'start': 7*60,   'end': 11*60+30,'wraps': False, 'note': 'Asia–Europe bridge'},
            {'name': 'London–New York',             'start': 12*60,  'end': 16*60,  'wraps': False, 'note': 'Peak liquidity & volatility'},
        ]

        active_overlaps = []
        upcoming_overlap = None
        for ow in overlap_windows:
            ow_active = False
            if ow.get('wraps'):
                ow_active = total_mins >= ow['start'] or total_mins < ow['end']
            else:
                ow_active = ow['start'] <= total_mins < ow['end']

            if ow_active:
                ends_in = countdown_mins(ow['end'])
                active_overlaps.append((ow, ends_in))
            elif not upcoming_overlap:
                starts_in = countdown_mins(ow['start'])
                upcoming_overlap = (ow, starts_in)

        if active_overlaps:
            for ow, ends_in in active_overlaps:
                session_rows += (
                    f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">'
                    f'<span class="session-badge overlap">⚡ {ow["name"]} Overlap</span>'
                    f'<span style="font-size:9px;color:#f0b90b;font-weight:700;">ACTIVE</span>'
                    f'<span style="font-size:9px;color:#a8b2c8;">Ends in <b style="color:#f0b90b;">{fmt_countdown(ends_in)}</b></span>'
                    f'<span style="font-size:8px;color:#5a6a8a;">({ow["note"]})</span>'
                    f'</div>'
                )
        elif upcoming_overlap:
            ow, starts_in = upcoming_overlap
            session_rows += (
                f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">'
                f'<span class="session-badge inactive">⏳ Next: {ow["name"]}</span>'
                f'<span style="font-size:9px;color:#5a6a8a;">Starts in {fmt_countdown(starts_in)}</span>'
                f'<span style="font-size:8px;color:#5a6a8a;">({ow["note"]})</span>'
                f'</div>'
            )

    return (
        f'<div class="session-clock">'
        f'<div class="session-clock-times">'
        f'<div class="session-clock-zone"><div class="tz-label">New York</div><div class="tz-time">{fmt12(est)}</div></div>'
        f'<div class="session-clock-zone"><div class="tz-label">London</div><div class="tz-time">{fmt12(gmt)}</div></div>'
        f'<div class="session-clock-zone"><div class="tz-label">India</div><div class="tz-time">{fmt12(ist)}</div></div>'
        f'<div class="session-clock-zone"><div class="tz-label">Tokyo</div><div class="tz-time">{fmt12(jst)}</div></div>'
        f'<div class="session-clock-zone"><div class="tz-label">Sydney</div><div class="tz-time">{fmt12(aest)}</div></div>'
        f'</div>'
        f'<div style="display:flex;flex-direction:column;gap:2px;">{session_rows}</div>'
        f'</div>'
    )


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

    # Build macro driver cards HTML
    # Check beginner mode from session state
    is_beginner = st.session_state.get('beginner_mode', True)

    # Beginner-friendly explanations for each driver
    _beginner_explain = {
        'USD (DXY)': {
            'BULLISH': ('The US Dollar is weakening', 'When the dollar drops, gold usually rises because gold becomes cheaper for foreign buyers.', '👍 Good for gold'),
            'BEARISH': ('The US Dollar is getting stronger', 'When the dollar rises, gold usually falls because gold becomes more expensive for foreign buyers.', '👎 Bad for gold'),
            'NEUTRAL': ('The US Dollar is steady', 'No major dollar move right now — not pushing gold either way.', '➡️ No effect'),
        },
        'US 10Y Yield': {
            'BULLISH': ('Bond yields are falling', 'When interest rates drop, gold becomes more attractive because bonds pay less — money flows into gold instead.', '👍 Good for gold'),
            'BEARISH': ('Bond yields are rising', 'When interest rates rise, investors prefer bonds over gold because bonds now pay more. Gold loses appeal.', '👎 Bad for gold'),
            'NEUTRAL': ('Bond yields are stable', 'Yields aren\'t moving much — no major pressure on gold from the bond market.', '➡️ No effect'),
        },
        'VIX (Fear Index)': {
            'BULLISH': ('Market fear is high', 'The "Fear Index" is elevated — investors are nervous and buying gold as a safe place to park money.', '👍 Good for gold'),
            'BEARISH': ('Markets are calm', 'Fear is low — investors feel confident and prefer stocks over safe-haven assets like gold.', '👎 Bad for gold'),
            'NEUTRAL': ('Market anxiety is normal', 'Fear levels are average — no panic buying or confident selling.', '➡️ No effect'),
        },
        'Gold Trend (SMA 20/50)': {
            'BULLISH': ('Gold\'s trend is pointing up', 'The price is above its key moving averages — the trend is your friend, and right now it favours buyers.', '👍 Trend supports gold'),
            'BEARISH': ('Gold\'s trend is pointing down', 'The price is below its key moving averages — the trend is working against gold right now.', '👎 Trend is against gold'),
            'NEUTRAL': ('Gold\'s trend is unclear', 'Mixed signals from the moving averages — no clear direction yet.', '➡️ No clear trend'),
        },
        'S&P 500': {
            'BULLISH': ('The stock market is falling', 'When stocks drop, investors get nervous and move money into gold for safety — this is called a "risk-off" move.', '👍 Good for gold'),
            'BEARISH': ('The stock market is rising', 'When stocks are rallying, investors prefer equities over gold — less demand for safe-haven assets.', '👎 Bad for gold'),
            'NEUTRAL': ('Stocks are flat', 'No big move in equities — not driving gold either way.', '➡️ No effect'),
        },
        'Crude Oil': {
            'BULLISH': ('Oil prices are rising', 'Rising oil signals inflation fears — and gold is the classic inflation hedge. Money flows into gold.', '👍 Good for gold'),
            'BEARISH': ('Oil prices are falling', 'Falling oil eases inflation worries — less reason to hold gold as a hedge.', '👎 Bad for gold'),
            'NEUTRAL': ('Oil is stable', 'No major oil move — not pushing gold in either direction.', '➡️ No effect'),
        },
    }

    driver_cards_html = '<div class="driver-grid">'
    for d in drivers:
        name, detail, impact = d[0], d[1], d[2]
        why = d[3] if len(d) > 3 else ""
        card_class = "bullish" if impact == "BULLISH" else "bearish" if impact == "BEARISH" else "neutral"
        chg_color = "#10b981" if impact == "BULLISH" else "#ef4444" if impact == "BEARISH" else "#5a6a8a"

        if is_beginner and name in _beginner_explain:
            # ── BEGINNER MODE: plain English cards ──
            explain = _beginner_explain[name].get(impact, _beginner_explain[name].get('NEUTRAL'))
            headline, explanation, verdict = explain
            driver_cards_html += (
                f'<div class="driver-card {card_class}" style="padding:10px 12px;">'
                f'<div class="dc-name" style="font-size:10px;margin-bottom:2px;">{name}</div>'
                f'<div style="font-size:12px;font-weight:700;color:#e2e8f0;margin-bottom:4px;">{headline}</div>'
                f'<div style="font-size:10px;color:#94a3b8;line-height:1.4;margin-bottom:6px;">{explanation}</div>'
                f'<div style="font-size:11px;font-weight:700;color:{chg_color};border-top:1px solid rgba(255,255,255,0.05);padding-top:5px;">{verdict}</div>'
                f'</div>'
            )
        else:
            # ── PRO MODE: compact data cards ──
            if why:
                gold_label = why[:45]
            else:
                gold_arrow = "↑" if impact == "BULLISH" else "↓" if impact == "BEARISH" else "→"
                gold_label = f"Gold {gold_arrow}"
            driver_cards_html += (
                f'<div class="driver-card {card_class}">'
                f'<div class="dc-name">{name}</div>'
                f'<div class="dc-value">{detail}</div>'
                f'<div class="dc-change" style="color:{chg_color};">{gold_label}</div>'
                f'</div>'
            )
    driver_cards_html += '</div>'

    # Inline driver summary for the text paragraph
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

    # Key levels to watch — show S1/S2 and R1/R2 for more useful context
    s1, s2 = pivots['S1'], pivots['S2']
    r1, r2 = pivots['R1'], pivots['R2']
    pp = pivots['PP']
    levels_text = (
        f'Fibonacci Pivots — '
        f'Pivot: <b>${pp:,.0f}</b> · '
        f'Support: <span class="highlight-up">${s1:,.0f}</span> / <span class="highlight-up">${s2:,.0f}</span> · '
        f'Resistance: <span class="highlight-down">${r1:,.0f}</span> / <span class="highlight-down">${r2:,.0f}</span>'
    )

    # ── Check for skill-generated brief (richer analysis from gold-market-brief skill) ──
    skill_brief = load_skill_brief()
    skill_section = ""
    if skill_brief:
        # Override bias with skill's conviction-based bias
        skill_bias = skill_brief.get('session_bias', '')
        if skill_bias in ('BULLISH', 'BEARISH', 'NEUTRAL'):
            bias = skill_bias
            if skill_bias == 'BULLISH':
                bias_color, bias_bg, bias_word = "#10b981", "rgba(16,185,129,0.12)", "bullish"
            elif skill_bias == 'BEARISH':
                bias_color, bias_bg, bias_word = "#ef4444", "rgba(239,68,68,0.12)", "bearish"
            else:
                bias_color, bias_bg, bias_word = "#f59e0b", "rgba(245,158,11,0.12)", "mixed"

        # Add skill's richer context sections
        parts = []
        if skill_brief.get('outlook'):
            parts.append(f'<p style="margin-top:10px;"><span style="color:#f0b90b;font-weight:700;font-size:9px;text-transform:uppercase;letter-spacing:0.8px;">Capt. Gold&rsquo;s Outlook</span><br>'
                         f'<span style="color:#e2e8f0;">{html_escape(skill_brief["outlook"])}</span></p>')
        if skill_brief.get('watching'):
            parts.append(f'<p><span style="color:#f0b90b;font-weight:700;font-size:9px;text-transform:uppercase;letter-spacing:0.8px;">Today I&rsquo;m Watching</span><br>'
                         f'<span style="color:#e2e8f0;">{html_escape(skill_brief["watching"])}</span></p>')
        if skill_brief.get('trade_context'):
            parts.append(f'<p><span style="color:#f0b90b;font-weight:700;font-size:9px;text-transform:uppercase;letter-spacing:0.8px;">Trade Context</span><br>'
                         f'<span style="color:#e2e8f0;">{html_escape(skill_brief["trade_context"])}</span></p>')
        if skill_brief.get('platform_signal'):
            parts.append(f'<p style="background:rgba(240,185,11,0.06);border-radius:6px;padding:8px 12px;border-left:2px solid #f0b90b;">'
                         f'<span style="font-size:9px;font-weight:700;color:#f0b90b;">PLATFORM SIGNAL</span><br>'
                         f'<span style="font-size:11px;color:#a8b2c8;">{html_escape(skill_brief["platform_signal"])}</span></p>')
        if parts:
            skill_section = ''.join(parts)
            skill_section += '<div style="font-size:8px;color:#3d4b6b;margin-top:6px;text-align:right;">Analysis: Gold Intel Daily Brief</div>'

    # Compose the brief — adapt language for beginner mode
    if is_beginner:
        # Beginner: plain English, no jargon
        if bias_word == "bullish":
            bias_explain = "Most market forces are <b style='color:#10b981;'>pushing gold higher</b> right now."
        elif bias_word == "bearish":
            bias_explain = "Most market forces are <b style='color:#ef4444;'>pushing gold lower</b> right now."
        else:
            bias_explain = "Market forces are <b style='color:#f59e0b;'>pulling gold in both directions</b> — expect choppy price action."

        # Beginner-friendly RSI
        if rsi < 30:
            rsi_beginner = f'Gold looks <span class="highlight-down">oversold</span> — it may be due for a bounce upward.'
        elif rsi > 70:
            rsi_beginner = f'Gold looks <span class="highlight-up">overbought</span> — it may pull back from here.'
        else:
            rsi_beginner = "Gold's momentum is in a normal range — no extreme readings."

        brief_html = (
            f'<p>Gold is trading at <b>${current:,.2f}</b>, '
            f'<span class="{dir_class}">{direction} ${abs(daily_chg):,.2f} ({daily_pct:+.2f}%)</span> on the session.</p>'
            f'<p>{bias_explain}</p>'
            f'<p style="font-size:11px;color:#94a3b8;margin-bottom:6px;">Here\'s what\'s moving gold — each card explains how it affects the price:</p>'
            f'{driver_cards_html}'
            f'<p style="margin-top:12px;">{rsi_beginner} {range_text}</p>'
            f'{skill_section}'
        )
    else:
        # Pro: data-dense, technical
        brief_html = (
            f'<p>Gold is trading at <b>${current:,.2f}</b>, '
            f'<span class="{dir_class}">{direction} ${abs(daily_chg):,.2f} ({daily_pct:+.2f}%)</span> on the session. '
            f'The daily trend is <b>{signal_trend.replace("_", " ").lower()}</b> and macro conditions are <b>{bias_word}</b>.</p>'
            f'{driver_cards_html}'
            f'<p style="margin-top:12px;">{rsi_text}. {range_text}</p>'
            f'<p>{sig_text}</p>'
            f'<p>{levels_text}</p>'
            f'{skill_section}'
        )

    return brief_html, bias, bias_color, bias_bg


def get_market_regime_html(gold_df, econ_events):
    """Compute and render market regime status bar with volatility, event risk, and session overlap."""
    # Current ATR vs 20-day average
    atr_current = gold_df['ATR_14'].iloc[-1] if 'ATR_14' in gold_df.columns else 0
    atr_20day = gold_df['ATR_14'].tail(20).mean() if 'ATR_14' in gold_df.columns else atr_current
    atr_ratio = atr_current / atr_20day if atr_20day > 0 else 1.0

    # Regime classification
    if atr_ratio > 1.5:
        regime = "HIGH VOLATILITY"
        regime_badge_class = "regime-high"
        regime_color = "#ef4444"
    elif atr_ratio > 1.2:
        regime = "ELEVATED"
        regime_badge_class = "regime-elevated"
        regime_color = "#f59e0b"
    else:
        regime = "NORMAL"
        regime_badge_class = "regime-normal"
        regime_color = "#10b981"

    # Check for HIGH impact economic events today
    high_events = []
    if econ_events:
        now_date = datetime.utcnow().date()
        # Known high-impact event short names for clean display
        _event_labels = {
            'nfp': 'NFP', 'non-farm': 'NFP', 'non farm': 'NFP', 'payroll': 'NFP',
            'fomc': 'FOMC', 'rate decision': 'Fed Rate Decision',
            'cpi': 'CPI', 'consumer price': 'CPI',
            'pce': 'PCE', 'core pce': 'Core PCE',
            'gdp': 'GDP', 'powell': 'Fed Chair Powell',
            'fed chair': 'Fed Chair Speech',
        }
        for evt in econ_events:
            evt_date = evt.get('date')
            if evt_date and evt_date == now_date and evt.get('impact') == 'HIGH':
                # Extract a clean short label from the event name or title
                raw_name = evt.get('event_name', '') or evt.get('title', '')
                raw_lower = raw_name.lower()
                short_label = None
                for kw, label in _event_labels.items():
                    if kw in raw_lower:
                        short_label = label
                        break
                if not short_label:
                    # Fallback: take first 4 meaningful words
                    words = [w for w in raw_name.split() if len(w) > 2][:4]
                    short_label = ' '.join(words) if words else 'Economic Data'
                released = evt.get('released', False)
                actual = evt.get('actual')
                forecast = evt.get('forecast')
                if released and actual:
                    detail = f'{short_label}: {actual}'
                    if forecast:
                        detail += f' vs {forecast} exp'
                    high_events.append(('released', detail))
                else:
                    high_events.append(('upcoming', short_label))

    event_text = ""
    for evt_status, evt_label in high_events[:2]:
        if evt_status == 'released':
            event_text += (f'<div class="regime-info-item" style="color:#f59e0b;">'
                          f'📊 {html_escape(evt_label)}</div>')
        else:
            event_text += (f'<div class="regime-info-item" style="color:#ef4444;">'
                          f'⚠️ Upcoming: {html_escape(evt_label)}</div>')

    # Active session from session clock logic
    now_utc = datetime.utcnow()
    utc_h = now_utc.hour
    total_mins = utc_h * 60 + now_utc.minute
    is_weekend = now_utc.weekday() >= 5

    session_text = ""
    if not is_weekend:
        if 12*60 <= total_mins < 16*60:
            session_text = '<div class="regime-info-item" style="color:#10b981;">🔥 London–NY Overlap</div>'
        elif 7*60 <= total_mins < 11*60+30:
            session_text = '<div class="regime-info-item" style="color:#a8b2c8;">India–London Overlap</div>'
        elif 0*60 <= total_mins < 6*60:
            session_text = '<div class="regime-info-item" style="color:#a8b2c8;">Sydney–Tokyo Overlap</div>'
    elif is_weekend:
        session_text = '<div class="regime-info-item" style="color:#5a6a8a;">Market Closed</div>'

    regime_html = (
        f'<div class="regime-bar">'
        f'<div class="regime-badge {regime_badge_class}">{regime} · {atr_ratio:.1f}x ATR</div>'
        f'<div class="regime-info">'
        f'{event_text}'
        f'{session_text}'
        f'</div>'
        f'</div>'
    )
    return regime_html


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
            <div style="font-size:9px;color:#5a6a8a;margin-top:3px;letter-spacing:0.5px;">by <span style="color:#f0b90b;">Capt. Gold</span>
                &nbsp;·&nbsp; <a href="https://t.me/capt_gold" target="_blank" style="color:#3b82f6;text-decoration:none;font-weight:600;">✈ Telegram</a>
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:16px;">
            <span class="live-badge"><span class="live-dot"></span>LIVE DATA</span>
            <span style="font-family:'JetBrains Mono'; font-size:11px; color:#6b7a99;">""" +
    datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC') + """</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar: Branding + Controls + CTA ──
    with st.sidebar:
        # Product branding
        st.markdown("""<div style="text-align:center;padding:12px 0 16px;">
            <div style="font-size:18px;font-weight:900;color:#f0b90b;letter-spacing:2px;">GOLD COMMAND</div>
            <div style="font-size:9px;color:#5a6a8a;letter-spacing:1px;margin-top:2px;">XAU/USD Intelligence Terminal</div>
            <div style="font-size:8px;color:#3d4b6b;margin-top:4px;">v2.0 · by Capt. Gold</div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div style="border-bottom:1px solid #1a2240;margin:8px 0;"></div>', unsafe_allow_html=True)

        # Quick stats summary (always visible in sidebar)
        st.markdown("### Quick Stats")
        st.markdown("""<div style="font-size:10px;color:#6b7a99;margin-bottom:8px;">
            Data auto-updates every refresh cycle.
        </div>""", unsafe_allow_html=True)

        st.markdown('<div style="border-bottom:1px solid #1a2240;margin:12px 0;"></div>', unsafe_allow_html=True)

        # Auto-refresh
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

        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = time.time()

        elapsed = time.time() - st.session_state.last_refresh
        next_in = max(0, refresh_interval * 60 - elapsed)
        st.markdown(f"""<div style="font-size:11px;color:#6b7a99;margin-top:8px;">
            Last refresh: {int(elapsed)}s ago<br>
            Next refresh: {int(next_in)}s
        </div>""", unsafe_allow_html=True)

        st.markdown('<div style="border-bottom:1px solid #1a2240;margin:12px 0;"></div>', unsafe_allow_html=True)

        # Beginner mode indicator (toggle is on main page for visibility)
        st.markdown("### Display Mode")
        bm_status = "ON" if st.session_state.get('beginner_mode', True) else "OFF"
        bm_color = "#10b981" if bm_status == "ON" else "#5a6a8a"
        st.markdown(f'<div style="font-size:11px;color:{bm_color};font-weight:600;">👶 Beginner Mode: {bm_status}</div>'
                    f'<div style="font-size:9px;color:#5a6a8a;margin-top:2px;">Toggle is at the top-right of the main page</div>',
                    unsafe_allow_html=True)

        st.markdown('<div style="border-bottom:1px solid #1a2240;margin:12px 0;"></div>', unsafe_allow_html=True)

        # Subscription CTA
        st.markdown("""<div style="background:linear-gradient(135deg,rgba(240,185,11,0.08),rgba(240,185,11,0.02));
            border:1px solid rgba(240,185,11,0.2);border-radius:10px;padding:14px;text-align:center;margin-top:8px;">
            <div style="font-size:11px;font-weight:800;color:#f0b90b;letter-spacing:0.5px;margin-bottom:6px;">UPGRADE TO PRO</div>
            <div style="font-size:10px;color:#8892ab;line-height:1.5;margin-bottom:10px;">
                Unlock SMC Engine, Backtesting,<br>Telegram Alerts & Priority Support
            </div>
            <div style="font-size:13px;font-weight:800;color:#f0b90b;margin-bottom:8px;">
                $19.99<span style="font-size:9px;color:#6b7a99;font-weight:400;">/month</span>
            </div>
            <div style="font-size:8px;color:#5a6a8a;">7-day free trial · Cancel anytime</div>
            <a href="https://t.me/capt_gold" target="_blank" style="display:inline-block;margin-top:10px;
                background:rgba(59,130,246,0.1);color:#3b82f6;border:1px solid rgba(59,130,246,0.2);
                border-radius:8px;padding:8px 16px;font-size:10px;font-weight:700;text-decoration:none;
                letter-spacing:0.5px;">✈ Join Telegram Channel</a>
        </div>""", unsafe_allow_html=True)

        # What's included in free vs pro
        st.markdown("""<div style="margin-top:12px;font-size:9px;color:#5a6a8a;line-height:1.8;">
            <div style="font-weight:700;color:#6b7a99;margin-bottom:4px;">FREE TIER (Current)</div>
            ✅ Daily Brief &amp; KPI Dashboard<br>
            ✅ Price Ranges &amp; Key Levels<br>
            ✅ Macro Drivers &amp; News Feed<br>
            ✅ Basic Signal Engine (15m)<br>
            ✅ 3-Tier Analysis<br>
            <div style="font-weight:700;color:#f0b90b;margin-top:8px;margin-bottom:4px;">PRO TIER</div>
            🔒 SMC Engine (Order Blocks + FVGs)<br>
            🔒 Signal Backtesting &amp; Stats<br>
            🔒 5m Entry Timeframe<br>
            🔒 Telegram Alert Integration<br>
            🔒 Custom S/R Level Alerts<br>
            🔒 Priority Refresh (1 min)<br>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div style="border-bottom:1px solid #1a2240;margin:12px 0;"></div>', unsafe_allow_html=True)

        # ICMarkets Live Price Widget + Partner Banner
        st.markdown("""<div style="text-align:center;margin-bottom:6px;">
            <a href="https://icmarkets.com/?camp=87951" target="_blank">
                <img src="https://promo.icmarkets.com/Logos/2021/400x110/BAN_ICM_black_400x110.png"
                     style="width:100%;max-width:260px;border-radius:6px;" alt="ICMarkets"/>
            </a>
        </div>""", unsafe_allow_html=True)

        st.components.v1.iframe(
            src="https://secure.icmarkets.com//Partner/Widget/PriceWidget/87951",
            width=273,
            height=480,
            scrolling=False,
        )

        st.markdown("""<div style="text-align:center;margin-top:4px;">
            <a href="https://icmarkets.com/?camp=87951" target="_blank"
               style="font-size:9px;color:#60a5fa;text-decoration:none;font-weight:600;">
                Open Live Account →
            </a>
            <span style="font-size:7px;color:#3d4b6b;display:block;margin-top:3px;">
                Raw spreads from 0.0 pips · ASIC regulated
            </span>
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

    # ── Beginner Mode toggle — placed BEFORE data computation so all components can read it ──
    bm_col1, bm_col2 = st.columns([6, 1])
    with bm_col2:
        beginner_mode = st.toggle("👶 Beginner", value=st.session_state.get('beginner_mode', True),
                                   help="Simplify everything — plain English explanations, no jargon")
        st.session_state['beginner_mode'] = beginner_mode

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
    econ_events = fetch_economic_calendar()
    spikes_correlated = correlate_news_to_spikes(spikes, news, corr_data=corr_data, econ_events=econ_events)
    correlations = compute_correlations(gold_df, corr_data)
    multi_corr = compute_multi_window_correlations(gold_df, corr_data)
    up_probs, down_probs = compute_probability_targets(gold_df)
    mtf_probs = compute_multi_tf_probability(gold_df)
    pivots = compute_pivot_levels(gold_df)
    ranges = compute_ranges(gold_df)
    drivers = assess_macro_drivers(gold_df, corr_data)
    beginner, intermediate, pro = generate_three_tier_analysis(gold_df, spikes_correlated, drivers)

    # ── New Intelligence Features ──
    cot_data = fetch_cot_data()
    etf_flows = fetch_etf_flows()
    gs_ratio = compute_gold_silver_ratio(gold_df, corr_data)
    fear_greed = compute_fear_greed_index(gold_df, corr_data, drivers)
    candle_patterns = detect_candlestick_patterns(gold_df)
    news_sentiment = compute_news_sentiment(news)

    # ── Multi-Timeframe RSI + Fibonacci ──
    mtf_raw = fetch_multi_tf_data(GOLD_TICKER)
    mtf_rsi = compute_multi_tf_rsi(mtf_raw)
    mtf_fib = compute_multi_tf_fib(mtf_raw)

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
    # WELCOME BANNER (first visit only)
    # ══════════════════════════════════════════════════
    if 'visited' not in st.session_state:
        st.session_state.visited = True
        st.markdown("""<div style="background:linear-gradient(135deg,rgba(240,185,11,0.06),rgba(16,185,129,0.04));
            border:1px solid rgba(240,185,11,0.15);border-radius:10px;padding:16px 20px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-size:14px;font-weight:700;color:#f0b90b;margin-bottom:4px;">Welcome to Gold Command</div>
                    <div style="font-size:11px;color:#8892ab;line-height:1.6;">
                        Your AI-powered gold market intelligence terminal. Start with the <b style="color:#f0b90b;">📋 Daily Brief</b> tab for a quick summary,
                        then explore <b style="color:#f0b90b;">Trade Signals</b> and <b style="color:#f0b90b;">Intelligence</b> tabs.
                        Hover any <span style="display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;border-radius:50%;
                        background:rgba(240,185,11,0.12);color:#f0b90b;font-size:9px;font-weight:800;border:1px solid rgba(240,185,11,0.2);">?</span>
                        icon for beginner explanations.
                    </div>
                </div>
                <div style="font-size:9px;color:#5a6a8a;text-align:right;white-space:nowrap;margin-left:16px;">
                    New to gold trading?<br>Toggle <b style="color:#f0b90b;">Beginner Mode</b> in sidebar
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # STATS TICKER (social proof + live metrics)
    # ══════════════════════════════════════════════════
    n_signals = len(trade_signals)
    n_drivers = len(drivers)
    n_bull = sum(1 for d in drivers if d[2] == "BULLISH")
    n_spikes = len(spikes_correlated) if spikes_correlated else 0
    n_news = len(news) if news else 0
    st.markdown(f"""<div style="display:flex;justify-content:center;gap:24px;padding:8px 0;margin-bottom:12px;
        border-bottom:1px solid rgba(26,34,64,0.4);flex-wrap:wrap;">
        <span style="font-size:10px;color:#5a6a8a;display:flex;align-items:center;gap:4px;">
            <span style="color:#f0b90b;font-weight:700;">{n_signals}</span> Active Signals</span>
        <span style="font-size:10px;color:#5a6a8a;display:flex;align-items:center;gap:4px;">
            <span style="color:#10b981;font-weight:700;">{n_bull}/{n_drivers}</span> Bullish Drivers</span>
        <span style="font-size:10px;color:#5a6a8a;display:flex;align-items:center;gap:4px;">
            <span style="color:#a855f7;font-weight:700;">{n_spikes}</span> Volume Spikes (6M)</span>
        <span style="font-size:10px;color:#5a6a8a;display:flex;align-items:center;gap:4px;">
            <span style="color:#ef4444;font-weight:700;">{n_news}</span> Live Headlines</span>
        <span style="font-size:10px;color:#5a6a8a;display:flex;align-items:center;gap:4px;">
            <span style="color:#3b82f6;font-weight:700;">6</span> Intelligence Modules</span>
    </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # DISPLAY — ABOVE TABS (always visible)
    # ══════════════════════════════════════════════════
    rsi_val = gold_df['RSI'].iloc[-1]
    brief_text, brief_bias, brief_bias_color, brief_bias_bg = generate_daily_brief_text(
        current, daily_chg, daily_pct, rsi_val,
        gold_df['ATR_14'].iloc[-1], drivers, trade_signals,
        signal_trend, ranges, pivots, key_levels
    )

    # Session Clock Bar — above the Daily Brief
    session_clock_html = get_session_clock_html()
    st.markdown(session_clock_html, unsafe_allow_html=True)

    # Market Regime Status Bar — shows volatility, event risk, and session overlap
    regime_html = get_market_regime_html(gold_df, econ_events)
    st.markdown(regime_html, unsafe_allow_html=True)


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

    icon_gold = get_instrument_icon("Gold Price")
    icon_rsi = get_instrument_icon("RSI")
    icon_atr = get_instrument_icon("ATR")
    icon_bias = get_instrument_icon("Session Bias")

    tt_rsi = tooltip("RSI", f"{icon_rsi} RSI (14)")
    tt_atr = tooltip("ATR", f"{icon_atr} ATR (14)")
    tt_bias = tooltip("Session Bias", f"{icon_bias} Session Bias")
    tt_6mh = tooltip("6M High/Low", f"{icon_gold} 6M High")
    tt_6ml = tooltip("6M High/Low", f"{icon_gold} 6M Low")

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card" style="--kpi-accent: #f0b90b;">
            <div class="kpi-label">{icon_gold} Gold Price</div>
            <div class="kpi-value" style="color: #f0b90b;">${current:,.2f}</div>
            <div class="kpi-delta {'up' if daily_chg >= 0 else 'down'}">{chg_arrow} ${abs(daily_chg):,.2f} ({daily_pct:+.1f}%)</div>
        </div>
        <div class="kpi-card" style="--kpi-accent: {rsi_color};">
            <div class="kpi-label">{tt_rsi}</div>
            <div class="kpi-value">{rsi_val:.1f}</div>
            <div class="kpi-delta neutral" style="color:{rsi_color};background:rgba(0,0,0,0.2);">{rsi_status}</div>
        </div>
        <div class="kpi-card" style="--kpi-accent: #3b82f6;">
            <div class="kpi-label">{tt_atr}</div>
            <div class="kpi-value">${gold_df['ATR_14'].iloc[-1]:,.0f}</div>
            <div class="kpi-delta neutral">Daily Range</div>
        </div>
        <div class="kpi-card" style="--kpi-accent: #ef4444;">
            <div class="kpi-label">{tt_6mh}</div>
            <div class="kpi-value">${high_52w:,.0f}</div>
            <div class="kpi-delta {'down' if current < high_52w else 'up'}">{((current/high_52w)-1)*100:+.1f}%</div>
        </div>
        <div class="kpi-card" style="--kpi-accent: #10b981;">
            <div class="kpi-label">{tt_6ml}</div>
            <div class="kpi-value">${low_52w:,.0f}</div>
            <div class="kpi-delta up">{((current/low_52w)-1)*100:+.1f}%</div>
        </div>
        <div class="kpi-card" style="--kpi-accent: {fear_greed['color'] if fear_greed else '#f59e0b'};">
            <div class="kpi-label">Fear &amp; Greed</div>
            <div class="kpi-value" style="color:{fear_greed['color'] if fear_greed else '#f59e0b'};font-size:22px;">{fear_greed['score']:.0f}<span style="font-size:11px;color:#5a6a8a;">/100</span></div>
            <div class="kpi-delta neutral" style="color:{fear_greed['color'] if fear_greed else '#f59e0b'};background:rgba(0,0,0,0.2);">{fear_greed['label'] if fear_greed else 'N/A'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # TAB NAVIGATION
    # ══════════════════════════════════════════════════
    tab_brief, tab_dashboard, tab_signals, tab_intel, tab_news, tab_smc, tab_backtest = st.tabs([
        "📋 Daily Brief", "📊 Dashboard", "🎯 Trade Signals", "🧠 Intelligence", "📰 News & Events", "🔲 SMC Engine", "📈 Backtest"
    ])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB — DAILY BRIEF
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_brief:
        brief_daily, brief_weekly, brief_monthly = st.tabs(["Daily", "This Week", "This Month"])

        with brief_daily:
            brief_date = datetime.utcnow().strftime('%B %d, %Y')
            st.markdown(
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
                f'</div>',
                unsafe_allow_html=True
            )

            # 3-Tier Analysis inside Daily Brief
            st.markdown("""<div class="section-header" style="--section-accent: #a855f7; margin-top: 16px;">
                <span class="section-title">Market Analysis</span>
                <span class="pill pill-model">3-TIER</span>
            </div>""", unsafe_allow_html=True)

            tier_brief = st.radio("Perspective", ["Beginner", "Intermediate", "Pro"], horizontal=True, label_visibility="collapsed", key="brief_tier")

            if tier_brief == "Beginner":
                st.markdown(f'<div class="tier-tab tier-beginner"><div class="tier-label" style="color:#3b82f6;">Beginner View</div>{beginner}</div>', unsafe_allow_html=True)
            elif tier_brief == "Intermediate":
                st.markdown(f'<div class="tier-tab tier-intermediate"><div class="tier-label" style="color:#f59e0b;">Intermediate View</div>{intermediate}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="tier-tab tier-pro"><div class="tier-label" style="color:#a855f7;">Pro View</div>{pro}</div>', unsafe_allow_html=True)

            # Pivot levels
            st.markdown(f"""<div class="intel-card" style="margin-top:16px;">
                <h3>Pivot Levels <span class="pill pill-data">FIBONACCI</span></h3>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;text-align:center;">
                    <div><div style="font-size:9px;color:#6b7a99;">R2</div><div style="font-size:13px;color:#ef4444;font-weight:600;">${pivots['R2']:,.0f}</div></div>
                    <div><div style="font-size:9px;color:#6b7a99;">R1</div><div style="font-size:13px;color:#ef4444;font-weight:600;">${pivots['R1']:,.0f}</div></div>
                    <div><div style="font-size:9px;color:#6b7a99;">Pivot</div><div style="font-size:13px;color:#f0b90b;font-weight:700;">${pivots['PP']:,.0f}</div></div>
                    <div><div style="font-size:9px;color:#6b7a99;">S1</div><div style="font-size:13px;color:#10b981;font-weight:600;">${pivots['S1']:,.0f}</div></div>
                    <div><div style="font-size:9px;color:#6b7a99;">S2</div><div style="font-size:13px;color:#10b981;font-weight:600;">${pivots['S2']:,.0f}</div></div>
                    <div><div style="font-size:9px;color:#6b7a99;">S3</div><div style="font-size:13px;color:#10b981;font-weight:600;">${pivots['S3']:,.0f}</div></div>
                </div>
            </div>""", unsafe_allow_html=True)

        with brief_weekly:
            # Weekly brief — use weekly timeframe data
            week_start = (datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())).strftime('%b %d')
            week_end = datetime.utcnow().strftime('%b %d, %Y')

            # Weekly stats from gold_df
            week_mask = gold_df.index >= (pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=7))
            week_df = gold_df[week_mask]
            if len(week_df) >= 2:
                week_open = week_df['Open'].iloc[0]
                week_close = week_df['Close'].iloc[-1]
                week_high = week_df['High'].max()
                week_low = week_df['Low'].min()
                week_chg = week_close - week_open
                week_pct = (week_chg / week_open) * 100
                week_range = week_high - week_low
                week_dir = "up" if week_chg >= 0 else "down"
                week_color = "#10b981" if week_chg >= 0 else "#ef4444"
                week_avg_vol = week_df['Volume'].mean() if 'Volume' in week_df.columns else 0

                # Weekly volume spikes
                week_spikes = [s for s in spikes_correlated if s['date'] >= (datetime.utcnow() - timedelta(days=7)).date()] if spikes_correlated else []

                # Weekly driver summary
                bull_d = sum(1 for d in drivers if d[2] == "BULLISH")
                bear_d = sum(1 for d in drivers if d[2] == "BEARISH")
                week_bias = "BULLISH" if bull_d > bear_d + 1 else "BEARISH" if bear_d > bull_d + 1 else "NEUTRAL"
                wb_color = "#10b981" if week_bias == "BULLISH" else "#ef4444" if week_bias == "BEARISH" else "#f59e0b"
                wb_bg = f"rgba({16 if week_bias=='BULLISH' else 239 if week_bias=='BEARISH' else 245},{185 if week_bias=='BULLISH' else 68 if week_bias=='BEARISH' else 158},{129 if week_bias=='BULLISH' else 68 if week_bias=='BEARISH' else 11},0.12)"

                st.markdown(
                    f'<div class="daily-brief">'
                    f'<div class="daily-brief-header">'
                    f'<div class="daily-brief-title">'
                    f'<span style="font-size:16px;">&#128197;</span> Weekly Brief '
                    f'<span style="font-size:9px;color:#6b7a99;font-weight:400;letter-spacing:0.5px;">'
                    f'{week_start} — {week_end}</span>'
                    f'</div>'
                    f'<span class="brief-bias-badge" style="background:{wb_bg};color:{wb_color};border:1px solid {wb_color}33;">'
                    f'{week_bias}</span>'
                    f'</div>'
                    f'<div class="daily-brief-body">'
                    f'<p>Gold moved <span style="color:{week_color};font-weight:700;">{week_dir} ${abs(week_chg):,.2f} ({week_pct:+.2f}%)</span> this week, '
                    f'trading in a <b>${week_range:,.0f}</b> range from ${week_low:,.0f} to ${week_high:,.0f}.</p>'
                    f'<p style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:12px 0;">'
                    f'<span style="text-align:center;background:rgba(240,185,11,0.06);border-radius:6px;padding:8px;">'
                    f'<span style="font-size:9px;color:#6b7a99;display:block;">Open</span>'
                    f'<span style="font-size:14px;font-weight:700;color:#e2e8f0;">${week_open:,.0f}</span></span>'
                    f'<span style="text-align:center;background:rgba(16,185,129,0.06);border-radius:6px;padding:8px;">'
                    f'<span style="font-size:9px;color:#6b7a99;display:block;">High</span>'
                    f'<span style="font-size:14px;font-weight:700;color:#10b981;">${week_high:,.0f}</span></span>'
                    f'<span style="text-align:center;background:rgba(239,68,68,0.06);border-radius:6px;padding:8px;">'
                    f'<span style="font-size:9px;color:#6b7a99;display:block;">Low</span>'
                    f'<span style="font-size:14px;font-weight:700;color:#ef4444;">${week_low:,.0f}</span></span>'
                    f'<span style="text-align:center;background:rgba(240,185,11,0.06);border-radius:6px;padding:8px;">'
                    f'<span style="font-size:9px;color:#6b7a99;display:block;">Close</span>'
                    f'<span style="font-size:14px;font-weight:700;color:#e2e8f0;">${week_close:,.0f}</span></span>'
                    f'</p>'
                    f'<p>Macro bias is <b style="color:{wb_color};">{week_bias.lower()}</b> ({bull_d} bullish / {bear_d} bearish drivers). '
                    f'{"Volume spikes detected on " + str(len(week_spikes)) + " session(s) — institutional activity likely." if week_spikes else "No significant volume spikes this week."}</p>'
                    f'<p>RSI at <b>{rsi_val:.1f}</b> · ATR <b>${gold_df["ATR_14"].iloc[-1]:,.0f}</b> · '
                    f'Fear & Greed <b style="color:{fear_greed["color"] if fear_greed else "#f59e0b"};">{fear_greed["score"]:.0f}/100</b> ({fear_greed["label"] if fear_greed else "N/A"})</p>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )

                # Weekly volume spikes table
                if week_spikes:
                    st.markdown("""<div class="section-header" style="--section-accent: #a855f7; margin-top: 16px;">
                        <span class="section-title">Volume Spikes This Week</span>
                    </div>""", unsafe_allow_html=True)
                    for s in week_spikes[:5]:
                        s_color = "#10b981" if s['direction'] == 'UP' else "#ef4444"
                        trigger_tag = f" · <span style='color:#a855f7;'>{s.get('trigger', 'volume')}</span>" if s.get('trigger') else ""
                        st.markdown(
                            f'<div style="background:rgba(15,20,40,0.6);border:1px solid rgba(26,34,64,0.5);border-radius:8px;padding:10px 14px;margin-bottom:6px;">'
                            f'<span style="color:#8892ab;font-size:11px;">{s["date"]}</span> · '
                            f'<span style="color:{s_color};font-weight:700;">{s["direction"]}</span> '
                            f'<span style="color:#e2e8f0;">${abs(s["change"]):,.0f} ({s["change_pct"]:.1f}%)</span>'
                            f'{trigger_tag}'
                            f'<span style="float:right;color:#6b7a99;font-size:10px;">{s["vol_ratio"]:.1f}x vol</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
            else:
                st.info("Not enough weekly data available yet.")

        with brief_monthly:
            # Monthly brief — use ~30 days of data
            month_name = datetime.utcnow().strftime('%B %Y')

            month_mask = gold_df.index >= (pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=30))
            month_df = gold_df[month_mask]
            if len(month_df) >= 5:
                month_open = month_df['Open'].iloc[0]
                month_close = month_df['Close'].iloc[-1]
                month_high = month_df['High'].max()
                month_low = month_df['Low'].min()
                month_chg = month_close - month_open
                month_pct = (month_chg / month_open) * 100
                month_range = month_high - month_low
                month_dir = "up" if month_chg >= 0 else "down"
                month_color = "#10b981" if month_chg >= 0 else "#ef4444"

                # Monthly spikes
                month_spikes = [s for s in spikes_correlated if s['date'] >= (datetime.utcnow() - timedelta(days=30)).date()] if spikes_correlated else []

                # COT positioning summary for monthly
                cot_text = ""
                if cot_data and cot_data.get('latest'):
                    lat = cot_data['latest']
                    net_mm = lat.get('net_managed_money', 0)
                    cot_bias = "net long" if net_mm > 0 else "net short"
                    cot_text = f'Managed money is <b>{cot_bias}</b> ({net_mm:+,.0f} contracts). '

                # ETF flows summary
                etf_text = ""
                if etf_flows:
                    for etf in etf_flows:
                        if etf['symbol'] == 'GLD':
                            etf_text = f'GLD flows: <b>{etf["flow_label"]}</b> (${etf["dollar_volume"]/1e6:,.0f}M). '
                            break

                mb_color = month_color
                mb_bg = f"rgba({16 if month_chg >= 0 else 239},{185 if month_chg >= 0 else 68},{129 if month_chg >= 0 else 68},0.12)"
                mb_label = "BULLISH" if month_pct > 2 else "BEARISH" if month_pct < -2 else "NEUTRAL"

                st.markdown(
                    f'<div class="daily-brief">'
                    f'<div class="daily-brief-header">'
                    f'<div class="daily-brief-title">'
                    f'<span style="font-size:16px;">&#128200;</span> Monthly Brief '
                    f'<span style="font-size:9px;color:#6b7a99;font-weight:400;letter-spacing:0.5px;">'
                    f'{month_name}</span>'
                    f'</div>'
                    f'<span class="brief-bias-badge" style="background:{mb_bg};color:{mb_color};border:1px solid {mb_color}33;">'
                    f'{mb_label}</span>'
                    f'</div>'
                    f'<div class="daily-brief-body">'
                    f'<p>Gold has moved <span style="color:{month_color};font-weight:700;">{month_dir} ${abs(month_chg):,.2f} ({month_pct:+.2f}%)</span> over the past 30 days, '
                    f'with a total range of <b>${month_range:,.0f}</b> (${month_low:,.0f} — ${month_high:,.0f}).</p>'
                    f'<p style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:12px 0;">'
                    f'<span style="text-align:center;background:rgba(240,185,11,0.06);border-radius:6px;padding:8px;">'
                    f'<span style="font-size:9px;color:#6b7a99;display:block;">Month Open</span>'
                    f'<span style="font-size:14px;font-weight:700;color:#e2e8f0;">${month_open:,.0f}</span></span>'
                    f'<span style="text-align:center;background:rgba(16,185,129,0.06);border-radius:6px;padding:8px;">'
                    f'<span style="font-size:9px;color:#6b7a99;display:block;">Month High</span>'
                    f'<span style="font-size:14px;font-weight:700;color:#10b981;">${month_high:,.0f}</span></span>'
                    f'<span style="text-align:center;background:rgba(239,68,68,0.06);border-radius:6px;padding:8px;">'
                    f'<span style="font-size:9px;color:#6b7a99;display:block;">Month Low</span>'
                    f'<span style="font-size:14px;font-weight:700;color:#ef4444;">${month_low:,.0f}</span></span>'
                    f'<span style="text-align:center;background:rgba(240,185,11,0.06);border-radius:6px;padding:8px;">'
                    f'<span style="font-size:9px;color:#6b7a99;display:block;">Current</span>'
                    f'<span style="font-size:14px;font-weight:700;color:#e2e8f0;">${month_close:,.0f}</span></span>'
                    f'</p>'
                    f'<p>{cot_text}{etf_text}</p>'
                    f'<p>{len(month_spikes)} volume spike(s) in the past 30 days. '
                    f'Fear & Greed at <b style="color:{fear_greed["color"] if fear_greed else "#f59e0b"};">{fear_greed["score"]:.0f}/100</b> ({fear_greed["label"] if fear_greed else "N/A"}).</p>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )

                # Monthly spikes list
                if month_spikes:
                    st.markdown("""<div class="section-header" style="--section-accent: #a855f7; margin-top: 16px;">
                        <span class="section-title">Volume Spikes (30 Days)</span>
                    </div>""", unsafe_allow_html=True)
                    for s in month_spikes[:10]:
                        s_color = "#10b981" if s['direction'] == 'UP' else "#ef4444"
                        trigger_tag = f" · <span style='color:#a855f7;'>{s.get('trigger', 'volume')}</span>" if s.get('trigger') else ""
                        news_tags = ""
                        if s.get('news'):
                            news_tags = " · ".join([f"<span style='color:#94a3b8;font-size:9px;'>{n['title'][:40]}...</span>" for n in s['news'][:2]])
                            news_tags = f"<div style='margin-top:4px;'>{news_tags}</div>"
                        st.markdown(
                            f'<div style="background:rgba(15,20,40,0.6);border:1px solid rgba(26,34,64,0.5);border-radius:8px;padding:10px 14px;margin-bottom:6px;">'
                            f'<span style="color:#8892ab;font-size:11px;">{s["date"]}</span> · '
                            f'<span style="color:{s_color};font-weight:700;">{s["direction"]}</span> '
                            f'<span style="color:#e2e8f0;">${abs(s["change"]):,.0f} ({s["change_pct"]:.1f}%)</span>'
                            f'{trigger_tag}'
                            f'<span style="float:right;color:#6b7a99;font-size:10px;">{s["vol_ratio"]:.1f}x vol</span>'
                            f'{news_tags}'
                            f'</div>',
                            unsafe_allow_html=True
                        )
            else:
                st.info("Not enough monthly data available yet.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 1 — DASHBOARD
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_dashboard:

        # ── RANGE ANALYSIS ──
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

        # ── MULTI-TIMEFRAME PROBABILITY ──
        tt_mtf = tooltip("Probability", "Directional Probability")
        st.markdown(f"""<div class="section-header" style="--section-accent: #a855f7;">
            <span class="section-title">{tt_mtf}</span>
            <span class="pill pill-model">DAILY / WEEKLY / MONTHLY</span>
        </div>""", unsafe_allow_html=True)

        prob_cols = st.columns(3)
        for pcol, (tf_key, tf_label) in zip(prob_cols, [('daily', 'Daily (1-2D)'), ('weekly', 'Weekly (5D)'), ('monthly', 'Monthly (20D)')]):
            p = mtf_probs[tf_key]
            bull_pct = p['bullish']
            bear_pct = p['bearish']
            bias = p['bias']
            rationale = p['rationale']
            b_color = "#10b981" if bias == "BULLISH" else "#ef4444" if bias == "BEARISH" else "#f59e0b"
            b_bg = f"rgba({16 if bias == 'BULLISH' else 239 if bias == 'BEARISH' else 245},{185 if bias == 'BULLISH' else 68 if bias == 'BEARISH' else 158},{129 if bias == 'BULLISH' else 68 if bias == 'BEARISH' else 11},0.12)"
            with pcol:
                st.markdown(f"""<div class="intel-card" style="padding:14px 16px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                        <span style="font-size:11px;font-weight:700;color:#a8b2c8;text-transform:uppercase;letter-spacing:0.5px;">{tf_label}</span>
                        <span style="font-size:9px;font-weight:800;padding:3px 10px;border-radius:4px;background:{b_bg};color:{b_color};">{bias}</span>
                    </div>
                    <div class="prob-row">
                        <span class="prob-label" style="color:#10b981;">Bull</span>
                        <div class="prob-track"><div class="prob-fill" style="width:{bull_pct}%;background:linear-gradient(90deg,#10b981,#059669);"></div></div>
                        <span class="prob-val" style="color:#10b981;">{bull_pct}%</span>
                    </div>
                    <div class="prob-row">
                        <span class="prob-label" style="color:#ef4444;">Bear</span>
                        <div class="prob-track"><div class="prob-fill" style="width:{bear_pct}%;background:linear-gradient(90deg,#ef4444,#dc2626);"></div></div>
                        <span class="prob-val" style="color:#ef4444;">{bear_pct}%</span>
                    </div>
                    <div style="font-size:10px;color:#6b7a99;margin-top:6px;font-style:italic;">{rationale}</div>
                </div>""", unsafe_allow_html=True)

        # ── DAILY KEY LEVELS — The Game Plan ──
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

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 2 — TRADE SIGNALS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_signals:

        # ── SIGNAL ENGINE ──
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
                    tt_rr = tooltip("Risk/Reward", "Risk:Reward")
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
                            <div class="signal-level-label">{tt_rr}</div>
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
                        <div style="font-size:10px;color:#6b7a99;margin-top:4px;">{time_str} · {signal['timeframe']} · {signal.get('session', '')} · {signal['pattern_name']}</div>
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

        # ── ICMarkets contextual CTA (post-signals) ──
        st.markdown("""<a href="https://icmarkets.com/?camp=87951" target="_blank" style="text-decoration:none;display:block;">
            <div style="background:linear-gradient(135deg,rgba(37,99,235,0.06),rgba(37,99,235,0.02));
                border:1px solid rgba(59,130,246,0.12);border-radius:8px;padding:10px 16px;
                display:flex;align-items:center;justify-content:space-between;margin:12px 0 16px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:16px;">⚡</span>
                    <div>
                        <div style="font-size:10px;font-weight:700;color:#60a5fa;">Ready to trade these signals?</div>
                        <div style="font-size:9px;color:#6b7a99;">Execute XAU/USD trades with raw spreads from 0.0 pips on ICMarkets</div>
                    </div>
                </div>
                <div style="background:linear-gradient(135deg,#2563eb,#1d4ed8);color:#fff;
                    font-size:9px;font-weight:700;padding:6px 14px;border-radius:5px;white-space:nowrap;">
                    Open Account →
                </div>
            </div>
        </a>""", unsafe_allow_html=True)

        # ── FULL-WIDTH TRADINGVIEW CHART ──
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

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 3 — INTELLIGENCE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_intel:

        col_drivers, col_data = st.columns([1, 1])

        with col_drivers:
            # ── MACRO DRIVERS ──
            tt_macro = tooltip("Macro Drivers")
            st.markdown(f"""<div class="intel-card"><h3 style="margin-bottom:14px;">{tt_macro}
                <span class="pill pill-data">AUTO-COMPUTED</span></h3>""", unsafe_allow_html=True)
            # Map driver names to glossary terms for tooltips
            _driver_tt_map = {"USD (DXY)": "DXY", "US 10Y Yield": "Yield", "VIX (Fear Index)": "VIX",
                              "Gold Trend (SMA 20/50)": "SMA", "S&P 500": None, "Crude Oil": None}
            for d in drivers:
                name, detail, impact, why = d[0], d[1], d[2], d[3]
                tag_class = "tag-bull" if impact == "BULLISH" else "tag-bear" if impact == "BEARISH" else "tag-mixed"
                why_html = f'<br><small style="color:#8892ab;font-style:italic;">{why}</small>' if why else ''
                icon_html = get_instrument_icon(name)
                tt_key = _driver_tt_map.get(name)
                name_html = tooltip(tt_key, name) if tt_key else name
                st.markdown(f"""<div class="driver-row">
                    <span>{icon_html} {name_html}<br><small style="color:#6b7a99">{detail}</small>{why_html}</span>
                    <span class="{tag_class}">{impact}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # ── CORRELATIONS (multi-window) ──
            tt_corr = tooltip("Correlation", "Correlations")
            st.markdown(f"""<div class="intel-card"><h3>{tt_corr}
                <span class="pill pill-model">COMPUTED</span></h3>""", unsafe_allow_html=True)
            corr_window = st.radio("Window", ["7D", "30D", "90D"], index=1, horizontal=True, key="corr_window", label_visibility="collapsed")
            active_corr = multi_corr.get(corr_window, correlations)
            for name, val in active_corr.items():
                color = "#10b981" if val > 0.3 else "#ef4444" if val < -0.3 else "#6b7a99"
                bg = "rgba(16,185,129,0.12)" if val > 0.3 else "rgba(239,68,68,0.12)" if val < -0.3 else "rgba(107,122,153,0.08)"
                corr_icon = get_instrument_icon(name)
                # Interpretation label
                if val > 0.6:
                    interp = "strong +"
                elif val > 0.3:
                    interp = "moderate +"
                elif val < -0.6:
                    interp = "strong −"
                elif val < -0.3:
                    interp = "moderate −"
                else:
                    interp = "weak"
                st.markdown(f"""<div style="display:flex;justify-content:space-between;padding:5px 0;font-size:12px;align-items:center;border-bottom:1px solid rgba(26,34,64,0.3);">
                    <span style="display:flex;align-items:center;gap:4px;">{corr_icon} {name}</span>
                    <span style="display:flex;align-items:center;gap:6px;">
                        <span style="font-size:9px;color:#5a6a8a;">{interp}</span>
                        <span class="corr-cell" style="background:{bg};color:{color};padding:3px 10px;border-radius:4px;min-width:55px;text-align:center;font-family:JetBrains Mono;font-weight:600;">{val:+.2f}</span>
                    </span>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_data:
            # ── KEY LEVELS ──
            tt_pivot = tooltip("Pivot", "Key Levels")
            st.markdown(f"""<div class="intel-card"><h3>{tt_pivot}
                <span class="pill pill-data">PIVOT + S/R</span></h3>""", unsafe_allow_html=True)
            pcol1, pcol2 = st.columns(2)
            with pcol1:
                tt_sup = tooltip("Support")
                st.markdown(f"<b style='color:#10b981;font-size:11px;'>{tt_sup}</b>", unsafe_allow_html=True)
                for label, val in [("Pivot S1", pivots['S1']), ("Pivot S2", pivots['S2']), ("Pivot S3", pivots['S3'])]:
                    st.markdown(f'<div class="level-row"><span style="color:#10b981;font-family:JetBrains Mono">${val:,.0f}</span><span style="font-size:9px;color:#6b7a99">{label}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="level-row"><span style="color:#10b981;font-family:JetBrains Mono">${gold_df["SMA_20"].iloc[-1]:,.0f}</span><span style="font-size:9px;color:#6b7a99">SMA 20</span></div>', unsafe_allow_html=True)
            with pcol2:
                tt_res = tooltip("Resistance")
                st.markdown(f"<b style='color:#ef4444;font-size:11px;'>{tt_res}</b>", unsafe_allow_html=True)
                for label, val in [("Pivot R1", pivots['R1']), ("Pivot R2", pivots['R2']), ("Pivot R3", pivots['R3'])]:
                    st.markdown(f'<div class="level-row"><span style="color:#ef4444;font-family:JetBrains Mono">${val:,.0f}</span><span style="font-size:9px;color:#6b7a99">{label}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="level-row"><span style="color:#ef4444;font-family:JetBrains Mono">${gold_df["BB_upper"].iloc[-1]:,.0f}</span><span style="font-size:9px;color:#6b7a99">BB Upper</span></div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # ── PROBABILITY ──
            tt_prob = tooltip("Probability", "30-Day Targets")
            st.markdown(f"""<div class="intel-card"><h3>{tt_prob}
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

        # ── NEW: FULL-WIDTH ROW — Fear & Greed | COT | ETF Flows ──
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown("""<div class="section-header" style="--section-accent: #f0b90b;">
            <span class="section-title">Market Intelligence</span>
            <span class="pill pill-data">NEW</span>
        </div>""", unsafe_allow_html=True)

        intel_col1, intel_col2, intel_col3 = st.columns(3)

        with intel_col1:
            # ── FEAR & GREED INDEX ──
            fg_html = render_fear_greed_html(fear_greed)
            if fg_html:
                st.markdown(fg_html, unsafe_allow_html=True)

        with intel_col2:
            # ── COT POSITIONING ──
            cot_html = render_cot_html(cot_data)
            st.markdown(cot_html, unsafe_allow_html=True)

        with intel_col3:
            # ── ETF FLOWS ──
            etf_html = render_etf_flows_html(etf_flows)
            st.markdown(etf_html, unsafe_allow_html=True)

        # ── SECOND ROW: Gold/Silver Ratio | Candlestick Patterns ──
        ratio_col, pattern_col = st.columns(2)

        with ratio_col:
            # ── GOLD/SILVER RATIO ──
            if gs_ratio:
                # Mini sparkline bars for ratio history
                hist = gs_ratio['history']
                max_r = max(hist) if hist else 1
                min_r = min(hist) if hist else 0
                r_range = max_r - min_r if max_r != min_r else 1
                spark_bars = ""
                for v in hist:
                    h = max(4, ((v - min_r) / r_range) * 28)
                    c = "#f0b90b" if v == hist[-1] else "#3d4b6b"
                    spark_bars += f'<div style="width:6px;height:{h:.0f}px;background:{c};border-radius:2px;"></div>'

                st.markdown(f"""<div class="intel-card">
                    <h3 style="display:flex;justify-content:space-between;align-items:center;">
                        <span>Gold/Silver Ratio</span>
                        <span style="font-size:10px;font-weight:700;color:{gs_ratio['interp_color']};">INTERMARKET</span>
                    </h3>
                    <div style="display:flex;align-items:flex-end;gap:16px;margin:8px 0;">
                        <div>
                            <div class="ratio-value">{gs_ratio['current']:.1f}</div>
                            <div class="ratio-compare">20D avg: {gs_ratio['avg_20d']:.1f} &nbsp;·&nbsp; 50D avg: {gs_ratio['avg_50d']:.1f}</div>
                        </div>
                        <div style="display:flex;align-items:flex-end;gap:2px;height:32px;margin-left:auto;">
                            {spark_bars}
                        </div>
                    </div>
                    <div style="font-size:11px;color:{gs_ratio['interp_color']};margin-top:6px;padding-top:6px;border-top:1px solid #1e2745;">
                        {gs_ratio['interp']}
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:10px;color:#5a6a8a;margin-top:4px;">
                        <span>Period Low: {gs_ratio['low']:.1f}</span>
                        <span>Period High: {gs_ratio['high']:.1f}</span>
                    </div>
                </div>""", unsafe_allow_html=True)

        with pattern_col:
            # ── CANDLESTICK PATTERNS ──
            st.markdown(f"""<div class="intel-card">
                <h3 style="display:flex;justify-content:space-between;align-items:center;">
                    <span>Candlestick Patterns</span>
                    <span style="font-size:10px;font-weight:700;color:#a855f7;">LAST 3 SESSIONS</span>
                </h3>
                {render_patterns_html(candle_patterns)}
            </div>""", unsafe_allow_html=True)

        # ── THIRD ROW: Multi-TF RSI Heatmap | Multi-TF Fibonacci ──
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown("""<div class="section-header" style="--section-accent: #a855f7;">
            <span class="section-title">Multi-Timeframe Analysis</span>
            <span class="pill pill-model">RSI + FIBONACCI</span>
        </div>""", unsafe_allow_html=True)

        rsi_col, fib_col = st.columns(2)

        with rsi_col:
            st.markdown(render_mtf_rsi_html(mtf_rsi), unsafe_allow_html=True)

        with fib_col:
            st.markdown(render_mtf_fib_html(mtf_fib), unsafe_allow_html=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 4 — NEWS & EVENTS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_news:

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # ── TradingView Alerts Section ──
        tv_alerts = load_webhook_alerts()
        if tv_alerts:
            st.markdown("""<div class="section-header" style="--section-accent: #f0b90b;">
                <div>
                    <span class="section-title">⚡ TradingView Alerts</span>
                    <div style="font-size:9px;color:#5a6a8a;margin-top:4px;">Real-time price and indicator alerts from TradingView</div>
                </div>
                <span class="pill pill-data">WEBHOOK</span>
            </div>""", unsafe_allow_html=True)

            for alert in tv_alerts:
                alert_time = alert.get('time', '')
                alert_ticker = alert.get('ticker', 'UNKNOWN')
                alert_message = alert.get('message', '')
                alert_type = alert.get('type', 'custom')

                # Format time
                try:
                    from datetime import datetime as dt_parse
                    parsed_time = dt_parse.fromisoformat(alert_time.replace('Z', '+00:00'))
                    time_str = parsed_time.strftime('%b %d, %H:%M')
                except:
                    time_str = alert_time[:16]

                st.markdown(f"""<div class="tv-alert-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
                        <div style="flex:1;">
                            <div class="tv-alert-msg">{alert_ticker}: {html_escape(alert_message[:80])}</div>
                            <div class="tv-alert-time">{time_str}</div>
                        </div>
                        <div class="tv-alert-type">{alert_type.replace('_', ' ').upper()}</div>
                    </div>
                </div>""", unsafe_allow_html=True)

            st.markdown('<div style="font-size:9px;color:#5a6a99;background:rgba(240,185,11,0.05);border-radius:6px;padding:10px 12px;margin-top:10px;">'
                        '<b style="color:#f0b90b;">💡 How to connect:</b> Set your TradingView webhook to POST to your deployment endpoint. '
                        'Save JSON alerts in a <code>tv_alerts.json</code> file in the repo root.</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown("""<div class="section-header" style="--section-accent: #a855f7;">
            <div>
                <span class="section-title">Volume Spike Detector</span>
                <div style="font-size:9px;color:#5a6a8a;margin-top:4px;">High-volume candles matched to news, economic events &amp; correlated asset moves</div>
            </div>
            <span class="pill pill-model">MULTI-SOURCE</span>
        </div>""", unsafe_allow_html=True)

        # ── Helper to render a single spike card ──
        def render_spike_card(spike):
            dir_arrow = "▲" if spike['direction'] == 'UP' else "▼"
            dir_color = "#10b981" if spike['direction'] == 'UP' else "#ef4444"

            # Build structured WHY section with labeled lines
            why_lines = []
            econ_evts = spike.get('econ_events', [])
            asset_moves = spike.get('asset_moves', {})

            # Event line with prominence
            if econ_evts:
                top_evt = econ_evts[0]
                event_label = top_evt['impact']  # HIGH, MEDIUM, LOW
                why_lines.append(f"<div><span style='color:#f0b90b;font-weight:700;'>EVENT:</span> {event_label} impact event</div>")

            # Correlated movers line
            if asset_moves:
                big_movers = [(k, v) for k, v in asset_moves.items() if abs(v['change_pct']) > 0.5]
                big_movers.sort(key=lambda x: abs(x[1]['change_pct']), reverse=True)
                if big_movers:
                    mover_text = ", ".join([f"{k} {'+' if v['change_pct'] > 0 else '-'}{abs(v['change_pct']):.1f}%" for k, v in big_movers[:2]])
                    why_lines.append(f"<div><span style='color:#a8b2c8;font-weight:700;'>MOVERS:</span> {mover_text}</div>")

            # Trading session context
            hour = spike['date'].hour if hasattr(spike['date'], 'hour') else 12
            if 13 <= hour <= 22:
                session_context = "US Session"
            elif 8 <= hour <= 16:
                session_context = "London Session"
            elif 0 <= hour <= 8:
                session_context = "Asia Session"
            else:
                session_context = "Mixed Session"
            why_lines.append(f"<div><span style='color:#6b7a99;font-weight:700;'>TIME:</span> {session_context}</div>")

            # Fallback if no structured data
            if not why_lines or len(why_lines) == 1:
                why_lines.append(f"<div><span style='color:#a8b2c8;font-weight:700;'>CATALYST:</span> Institutional flow or expiry</div>")

            why_html = "".join(why_lines)

            # Asset moves chips
            moves_chips = ""
            if asset_moves:
                for a_name, mv in list(asset_moves.items())[:4]:
                    mv_color = "#10b981" if mv['change_pct'] >= 0 else "#ef4444"
                    mv_arrow = "▲" if mv['change_pct'] >= 0 else "▼"
                    moves_chips += (f'<span style="font-size:9px;padding:2px 6px;border-radius:3px;'
                                    f'background:{mv_color}12;color:{mv_color};font-weight:600;margin-right:4px;">'
                                    f'{a_name} {mv_arrow}{abs(mv["change_pct"]):.1f}%</span>')

            st.markdown(f"""<div class="spike-card" style="border-left:3px solid {dir_color};">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                        <div style="font-size:13px;font-weight:800;color:#e8ecf4;">{spike['date']}</div>
                        <div style="font-size:10px;color:#a8b2c8;margin-top:2px;font-family:JetBrains Mono;">
                            O: ${spike['open']:,.2f} &nbsp; H: ${spike['high']:,.2f} &nbsp; L: ${spike['low']:,.2f} &nbsp; C: ${spike['close']:,.2f}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:12px;font-weight:800;color:{dir_color};font-family:JetBrains Mono;">
                            {dir_arrow} ${abs(spike['change']):,.2f} ({spike['change_pct']:+.2f}%)
                        </div>
                        <div style="font-size:10px;color:#f0b90b;font-weight:700;margin-top:2px;">{spike['vol_ratio']:.1f}x Avg Volume</div>
                    </div>
                </div>
                <div style="margin-top:10px;font-size:10px;color:#a8b2c8;line-height:1.8;display:flex;flex-direction:column;gap:4px;">
                    <span style="color:#f59e0b;font-weight:700;font-size:9px;text-transform:uppercase;letter-spacing:0.5px;">WHY:</span>
                    {why_html}
                </div>
                <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:4px;">{moves_chips}</div>
            </div>""", unsafe_allow_html=True)

        # ── Split spikes into Daily / Weekly / Monthly ──
        if spikes_correlated:
            from datetime import timedelta as _td
            today = datetime.utcnow().date()
            daily_spikes = [s for s in spikes_correlated if (today - s['date']).days <= 1]
            weekly_spikes = [s for s in spikes_correlated if 1 < (today - s['date']).days <= 7]
            monthly_spikes = [s for s in spikes_correlated if 7 < (today - s['date']).days <= 30]

            vs_daily, vs_weekly, vs_monthly = st.tabs(["Daily", "This Week", "This Month"])
            with vs_daily:
                if daily_spikes:
                    for spike in daily_spikes[:5]:
                        render_spike_card(spike)
                else:
                    st.markdown('<div style="color:#5a6a8a;font-size:11px;padding:12px;">No volume spikes today.</div>', unsafe_allow_html=True)
            with vs_weekly:
                if weekly_spikes:
                    for spike in weekly_spikes[:10]:
                        render_spike_card(spike)
                else:
                    st.markdown('<div style="color:#5a6a8a;font-size:11px;padding:12px;">No volume spikes this week.</div>', unsafe_allow_html=True)
            with vs_monthly:
                if monthly_spikes:
                    for spike in monthly_spikes[:10]:
                        render_spike_card(spike)
                else:
                    st.markdown('<div style="color:#5a6a8a;font-size:11px;padding:12px;">No volume spikes this month.</div>', unsafe_allow_html=True)
        else:
            st.info("No significant volume spikes detected in recent data.")

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # ── NEWS SENTIMENT GAUGE (above news feed) ──
        if news_sentiment:
            st.markdown(render_sentiment_html(news_sentiment), unsafe_allow_html=True)

        news_col, cal_col = st.columns([1, 1])

        with news_col:
            st.markdown("""<div class="section-header" style="--section-accent: #ef4444;">
                <span class="section-title">Live News Feed</span>
                <span class="pill pill-live">VERIFIED SOURCES · RSS</span>
            </div>""", unsafe_allow_html=True)
            if news:
                # Impact classification rules
                HIGH_IMPACT_KW = ['war', 'attack', 'strike', 'nuclear', 'bomb', 'missile', 'invasion',
                                  'sanctions', 'fomc', 'rate cut', 'rate hike', 'fed decision', 'powell',
                                  'breaking', 'crisis', 'emergency', 'ceasefire', 'escalat']
                MEDIUM_IMPACT_KW = ['gold price', 'xau', 'bullion', 'dollar', 'dxy', 'inflation', 'cpi',
                                    'treasury', 'yield', 'oil', 'crude', 'opec', 'tariff', 'trade war',
                                    'central bank', 'reserve', 'gdp', 'jobs', 'nfp', 'unemployment']

                # Classify each article
                high_news, medium_news, low_news = [], [], []
                for article in news[:30]:
                    title_lower = article['title'].lower()
                    if any(kw in title_lower for kw in HIGH_IMPACT_KW):
                        article['_impact'] = 'HIGH'
                        high_news.append(article)
                    elif any(kw in title_lower for kw in MEDIUM_IMPACT_KW):
                        article['_impact'] = 'MEDIUM'
                        medium_news.append(article)
                    else:
                        article['_impact'] = 'LOW'
                        low_news.append(article)

                # Category detection — no assumption-based gold impact
                _cat_rules = [
                    ('Geopolitical', ['war', 'attack', 'strike', 'nuclear', 'bomb', 'missile', 'invasion', 'crisis', 'sanctions', 'conflict'], None, '#ef4444'),
                    ('Fed / Rates', ['fed', 'fomc', 'powell', 'rate cut', 'rate hike', 'interest rate', 'federal reserve'], None, '#3b82f6'),
                    ('Inflation', ['inflation', 'cpi', 'pce', 'consumer price'], None, '#f59e0b'),
                    ('USD / DXY', ['dollar', 'usd', 'dxy'], None, '#10b981'),
                    ('Oil / Energy', ['oil', 'crude', 'opec', 'brent', 'wti'], None, '#8b5cf6'),
                    ('Bonds / Yields', ['bond', 'yield', 'treasury', '10-year', '10y'], None, '#3b82f6'),
                    ('Gold', ['gold', 'xau', 'bullion', 'precious metal', 'safe haven', 'gold reserve'], None, '#f0b90b'),
                    ('Tariffs / Trade', ['tariff', 'trade war', 'trade deal'], None, '#f59e0b'),
                ]

                def render_news_article(article):
                    date_str = article['published'].strftime('%b %d, %H:%M') if article['published'] else ""
                    source = f" — {article['source']}" if article['source'] else ""
                    title_lower = article['title'].lower()
                    is_breaking = any(kw in title_lower for kw in ['war', 'attack', 'strike', 'nuclear', 'missile', 'crisis'])

                    # Build chips: one per matched category only
                    matched_cats = []
                    for cat_name, keywords, _, cat_color in _cat_rules:
                        if any(kw in title_lower for kw in keywords):
                            matched_cats.append((cat_name, cat_color))

                    # Build category chip(s) — max 2 to avoid clutter
                    impact_chips = ""
                    for cat_name, cat_color in matched_cats[:2]:
                        impact_chips += (f'<span style="font-size:9px;padding:2px 6px;border-radius:3px;'
                                         f'background:{cat_color}15;color:{cat_color};font-weight:700;">'
                                         f'{cat_name}</span> ')

                    breaking_class = ' rss-breaking' if is_breaking else ''
                    prefix = '<span style="color:#ef4444;font-weight:700;font-size:10px;">&#9889; BREAKING </span>' if is_breaking else ''
                    safe_link = article['link'] if article['link'].startswith(('http://', 'https://')) else '#'
                    st.markdown(f"""<div class="rss-item{breaking_class}">
                        <div class="rss-title">
                            {prefix}<a href="{safe_link}" target="_blank" rel="noopener noreferrer">{article['title']}</a>
                            <div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:4px;">{impact_chips}</div>
                            <div style="font-size:9px;color:#6b7a99;margin-top:2px;">{date_str}{source}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)

                # Render in High / Medium / Low tabs
                nf_high, nf_medium, nf_low = st.tabs([
                    f"High Impact ({len(high_news)})",
                    f"Medium Impact ({len(medium_news)})",
                    f"Low Impact ({len(low_news)})"
                ])
                with nf_high:
                    if high_news:
                        for article in high_news[:10]:
                            render_news_article(article)
                    else:
                        st.markdown('<div style="color:#5a6a8a;font-size:11px;padding:12px;">No high-impact news right now.</div>', unsafe_allow_html=True)
                with nf_medium:
                    if medium_news:
                        for article in medium_news[:10]:
                            render_news_article(article)
                    else:
                        st.markdown('<div style="color:#5a6a8a;font-size:11px;padding:12px;">No medium-impact news right now.</div>', unsafe_allow_html=True)
                with nf_low:
                    if low_news:
                        for article in low_news[:10]:
                            render_news_article(article)
                    else:
                        st.markdown('<div style="color:#5a6a8a;font-size:11px;padding:12px;">No low-impact news right now.</div>', unsafe_allow_html=True)
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
                arrow = "▲" if chg >= 0 else "▼"
                ci_icon = get_instrument_icon(name)
                st.markdown(f"""<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #1e2745;font-size:12px;align-items:center;">
                    <span style="display:flex;align-items:center;gap:4px;color:#a8b2c8">{ci_icon} {name}</span>
                    <span style="display:flex;align-items:center;gap:8px;">
                        <span style="font-family:JetBrains Mono;color:#e8ecf4;font-weight:600;">{cur:,.2f}</span>
                        <span style="font-family:JetBrains Mono;color:{color};font-weight:600;min-width:60px;text-align:right;">{arrow} {chg:+.2f}%</span>
                    </span>
                </div>""", unsafe_allow_html=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 5 — SMC ENGINE (Placeholder)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_smc:
        st.markdown("""<div class="intel-card" style="padding:30px;text-align:center;">
            <div style="font-size:32px;margin-bottom:12px;">🔲</div>
            <h3 style="color:#f0b90b;margin-bottom:8px;">Smart Money Concepts Engine</h3>
            <p style="color:#8892ab;font-size:13px;line-height:1.6;">
                Order Blocks · Liquidity Sweeps · Break of Structure · Fair Value Gaps<br>
                Multi-timeframe cascade: Daily → 4H → 1H → 15m → 5m<br><br>
                <span style="color:#f59e0b;font-weight:600;">Coming Soon</span> — This module will detect institutional order flow patterns
                across timeframes and integrate with the signal engine for higher-conviction entries.
            </p>
        </div>""", unsafe_allow_html=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 6 — BACKTEST ENGINE (Placeholder)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_backtest:
        st.markdown("""<div class="intel-card" style="padding:30px;text-align:center;">
            <div style="font-size:32px;margin-bottom:12px;">📈</div>
            <h3 style="color:#f0b90b;margin-bottom:8px;">Signal Backtesting Engine</h3>
            <p style="color:#8892ab;font-size:13px;line-height:1.6;">
                Win Rate · Average R:R · Max Drawdown · Profit Factor<br>
                Per-pattern breakdown · Session performance · Equity curve<br><br>
                <span style="color:#f59e0b;font-weight:600;">Coming Soon</span> — This module will backtest all signal engine patterns
                against 3-6 months of historical data and show which setups actually perform.
            </p>
        </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # FOOTER (outside all tabs, at main() level)
    # ══════════════════════════════════════════════════
    st.markdown(f"""<div class="section-divider"></div>
    <div style="text-align:center;padding:20px 0;">
        <div style="font-size:12px;font-weight:900;color:#f0b90b;letter-spacing:3px;margin-bottom:6px;">GOLD COMMAND</div>
        <div style="font-size:10px;color:#8a94a8;margin-bottom:6px;">XAU/USD Market Intelligence Terminal&nbsp;&nbsp;·&nbsp;&nbsp;v2.0</div>
        <div style="font-size:9px;color:#5a6a8a;margin-bottom:8px;">by <span style="color:#f0b90b;font-weight:600;">Capt. Gold</span></div>
        <div style="display:flex;justify-content:center;gap:16px;margin-bottom:10px;">
            <a href="https://t.me/capt_gold" target="_blank"
               style="font-size:9px;color:#3b82f6;text-decoration:none;font-weight:600;">
                ✈ Telegram
            </a>
            <a href="https://icmarkets.com/?camp=87951" target="_blank"
               style="font-size:9px;color:#60a5fa;text-decoration:none;font-weight:600;">
                Trade on ICMarkets →
            </a>
        </div>
        <div style="display:flex;justify-content:center;gap:20px;margin-bottom:8px;">
            <span style="font-size:8px;color:#3d4b6b;">📊 6 Intelligence Modules</span>
            <span style="font-size:8px;color:#3d4b6b;">🎯 Multi-TF Signal Engine</span>
            <span style="font-size:8px;color:#3d4b6b;">🧠 Auto-Computed Macro Analysis</span>
            <span style="font-size:8px;color:#3d4b6b;">📰 Live RSS News Feed</span>
        </div>
        <div style="font-size:8px;color:#3d4b6b;letter-spacing:0.5px;">
            Data: Yahoo Finance, Google News RSS, CFTC COT, ForexFactory&nbsp;&nbsp;|&nbsp;&nbsp;Charts: TradingView&nbsp;&nbsp;|&nbsp;&nbsp;Signals: Proprietary Engine<br>
            <span style="color:#f59e0b;">⚠️ This is not financial advice.</span> All data is delayed and for informational purposes only.
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
