"""
Data fetcher module for Gold Command dashboard.

Provides parallel data fetching with error boundaries and caching.
Wraps multiple data sources (yfinance, news feeds, economic calendars) with:
- Concurrent execution via ThreadPoolExecutor
- Error boundaries for graceful degradation
- Last-known-good caching with TTL
- Framework-agnostic design (no Streamlit dependencies)
"""

import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import feedparser
import pandas as pd
import requests
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("data_fetcher")

# Correlated instruments configuration
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

# Cache configuration
CACHE_DIR = Path("/tmp/gold_command_cache")
CACHE_TTL_SECONDS = 3600  # 1 hour


def _ensure_cache_dir() -> None:
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_cache_path(key: str) -> Path:
    """Get cache file path for a given key."""
    return CACHE_DIR / f"{key}.json"


def _read_cache(key: str) -> Optional[Dict[str, Any]]:
    """
    Read cached data for a key.

    Args:
        key: Cache key

    Returns:
        Cached data dict or None if not found/expired
    """
    cache_path = _get_cache_path(key)
    if not cache_path.exists():
        return None

    try:
        with open(cache_path, "r") as f:
            cache = json.load(f)

        # Check TTL
        cached_at = datetime.fromisoformat(cache.get("cached_at", ""))
        if datetime.now() - cached_at > timedelta(seconds=CACHE_TTL_SECONDS):
            logger.debug(f"Cache expired for {key}")
            return None

        return cache
    except (json.JSONDecodeError, OSError, ValueError) as e:
        logger.warning(f"Error reading cache for {key}: {e}")
        return None


def _write_cache(key: str, data: Any) -> None:
    """
    Write data to cache.

    Args:
        key: Cache key
        data: Data to cache (must be JSON-serializable)
    """
    _ensure_cache_dir()
    cache_path = _get_cache_path(key)

    try:
        cache_data = {
            "data": data,
            "cached_at": datetime.now().isoformat(),
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f, default=str)
    except (TypeError, OSError) as e:
        logger.warning(f"Error writing cache for {key}: {e}")


class DataCache:
    """
    Last-known-good cache for data sources.

    Stores the last successful fetch result for each data source.
    On fetch failure, returns cached data with stale flag.
    """

    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS):
        """
        Initialize cache.

        Args:
            ttl_seconds: Time-to-live for cached data in seconds
        """
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached data for a key.

        Args:
            key: Cache key

        Returns:
            Cache dict with 'data', 'cached_at', and 'stale' flag, or None
        """
        cache = _read_cache(key)
        if cache:
            return {
                "data": cache["data"],
                "cached_at": cache["cached_at"],
                "stale": False,
            }
        return None

    def get_stale(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get any cached data, even if expired (for fallback).

        Args:
            key: Cache key

        Returns:
            Cache dict with stale flag set to True, or None
        """
        cache_path = _get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cache = json.load(f)
            return {
                "data": cache["data"],
                "cached_at": cache["cached_at"],
                "stale": True,
            }
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Error reading stale cache for {key}: {e}")
            return None

    def set(self, key: str, data: Any) -> None:
        """
        Store data in cache.

        Args:
            key: Cache key
            data: Data to cache
        """
        _write_cache(key, data)


# Global cache instance
_cache = DataCache()


class SafeSectionError:
    """Represents an error from a safe section."""

    def __init__(self, section_name: str, exception: Exception):
        """
        Initialize error.

        Args:
            section_name: Name of the section that failed
            exception: The exception that was raised
        """
        self.section_name = section_name
        self.exception = exception
        self.timestamp = datetime.now()

    def html_snippet(self) -> str:
        """
        Generate error HTML snippet for display.

        Returns:
            HTML string for error card
        """
        error_msg = str(self.exception)
        return f"""
        <div style="border-left: 4px solid #ff4444; background: #fff5f5; padding: 12px; margin: 8px 0; border-radius: 4px;">
            <strong style="color: #cc0000;">{self.section_name}</strong> error: {error_msg}
        </div>
        """


# Global error tracker for safe sections
_section_errors: List[SafeSectionError] = []


