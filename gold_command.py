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
    margin-bottom: 14px;
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
/* ─── Brief Block Grid ─── */
.brief-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 14px;
}
.brief-block {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 8px;
    padding: 12px 14px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
}
.brief-block-icon {
    font-size: 20px;
    line-height: 1;
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
}
.brief-block-content {
    flex: 1;
}
.brief-block-label {
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #5a6a8a;
    margin-bottom: 3px;
}
.brief-block-value {
    font-size: 13px;
    font-weight: 600;
    color: #e0e6f0;
    line-height: 1.4;
}
.brief-block-value .up { color: #10b981; }
.brief-block-value .down { color: #ef4444; }
.brief-block-value .gold { color: #f0b90b; }
.brief-block-value .neutral { color: #f59e0b; }
.brief-block-value .muted { color: #6b7a99; font-size: 11px; font-weight: 400; }
/* ─── Price hero row ─── */
.brief-price-row {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 6px;
}
.brief-price-main {
    font-size: 28px;
    font-weight: 900;
    color: #f0b90b;
    font-family: 'JetBrains Mono', monospace !important;
    letter-spacing: -0.5px;
}
.brief-price-change {
    font-size: 14px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 6px;
}
.brief-trend-line {
    font-size: 11px;
    color: #8892ab;
    margin-bottom: 14px;
}
.brief-trend-line b { color: #c8d0e4 !important; }
@media (max-width: 768px) {
    .daily-brief { padding: 14px 16px; }
    .brief-grid { grid-template-columns: 1fr; }
    .brief-price-main { font-size: 22px; }
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


@st.cache_data(ttl=1800)
def fetch_economic_calendar():
    """Fetch upcoming and recent economic events that impact gold from Google News RSS.
    Returns list of dicts: [{date, title, impact, instruments}]"""
    # Key economic terms that move gold
    cal_feeds = [
        "https://news.google.com/rss/search?q=NFP+jobs+report+OR+non+farm+payrolls&hl=en-US&gl=US&ceid=US:en&when=7d",
        "https://news.google.com/rss/search?q=CPI+inflation+data+OR+consumer+price+index&hl=en-US&gl=US&ceid=US:en&when=7d",
        "https://news.google.com/rss/search?q=FOMC+decision+OR+Fed+rate+decision+OR+Fed+minutes&hl=en-US&gl=US&ceid=US:en&when=7d",
        "https://news.google.com/rss/search?q=PMI+manufacturing+OR+ISM+services&hl=en-US&gl=US&ceid=US:en&when=7d",
        "https://news.google.com/rss/search?q=jobless+claims+OR+unemployment+rate&hl=en-US&gl=US&ceid=US:en&when=7d",
        "https://news.google.com/rss/search?q=GDP+data+OR+retail+sales+data&hl=en-US&gl=US&ceid=US:en&when=7d",
        "https://news.google.com/rss/search?q=PCE+inflation+OR+core+PCE&hl=en-US&gl=US&ceid=US:en&when=7d",
    ]

    # Impact classification rules
    _high_impact = ['nfp', 'non-farm', 'non farm', 'fomc', 'rate decision', 'cpi', 'inflation data',
                    'pce', 'core pce', 'gdp', 'powell', 'fed chair']
    _med_impact = ['pmi', 'ism', 'jobless claims', 'unemployment', 'retail sales', 'fed minutes',
                   'consumer confidence', 'housing', 'durable goods']
    _instrument_map = {
        'XAU': ['gold', 'safe haven', 'bullion'],
        'USD': ['dollar', 'dxy', 'fed', 'fomc', 'rate', 'inflation', 'cpi', 'pce', 'nfp', 'jobs',
                'gdp', 'retail', 'claims', 'payroll', 'employment', 'unemployment', 'powell'],
        'BOND': ['yield', 'treasury', 'bond', '10-year', '10y'],
        'SPX': ['stocks', 'equity', 's&p', 'nasdaq', 'wall street'],
    }

    events = []
    seen_titles = set()
    for feed_url in cal_feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                title = entry.get('title', '')
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                title_lower = title.lower()

                # Parse date
                pub_date = None
                for date_field in ['published_parsed', 'updated_parsed']:
                    parsed = entry.get(date_field)
                    if parsed:
                        try:
                            pub_date = datetime(*parsed[:6]).date()
                        except Exception:
                            pass
                        break
                if not pub_date:
                    continue

                # Classify impact
                impact = "LOW"
                if any(kw in title_lower for kw in _high_impact):
                    impact = "HIGH"
                elif any(kw in title_lower for kw in _med_impact):
                    impact = "MEDIUM"

                # Detect affected instruments
                instruments = []
                for instr, keywords in _instrument_map.items():
                    if any(kw in title_lower for kw in keywords):
                        instruments.append(instr)
                if not instruments:
                    instruments = ['USD']  # Default for econ data

                events.append({
                    'date': pub_date,
                    'title': title,
                    'impact': impact,
                    'instruments': instruments,
                })
        except Exception as e:
            logger.warning(f"Economic calendar fetch failed: {e}")

    # Deduplicate by date + similar title
    events.sort(key=lambda x: (x['date'], x['impact'] != 'HIGH'), reverse=False)
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


def generate_daily_brief_text(current, daily_chg, daily_pct, rsi, atr, drivers, trade_signals, signal_trend, ranges, pivots, key_levels):
    """Generate a structured daily brief with visual blocks for the dashboard."""
    # Direction
    is_up = daily_chg >= 0
    chg_color = "#10b981" if is_up else "#ef4444"
    chg_bg = "rgba(16,185,129,0.1)" if is_up else "rgba(239,68,68,0.1)"
    arrow = "▲" if is_up else "▼"

    # Session bias from drivers
    bull_count = sum(1 for d in drivers if d[2] == "BULLISH")
    bear_count = sum(1 for d in drivers if d[2] == "BEARISH")
    if bull_count > bear_count + 1:
        bias = "BULLISH"
        bias_color = "#10b981"
        bias_bg = "rgba(16,185,129,0.12)"
        trend_word = "bullish"
    elif bear_count > bull_count + 1:
        bias = "BEARISH"
        bias_color = "#ef4444"
        bias_bg = "rgba(239,68,68,0.12)"
        trend_word = "bearish"
    else:
        bias = "NEUTRAL"
        bias_color = "#f59e0b"
        bias_bg = "rgba(245,158,11,0.12)"
        trend_word = "mixed"

    # Key drivers
    key_drivers_parts = []
    for d in drivers:
        name, detail, impact = d[0], d[1], d[2]
        if impact != "NEUTRAL":
            d_icon = "🟢" if impact == "BULLISH" else "🔴"
            key_drivers_parts.append(f'{d_icon} {name} <span class="muted">({detail})</span>')
    drivers_html = " &nbsp;·&nbsp; ".join(key_drivers_parts[:4]) if key_drivers_parts else '<span class="muted">No strong macro catalysts</span>'

    # RSI block
    if rsi < 30:
        rsi_label, rsi_color, rsi_icon = "OVERSOLD", "#ef4444", "🔻"
        rsi_note = "Bounce potential — watch for reversal patterns"
    elif rsi > 70:
        rsi_label, rsi_color, rsi_icon = "OVERBOUGHT", "#10b981", "🔺"
        rsi_note = "Pullback risk — momentum stretched"
    elif rsi < 40:
        rsi_label, rsi_color, rsi_icon = "WEAK", "#f59e0b", "📉"
        rsi_note = "Below neutral — bears in control"
    elif rsi > 60:
        rsi_label, rsi_color, rsi_icon = "STRONG", "#10b981", "📈"
        rsi_note = "Above neutral — bulls in control"
    else:
        rsi_label, rsi_color, rsi_icon = "NEUTRAL", "#8892ab", "⚖️"
        rsi_note = "Balanced momentum — no edge"

    # Range utilization block
    daily_util = ranges['today']['util']
    if daily_util > 100:
        range_icon, range_status, range_color = "🔥", "EXCEEDED", "#ef4444"
        range_note = f"{daily_util:.0f}% of ATR used — extended"
    elif daily_util > 70:
        range_icon, range_status, range_color = "⚡", "NEAR LIMIT", "#f59e0b"
        range_note = f"{daily_util:.0f}% of ATR used — nearing cap"
    else:
        range_icon, range_status, range_color = "📊", "ROOM TO RUN", "#10b981"
        range_note = f"{daily_util:.0f}% of ATR used — expansion likely"

    # Signal block
    if trade_signals:
        top_sig = trade_signals[0]
        sig_dir = top_sig["direction"]
        sig_icon = "🟢" if sig_dir == "LONG" else "🔴"
        sig_color = "#10b981" if sig_dir == "LONG" else "#ef4444"
        sig_value = f'{sig_dir} · {top_sig["confidence"]} · Score {top_sig["score"]}'
        sig_note = f'{top_sig["pattern_name"]} at ${top_sig["level_price"]:,.0f}'
    else:
        sig_icon, sig_color = "🔍", "#6b7a99"
        sig_value = "Scanning..."
        sig_note = "No active setups — watching key levels"

    # Key levels block
    nearest_support = pivots['S1']
    nearest_resistance = pivots['R1']

    # Trend label
    trend_display = signal_trend.replace("_", " ").title()
    trend_color = "#10b981" if "BULL" in signal_trend else "#ef4444" if "BEAR" in signal_trend else "#f59e0b"

    # Compose structured brief HTML
    brief_html = (
        # Price hero row
        f'<div class="brief-price-row">'
        f'<span class="brief-price-main">${current:,.2f}</span>'
        f'<span class="brief-price-change" style="color:{chg_color};background:{chg_bg};">'
        f'{arrow} ${abs(daily_chg):,.2f} ({daily_pct:+.2f}%)</span>'
        f'</div>'
        # Trend + macro summary line
        f'<div class="brief-trend-line">'
        f'Daily trend: <b style="color:{trend_color};">{trend_display}</b>'
        f' &nbsp;·&nbsp; Macro bias: <b style="color:{bias_color};">{bias}</b>'
        f' &nbsp;·&nbsp; {drivers_html}'
        f'</div>'
        # 4-block grid
        f'<div class="brief-grid">'
        # Block 1: RSI
        f'<div class="brief-block">'
        f'<div class="brief-block-icon" style="background:rgba(107,122,153,0.08);">{rsi_icon}</div>'
        f'<div class="brief-block-content">'
        f'<div class="brief-block-label">RSI (14)</div>'
        f'<div class="brief-block-value">'
        f'<span style="color:{rsi_color};font-size:18px;font-weight:800;">{rsi:.0f}</span>'
        f' <span class="muted">{rsi_label}</span></div>'
        f'<div class="brief-block-value muted">{rsi_note}</div>'
        f'</div></div>'
        # Block 2: Range
        f'<div class="brief-block">'
        f'<div class="brief-block-icon" style="background:rgba(107,122,153,0.08);">{range_icon}</div>'
        f'<div class="brief-block-content">'
        f'<div class="brief-block-label">Daily Range</div>'
        f'<div class="brief-block-value">'
        f'<span style="color:{range_color};font-size:18px;font-weight:800;">{daily_util:.0f}%</span>'
        f' <span class="muted">{range_status}</span></div>'
        f'<div class="brief-block-value muted">{range_note}</div>'
        f'</div></div>'
        # Block 3: Signal
        f'<div class="brief-block">'
        f'<div class="brief-block-icon" style="background:rgba(107,122,153,0.08);">{sig_icon}</div>'
        f'<div class="brief-block-content">'
        f'<div class="brief-block-label">Signal Engine</div>'
        f'<div class="brief-block-value"><span style="color:{sig_color};">{sig_value}</span></div>'
        f'<div class="brief-block-value muted">{sig_note}</div>'
        f'</div></div>'
        # Block 4: Key Levels
        f'<div class="brief-block">'
        f'<div class="brief-block-icon" style="background:rgba(107,122,153,0.08);">🎯</div>'
        f'<div class="brief-block-content">'
        f'<div class="brief-block-label">Key Levels</div>'
        f'<div class="brief-block-value">'
        f'<span class="up">▲ ${nearest_resistance:,.0f}</span>'
        f' &nbsp;·&nbsp; '
        f'<span class="down">▼ ${nearest_support:,.0f}</span></div>'
        f'<div class="brief-block-value muted">Fibonacci pivot resistance · support</div>'
        f'</div></div>'
        f'</div>'
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

    # ── Sidebar: Branding + Controls + CTA ──
    with st.sidebar:
        # Product branding
        st.markdown("""<div style="text-align:center;padding:12px 0 16px;">
            <div style="font-size:18px;font-weight:900;color:#f0b90b;letter-spacing:2px;">GOLD COMMAND</div>
            <div style="font-size:9px;color:#5a6a8a;letter-spacing:1px;margin-top:2px;">XAU/USD Intelligence Terminal</div>
            <div style="font-size:8px;color:#3d4b6b;margin-top:4px;">v2.0 · by Anoop B.</div>
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

        # Beginner mode toggle
        st.markdown("### Display Mode")
        beginner_mode = st.toggle("Beginner Mode", value=True, help="Show tooltips and simplified explanations")
        st.session_state['beginner_mode'] = beginner_mode

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
        st.components.v1.html("""
            <div style="text-align:center;background:#000;border-radius:10px;padding:10px 6px 8px;
                border:1px solid rgba(59,130,246,0.15);">
                <a href="https://icmarkets.com/?camp=87951" target="_blank">
                    <img src="https://promo.icmarkets.com/Logos/2021/400x110/BAN_ICM_black_400x110.png"
                         style="width:100%;max-width:240px;margin-bottom:8px;" alt="ICMarkets"/>
                </a>
                <iframe src="https://secure.icmarkets.com/Partner/Widget/PriceWidget/87951"
                    width="100%" height="420" frameborder="0"
                    style="border:none;border-radius:6px;max-width:273px;">
                </iframe>
                <div style="margin-top:6px;">
                    <a href="https://icmarkets.com/?camp=87951" target="_blank"
                       style="font-size:11px;color:#4ade80;text-decoration:none;font-weight:700;">
                        Open Live Account →
                    </a>
                    <div style="font-size:8px;color:#666;margin-top:3px;">
                        Raw spreads from 0.0 pips · ASIC regulated
                    </div>
                </div>
            </div>
        """, height=560)

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
                        Your AI-powered gold market intelligence terminal. Start with the <b style="color:#f0b90b;">Daily Brief</b> below for a quick summary,
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
        <div class="kpi-card" style="--kpi-accent: {bias_kpi_color};">
            <div class="kpi-label">{tt_bias}</div>
            <div class="kpi-value" style="color:{bias_kpi_color};font-size:18px;">{bias_kpi_label}</div>
            <div class="kpi-delta neutral" style="color:{bias_kpi_color};background:rgba(0,0,0,0.2);">{bull_count}B / {bear_count}B drivers</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # TAB NAVIGATION
    # ══════════════════════════════════════════════════
    tab_dashboard, tab_signals, tab_intel, tab_news, tab_smc, tab_backtest = st.tabs([
        "📊 Dashboard", "🎯 Trade Signals", "🧠 Intelligence", "📰 News & Events", "🔲 SMC Engine", "📈 Backtest"
    ])

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

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 4 — NEWS & EVENTS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_news:

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown("""<div class="section-header" style="--section-accent: #a855f7;">
            <div>
                <span class="section-title">Volume Spike Detector</span>
                <div style="font-size:9px;color:#5a6a8a;margin-top:4px;">High-volume candles matched to news, economic events &amp; correlated asset moves</div>
            </div>
            <span class="pill pill-model">MULTI-SOURCE</span>
        </div>""", unsafe_allow_html=True)

        if spikes_correlated:
            for spike in spikes_correlated[:10]:
                dir_class = "spike-up" if spike['direction'] == 'UP' else "spike-down"
                dir_arrow = "▲" if spike['direction'] == 'UP' else "▼"
                dir_color = "#10b981" if spike['direction'] == 'UP' else "#ef4444"
                dir_bg = "rgba(16,185,129,0.08)" if spike['direction'] == 'UP' else "rgba(239,68,68,0.08)"

                # ── SECTION 1: Price Action ──
                st.markdown(f"""<div class="spike-card" style="border-left:3px solid {dir_color};">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
                        <div>
                            <div style="font-size:14px;font-weight:800;color:#e8ecf4;">{spike['date']}</div>
                            <div style="font-size:11px;color:#a8b2c8;margin-top:2px;font-family:JetBrains Mono;">
                                O: ${spike['open']:,.2f} &nbsp; H: ${spike['high']:,.2f} &nbsp; L: ${spike['low']:,.2f} &nbsp; C: ${spike['close']:,.2f}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:13px;font-weight:800;color:{dir_color};font-family:JetBrains Mono;">
                                {dir_arrow} ${abs(spike['change']):,.2f} ({spike['change_pct']:+.2f}%)
                            </div>
                            <div style="font-size:10px;color:#f0b90b;font-weight:700;margin-top:2px;">{spike['vol_ratio']:.1f}x Avg Volume</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                # ── SECTION 2: Economic Calendar ──
                econ_evts = spike.get('econ_events', [])
                if econ_evts:
                    cal_html = '<div style="background:rgba(15,21,40,0.6);border-radius:8px;padding:10px 12px;margin-bottom:10px;border:1px solid #1a2240;">'
                    cal_html += '<div style="font-size:9px;font-weight:800;color:#f59e0b;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;display:flex;align-items:center;gap:6px;">&#128197; Economic Calendar</div>'
                    for evt in econ_evts[:3]:
                        ic = "#ef4444" if evt['impact'] == 'HIGH' else "#f59e0b" if evt['impact'] == 'MEDIUM' else "#6b7a99"
                        ibg = f"rgba({239 if evt['impact']=='HIGH' else 245 if evt['impact']=='MEDIUM' else 107},{68 if evt['impact']=='HIGH' else 158 if evt['impact']=='MEDIUM' else 122},{68 if evt['impact']=='HIGH' else 11 if evt['impact']=='MEDIUM' else 153},0.15)"
                        dot = "&#128308;" if evt['impact'] == 'HIGH' else "&#128992;" if evt['impact'] == 'MEDIUM' else "&#9898;"
                        cal_html += f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:11px;">'
                        cal_html += f'<span style="font-size:8px;font-weight:800;padding:2px 8px;border-radius:3px;background:{ibg};color:{ic};min-width:40px;text-align:center;">{evt["impact"]}</span>'
                        cal_html += f'<span style="color:#e8ecf4;flex:1;">{html_escape(evt["title"][:70])}</span>'
                        cal_html += '</div>'
                    cal_html += '</div>'
                    st.markdown(cal_html, unsafe_allow_html=True)

                # ── SECTION 3: Correlated Asset Moves ──
                asset_moves = spike.get('asset_moves', {})
                if asset_moves:
                    moves_html = '<div style="background:rgba(15,21,40,0.6);border-radius:8px;padding:10px 12px;margin-bottom:10px;border:1px solid #1a2240;">'
                    moves_html += '<div style="font-size:9px;font-weight:800;color:#3b82f6;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;display:flex;align-items:center;gap:6px;">&#128200; Same-Day Cross-Market Moves</div>'
                    moves_html += '<div style="display:flex;flex-wrap:wrap;gap:6px;">'
                    for asset_name, mv in asset_moves.items():
                        mv_color = "#10b981" if mv['change_pct'] >= 0 else "#ef4444"
                        mv_bg = "rgba(16,185,129,0.08)" if mv['change_pct'] >= 0 else "rgba(239,68,68,0.08)"
                        mv_arrow = "▲" if mv['change_pct'] >= 0 else "▼"
                        asset_icon = get_instrument_icon(asset_name)
                        moves_html += (f'<div style="display:inline-flex;align-items:center;gap:5px;padding:5px 10px;'
                                       f'background:{mv_bg};border:1px solid {mv_color}22;border-radius:6px;font-size:11px;">'
                                       f'{asset_icon}<span style="color:#a8b2c8;font-weight:600;">{asset_name}</span>'
                                       f'<span style="color:{mv_color};font-family:JetBrains Mono;font-weight:700;">'
                                       f'{mv_arrow} {mv["change_pct"]:+.2f}%</span></div>')
                    moves_html += '</div></div>'
                    st.markdown(moves_html, unsafe_allow_html=True)

                # ── SECTION 4: Related Headlines ──
                if spike['news']:
                    news_html = '<div style="background:rgba(15,21,40,0.6);border-radius:8px;padding:10px 12px;margin-bottom:6px;border:1px solid #1a2240;">'
                    news_html += '<div style="font-size:9px;font-weight:800;color:#ef4444;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;display:flex;align-items:center;gap:6px;">&#128240; Related Headlines</div>'
                    for article in spike['news']:
                        source = f" — {article['source']}" if article['source'] else ""
                        safe_link = article['link'] if article['link'].startswith(('http://', 'https://')) else '#'
                        news_html += (f'<div style="padding:4px 0;border-bottom:1px solid rgba(26,34,64,0.3);font-size:11px;">'
                                      f'<a href="{safe_link}" target="_blank" rel="noopener noreferrer" style="color:#c8d0e4;text-decoration:none;">{html_escape(article["title"])}</a>'
                                      f'<span style="color:#5a6a8a;font-size:9px;">{source}</span></div>')
                    news_html += '</div>'
                    st.markdown(news_html, unsafe_allow_html=True)

                # ── Fallback ──
                if not spike['news'] and not econ_evts and not asset_moves:
                    st.markdown('<div style="font-size:11px;color:#5a6a8a;padding:8px 12px;background:rgba(15,21,40,0.4);border-radius:6px;border-left:2px solid #f59e0b;font-style:italic;">No catalyst identified — likely driven by options/futures expiry, institutional repositioning, or overseas session flows.</div>', unsafe_allow_html=True)
                elif not spike['news'] and not econ_evts:
                    st.markdown('<div style="font-size:11px;color:#5a6a8a;padding:8px 12px;background:rgba(15,21,40,0.4);border-radius:6px;border-left:2px solid #3b82f6;font-style:italic;">No headline catalyst — move likely driven by correlated asset flows shown above.</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No significant volume spikes detected in recent data.")

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        news_col, cal_col = st.columns([1, 1])

        with news_col:
            st.markdown("""<div class="section-header" style="--section-accent: #ef4444;">
                <span class="section-title">Live News Feed</span>
                <span class="pill pill-live">RSS · AUTO-REFRESH</span>
            </div>""", unsafe_allow_html=True)
            if news:
                # Directional impact rules: (keywords, instrument_name, typical_gold_impact, icon_color)
                _impact_rules = {
                    'gold': {
                        'keywords': ['gold', 'xau', 'bullion', 'precious metal', 'safe haven', 'gold price', 'gold demand', 'gold reserve'],
                        'name': 'Gold', 'icon': '&#129351;', 'color': '#f0b90b',
                    },
                    'dollar': {
                        'keywords': ['dollar', 'usd', 'dxy', 'fed', 'federal reserve', 'interest rate', 'rate hike', 'rate cut', 'fomc', 'powell'],
                        'name': 'Dollar', 'icon': '&#36;', 'color': '#10b981',
                    },
                    'oil': {
                        'keywords': ['oil', 'crude', 'opec', 'brent', 'wti', 'petroleum', 'energy'],
                        'name': 'Oil', 'icon': '&#128167;', 'color': '#8b5cf6',
                    },
                    'bonds': {
                        'keywords': ['bond', 'yield', 'treasury', '10-year', '10y', 'debt', 'sovereign'],
                        'name': 'Bonds', 'icon': '&#128196;', 'color': '#3b82f6',
                    },
                    'geopolitical': {
                        'keywords': ['war', 'attack', 'strike', 'nuclear', 'bomb', 'missile', 'invasion', 'crisis', 'emergency', 'sanctions', 'conflict', 'geopolitical', 'tariff', 'trade war'],
                        'name': 'Geopolitical', 'icon': '&#9888;', 'color': '#ef4444',
                        # Geopolitical events: Gold ↑, Stocks ↓, VIX ↑
                        'impacts': [('Gold', '↑', '#10b981'), ('Stocks', '↓', '#ef4444'), ('VIX', '↑', '#f59e0b')],
                    },
                    'stocks': {
                        'keywords': ['stock', 's&p', 'nasdaq', 'dow', 'equity', 'wall street', 'rally', 'selloff', 'correction', 'bear market', 'bull market'],
                        'name': 'Stocks', 'icon': '&#128200;', 'color': '#f59e0b',
                    },
                }
                for article in news[:20]:
                    date_str = article['published'].strftime('%b %d, %H:%M') if article['published'] else ""
                    source = f" — {article['source']}" if article['source'] else ""
                    title_lower = article['title'].lower()

                    # Detect impacts with directional chips
                    impact_chips = ""
                    is_breaking = False
                    matched_cats = []
                    for cat_key, rule in _impact_rules.items():
                        if any(kw in title_lower for kw in rule['keywords']):
                            matched_cats.append(cat_key)
                            if cat_key == 'geopolitical':
                                is_breaking = True
                                # Show directional impacts for geopolitical events
                                for instr, direction, dcolor in rule.get('impacts', []):
                                    impact_chips += (f'<span style="font-size:9px;padding:2px 6px;border-radius:3px;'
                                                     f'background:{dcolor}15;color:{dcolor};font-weight:700;'
                                                     f'display:inline-flex;align-items:center;gap:2px;">'
                                                     f'{instr} {direction}</span> ')
                            else:
                                c = rule['color']
                                impact_chips += (f'<span style="font-size:9px;padding:2px 6px;border-radius:3px;'
                                                 f'background:{c}15;color:{c};font-weight:700;'
                                                 f'display:inline-flex;align-items:center;gap:3px;">'
                                                 f'{rule["icon"]} {rule["name"]}</span> ')

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
        <div style="font-size:10px;color:#8a94a8;margin-bottom:6px;">XAU/USD Market Intelligence Terminal&nbsp;&nbsp;·&nbsp;&nbsp;v2.1</div>
        <div style="font-size:9px;color:#5a6a8a;margin-bottom:8px;">Developed by <span style="color:#f0b90b;font-weight:600;">Anoop B.</span></div>
        <div style="display:flex;justify-content:center;gap:20px;margin-bottom:8px;">
            <span style="font-size:8px;color:#3d4b6b;">📊 6 Intelligence Modules</span>
            <span style="font-size:8px;color:#3d4b6b;">🎯 Multi-TF Signal Engine</span>
            <span style="font-size:8px;color:#3d4b6b;">🧠 Auto-Computed Macro Analysis</span>
            <span style="font-size:8px;color:#3d4b6b;">📰 Live RSS News Feed</span>
        </div>
        <div style="margin-bottom:8px;">
            <a href="https://icmarkets.com/?camp=87951" target="_blank"
               style="font-size:9px;color:#60a5fa;text-decoration:none;font-weight:600;">
                Trade XAU/USD on ICMarkets →
            </a>
        </div>
        <div style="font-size:8px;color:#3d4b6b;letter-spacing:0.5px;">
            Data: Yahoo Finance, Google News RSS&nbsp;&nbsp;|&nbsp;&nbsp;Charts: TradingView&nbsp;&nbsp;|&nbsp;&nbsp;Signals: Proprietary Engine<br>
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
