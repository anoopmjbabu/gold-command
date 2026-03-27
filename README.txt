GOLD COMMAND - XAU/USD Market Intelligence Terminal
===================================================

SETUP (on any new machine)
--------------------------
1. Install Python 3.10+ from python.org
2. Double-click launch_gold_command.bat
   - It auto-installs: streamlit, yfinance, pandas, plotly, feedparser, requests
   - Opens browser to http://localhost:8501

FILES
-----
gold_command.py          - Main Streamlit dashboard (~1000 lines)
launch_gold_command.bat  - Windows launcher (installs deps + runs)
gold_technical_analysis.html - Old HTML-only version (superseded)
.streamlit/config.toml   - Dark theme config
README.txt               - This file

CURRENT FEATURES
----------------
- Live gold price data from Yahoo Finance (GC=F futures)
- TradingView embedded chart (15m, full-width, BB + Volume)
- 6 KPI cards: Price, RSI, ATR, 6M High/Low, Volume ratio
- Daily/Weekly/Monthly price ranges with ATR-based expected ranges
- 3-tier analysis (Beginner / Intermediate / Pro)
- Macro drivers auto-computed (DXY, 10Y, VIX, Oil, S&P) with BULL/BEAR tags
- 30-day rolling correlations (8 instruments)
- Pivot levels (S1/S2/R1/R2) + key support/resistance
- 30-day probability targets (up/down)
- Volume spike detector matched to news catalysts
- Breaking news feed (geopolitics, Fed, central banks, wars)
- Auto-refresh every 15 minutes (configurable in sidebar)

KNOWN LIMITATIONS / NEXT STEPS
-------------------------------
- All indicators computed on DAILY data only (not intraday)
- No candle pattern detection (doji, hammer, engulfing)
- No liquidity zone identification
- No multi-timeframe entry signals
- No push notifications / alerts
- Streamlit is not ideal for production SaaS (consider React/Next.js)
- Need authentication + Stripe for subscription model

TECH STACK
----------
Python 3.10+, Streamlit, yfinance, pandas, numpy, plotly, feedparser
TradingView embed (free widget)
Google News RSS for news feeds

DISCUSSION NOTES (for future development)
------------------------------------------
- Plan to host as subscription product for beginner gold traders
- Need to add: doji/pattern detection at liquidity zones,
  multi-timeframe confirmation (daily trend -> 4H zones -> 15m entry),
  simple BUY/SELL/WAIT signals with confidence scores
- Consider fintech-grade UI rebuild (React + animations)
- Legal: need financial disclaimer, possibly regulatory check