@contextmanager
def safe_section(name: str):
    """
    Context manager for wrapping dashboard sections with error boundaries.

    If code within the context raises an exception:
    - The exception is logged
    - The error is tracked globally
    - None is yielded
    - Execution continues safely

    Usage:
        with safe_section("Macro Drivers"):
            result = expensive_calculation()
            # If exception occurs, section fails gracefully

    Args:
        name: Display name of the section

    Yields:
        None (placeholder for future error context)
    """
    try:
        yield
    except Exception as e:
        error = SafeSectionError(name, e)
        _section_errors.append(error)
        logger.error(f"Safe section '{name}' failed: {e}", exc_info=True)


def get_section_errors() -> List[SafeSectionError]:
    """
    Get all accumulated section errors.

    Returns:
        List of SafeSectionError instances
    """
    return _section_errors.copy()


def clear_section_errors() -> None:
    """Clear accumulated section errors."""
    global _section_errors
    _section_errors = []


def _fetch_gold_data() -> Tuple[Optional[pd.DataFrame], Optional[Exception]]:
    """
    Fetch gold OHLCV data.

    Returns:
        Tuple of (DataFrame or None, exception or None)
    """
    try:
        logger.debug("Fetching gold data (GC=F, 6mo, 1d)...")
        start_time = time.time()
        gold_df = yf.download("GC=F", period="6mo", interval="1d", progress=False)
        elapsed = time.time() - start_time
        logger.info(f"Gold data fetched in {elapsed:.2f}s: {len(gold_df)} rows")
        _cache.set("gold_df", gold_df.to_dict())
        return gold_df, None
    except Exception as e:
        logger.error(f"Error fetching gold data: {e}")
        return None, e


def _fetch_single_instrument(
    name: str, ticker: str
) -> Tuple[str, Optional[pd.DataFrame], Optional[Exception]]:
    """
    Fetch data for a single correlated instrument.

    Args:
        name: Display name
        ticker: Yahoo Finance ticker

    Returns:
        Tuple of (name, DataFrame or None, exception or None)
    """
    try:
        logger.debug(f"Fetching {name} ({ticker}, 3mo, 1d)...")
        start_time = time.time()
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        elapsed = time.time() - start_time
        logger.info(f"{name} fetched in {elapsed:.2f}s: {len(df)} rows")
        return name, df, None
    except Exception as e:
        logger.error(f"Error fetching {name} ({ticker}): {e}")
        return name, None, e


def _fetch_all_instruments() -> Tuple[Dict[str, pd.DataFrame], List[str]]:
    """
    Fetch all 8 correlated instruments in parallel.

    Returns:
        Tuple of (dict mapping name to DataFrame, list of error messages)
    """
    corr_data = {}
    errors = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_fetch_single_instrument, name, ticker): name
            for name, ticker in CORRELATED.items()
        }

        for future in as_completed(futures):
            name, df, error = future.result()
            if error:
                errors.append(f"Failed to fetch {name}: {error}")
                # Try to use cached data
                cached = _cache.get_stale(f"corr_{name}")
                if cached:
                    logger.info(f"Using stale cache for {name}")
                    # Reconstruct DataFrame from cached dict
                    corr_data[name] = pd.DataFrame(cached["data"])
            else:
                corr_data[name] = df
                _cache.set(f"corr_{name}", df.to_dict())

    return corr_data, errors


def _fetch_gold_news() -> Tuple[Optional[List[Dict[str, str]]], Optional[Exception]]:
    """
    Fetch gold news from Google News RSS feed.

    Returns:
        Tuple of (list of news dicts or None, exception or None)
    """
    try:
        logger.debug("Fetching gold news...")
        start_time = time.time()
        rss_url = "https://news.google.com/rss/search?q=gold%20price"
        feed = feedparser.parse(rss_url)

        news = []
        for entry in feed.entries[:10]:  # Limit to 10 items
            news.append(
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "summary": entry.get("summary", "")[:200],  # Truncate
                }
            )

        elapsed = time.time() - start_time
        logger.info(f"Gold news fetched in {elapsed:.2f}s: {len(news)} items")
        _cache.set("news", news)
        return news, None
    except Exception as e:
        logger.error(f"Error fetching gold news: {e}")
        return None, e


