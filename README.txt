GOLD COMMAND - XAU/USD Market Intelligence Terminal
===================================================

SETUP (on any new machine)
--------------------------
1. Install Python 3.10+ from python.org
2. Install dependencies: pip install streamlit yfinance pandas numpy feedparser requests
3. Run: streamlit run gold_command.py
   - Opens browser to http://localhost:8501

FILES
-----
gold_command.py          - Main Streamlit dashboard
signal_engine.py         - Multi-TF signal engine (15m entries at 4H S/R)
.streamlit/config.toml   - Dark theme config
README.txt               - This file

CURRENT FEATURES (v2.1)
-----------------------
- Live gold price data from Yahoo Finance (GC=F futures)
- TradingView embedded chart (15m, full-width, BB + Volume)
- 6 KPI cards: Price, RSI, ATR, 6M High/Low, Volume ratio
- Daily/Weekly/Monthly price ranges with ATR-based expected ranges
- 3-tier analysis (Beginner / Intermediate / Pro)
- Macro drivers auto-computed (DXY, 10Y, VIX, Oil, S&P) with animated SVG icons
- Multi-window correlations (7D/30D/90D) with interpretation labels
- Multi-timeframe probability bars (Daily/Weekly/Monthly)
- Signal engine: candle patterns at 4H S/R zones, session + volume filters
- Volume spike detector with cross-market moves + economic calendar
- Live RSS news feed with directional impact chips
- Beginner tooltip/glossary system (22 terms)
- 6-tab navigation: Dashboard, Trade Signals, Intelligence, News, SMC, Backtest
- ICMarkets live price widget (partner integration)
- Auto-refresh (configurable, sidebar)
- Social proof stats ticker

TECH STACK
----------
Python 3.10+, Streamlit, yfinance, pandas, numpy, feedparser, requests
TradingView embed (free widget)
Google News RSS for news feeds
ICMarkets partner widget

Developed by Anoop B.