def _fetch_economic_calendar() -> Tuple[
    Optional[List[Dict[str, str]]], Optional[Exception]
]:
    """
    Fetch economic calendar events from FinnHub.

    Returns:
        Tuple of (list of event dicts or None, exception or None)

    Note:
        Requires FINNHUB_API_KEY environment variable.
        Falls back gracefully if API key is not set.
    """
    try:
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            logger.warning(
                "FINNHUB_API_KEY not set, skipping economic calendar fetch"
            )
            return [], None

        logger.debug("Fetching economic calendar...")
        start_time = time.time()

        # FinnHub economic calendar endpoint
        url = "https://finnhub.io/api/v1/economic_calendar"
        params = {"token": api_key}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        events = []
        for event in response.json()[:15]:  # Limit to 15 events
            events.append(
                {
                    "country": event.get("country", ""),
                    "event": event.get("event", ""),
                    "date": event.get("date", ""),
                    "estimate": event.get("estimate", ""),
                    "actual": event.get("actual", ""),
                }
            )

        elapsed = time.time() - start_time
        logger.info(f"Economic calendar fetched in {elapsed:.2f}s: {len(events)} events")
        _cache.set("econ_events", events)
        return events, None
    except Exception as e:
        logger.error(f"Error fetching economic calendar: {e}")
        return None, e


def fetch_all_data_parallel() -> Dict[str, Any]:
    """
    Fetch all data sources in parallel using ThreadPoolExecutor.

    Fetches:
    - Gold OHLCV data (GC=F, 6mo daily)
    - All 8 correlated instruments in parallel (DXY, US 10Y, VIX, etc.)
    - News feeds (Google RSS)
    - Economic calendar (FinnHub)

    Returns:
        Dict with keys:
        - 'gold_df': pandas DataFrame or None
        - 'corr_data': dict mapping instrument names to DataFrames
        - 'news': list of news dicts
        - 'econ_events': list of event dicts
        - 'errors': list of error messages
        - 'fetch_time_ms': total fetch time in milliseconds
        - 'cached': bool, True if any data came from cache
    """
    logger.info("Starting parallel data fetch...")
    fetch_start = time.time()
    all_errors = []
    cached_flags = {}

    # Fetch in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all fetch tasks
        gold_future = executor.submit(_fetch_gold_data)
        instruments_future = executor.submit(_fetch_all_instruments)
        news_future = executor.submit(_fetch_gold_news)
        econ_future = executor.submit(_fetch_economic_calendar)

        # Collect results as they complete
        gold_df, gold_error = gold_future.result()
        if gold_error:
            all_errors.append(f"Gold data: {gold_error}")
            # Try cache
            cached = _cache.get_stale("gold_df")
            if cached:
                logger.info("Using stale cache for gold data")
                gold_df = pd.DataFrame(cached["data"])
                cached_flags["gold"] = True

        corr_data, corr_errors = instruments_future.result()
        all_errors.extend(corr_errors)
        if corr_errors:
            cached_flags["corr"] = True

        news, news_error = news_future.result()
        if news_error:
            all_errors.append(f"News: {news_error}")
            cached = _cache.get_stale("news")
            if cached:
                logger.info("Using stale cache for news")
                news = cached["data"]
                cached_flags["news"] = True
        if news is None:
            news = []

        econ_events, econ_error = econ_future.result()
        if econ_error:
            all_errors.append(f"Economic calendar: {econ_error}")
            cached = _cache.get_stale("econ_events")
            if cached:
                logger.info("Using stale cache for economic events")
                econ_events = cached["data"]
                cached_flags["econ"] = True
        if econ_events is None:
            econ_events = []

    fetch_time_ms = int((time.time() - fetch_start) * 1000)

    logger.info(
        f"Parallel fetch completed in {fetch_time_ms}ms with {len(all_errors)} errors"
    )

    return {
        "gold_df": gold_df,
        "corr_data": corr_data,
        "news": news,
        "econ_events": econ_events,
        "errors": all_errors,
        "fetch_time_ms": fetch_time_ms,
        "cached": bool(cached_flags),
    }


if __name__ == "__main__":
    # Configure logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Test parallel fetch
    print("Testing parallel data fetch...")
    result = fetch_all_data_parallel()
    print(f"\nResults:")
    print(f"  Gold DF shape: {result['gold_df'].shape if result['gold_df'] is not None else 'None'}")
    print(f"  Correlated instruments: {len(result['corr_data'])}")
    print(f"  News items: {len(result['news'])}")
    print(f"  Economic events: {len(result['econ_events'])}")
    print(f"  Errors: {len(result['errors'])}")
    print(f"  Fetch time: {result['fetch_time_ms']}ms")
    print(f"  Used cache: {result['cached']}")

    if result["errors"]:
        print("\nErrors encountered:")
        for error in result["errors"]:
            print(f"  - {error}")
