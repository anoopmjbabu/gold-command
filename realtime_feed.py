"""
Real-time Gold Price Data Module for Gold Command Dashboard

This module provides multi-source gold price fetching with fallback support,
session detection for gold market trading hours, and caching.

Sources:
- GoldAPI.io: Real-time XAU/USD spot prices (free tier)
- Metals-API: Commodity price feed (free tier)
- yfinance: Fallback using GC=F ticker

Market Sessions (UTC):
- Asia/Pacific: 00:00 - 07:00
- London: 07:00 - 16:00
- London/NY Overlap: 13:30 - 16:00
- New York: 13:30 - 21:00
- Pre-London: 21:00 - 00:00 (previous day closing)
"""

import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any
import time

try:
    import yfinance as yf
except ImportError:
    yf = None

logger = logging.getLogger("realtime_feed")
logger.setLevel(logging.DEBUG)

# Create console handler if not already present
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

class PriceCache:
    """Simple in-memory TTL cache for price data."""

    def __init__(self):
        self.data = None
        self.timestamp = None
        self.ttl = 30  # seconds for real-time APIs

    def get(self, is_fallback: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached price data if still valid.

        Args:
            is_fallback: If True, uses longer TTL (300s) for yfinance data

        Returns:
            Cached price dict or None if expired/missing
        """
        if self.data is None:
            return None

        ttl = 300 if is_fallback else 30
        age = time.time() - self.timestamp

        if age < ttl:
            logger.debug(f"Cache hit (age: {age:.1f}s, TTL: {ttl}s)")
            return self.data

        logger.debug(f"Cache expired (age: {age:.1f}s, TTL: {ttl}s)")
        return None

    def set(self, data: Dict[str, Any]) -> None:
        """Store price data in cache."""
        self.data = data
        self.timestamp = time.time()
        logger.debug("Price data cached")

    def clear(self) -> None:
        """Clear cache."""
        self.data = None
        self.timestamp = None


_price_cache = PriceCache()


# ============================================================================
# SESSION DETECTION
# ============================================================================

def get_active_session() -> Dict[str, Any]:
    """
    Detect current gold market trading session based on UTC time.

    Gold markets operate in overlapping sessions across major financial centers.
    This function determines which session is currently active and provides
    timing information for UI display.

    Returns:
        dict: {
            'name': str,              # Session name
            'status': str,            # "ACTIVE", "CLOSED", or "OPENING_SOON"
            'opens_in': int or None,  # Minutes until next session (if closed)
            'closes_in': int or None, # Minutes until session closes (if active)
            'color': str,             # Hex color for UI display
        }

    Session times (UTC):
        - Asia/Pacific: 00:00 - 07:00
        - London: 07:00 - 16:00
        - London/NY Overlap: 13:30 - 16:00
        - New York: 13:30 - 21:00
        - Pre-London: 21:00 - 00:00 (previous day closing)
    """
    now = datetime.now(timezone.utc)
    hour = now.hour
    minute = now.minute
    current_minutes = hour * 60 + minute

    # Define sessions: (start_minutes, end_minutes, name, color)
    sessions = [
        (0, 420, "Asia/Pacific", "#FF6B6B"),      # 00:00 - 07:00
        (420, 810, "London", "#4ECDC4"),          # 07:00 - 13:30
        (810, 960, "London/NY Overlap", "#FFE66D"), # 13:30 - 16:00
        (960, 1260, "New York", "#95E1D3"),       # 16:00 - 21:00
        (1260, 1440, "Pre-London", "#C7CEEA"),    # 21:00 - 00:00
    ]

    # Simplified session definitions for status checking
    active_session = None
    next_session = None

    for start, end, name, color in sessions:
        if start <= current_minutes < end:
            active_session = {
                'name': name,
                'status': 'ACTIVE',
                'closes_in': end - current_minutes,
                'opens_in': None,
                'color': color,
            }
            break

    if active_session:
        return active_session

    # If no active session, find the next one
    for start, end, name, color in sessions:
        if current_minutes < start:
            next_session = {
                'name': name,
                'status': 'OPENING_SOON',
                'opens_in': start - current_minutes,
                'closes_in': None,
                'color': color,
            }
            break

    # Wrap to first session of next day
    if not next_session:
        next_session = {
            'name': sessions[0][2],
            'status': 'OPENING_SOON',
            'opens_in': 1440 - current_minutes,  # Minutes until midnight
            'closes_in': None,
            'color': sessions[0][3],
        }

    return next_session


# ============================================================================
# PRICE FETCHERS
# ============================================================================

def _fetch_goldapi(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Fetch real-time gold prices from GoldAPI.io.

    Free tier provides:
    - Real-time XAU/USD spot prices
    - Bid/ask spread
    - Daily change and change percentage

    API Docs: https://www.goldapi.io/api

    Args:
        api_key: GoldAPI.io access token

    Returns:
        dict with keys: price, bid, ask, ch (change), chp (change_pct), timestamp
        or None if request fails
    """
    if not api_key:
        logger.debug("GoldAPI key not provided")
        return None

    try:
        url = "https://www.goldapi.io/api/XAU/USD"
        headers = {"x-access-token": api_key}

        logger.debug(f"Fetching from GoldAPI: {url}")
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        data = response.json()
        logger.info(f"GoldAPI success: ${data.get('price'):.2f}")

        return {
            'price': float(data['price']),
            'bid': float(data.get('bid', data['price'])),
            'ask': float(data.get('ask', data['price'])),
            'change': float(data.get('ch', 0)),
            'change_pct': float(data.get('chp', 0)),
            'timestamp': datetime.fromisoformat(
                data.get('timestamp', '').replace('Z', '+00:00')
            ) if data.get('timestamp') else datetime.now(timezone.utc),
            'source': 'GoldAPI',
        }
    except requests.exceptions.RequestException as e:
        logger.warning(f"GoldAPI request failed: {e}")
        return None
    except (KeyError, ValueError) as e:
        logger.warning(f"GoldAPI parse error: {e}")
        return None


def _fetch_metals_api(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Fetch gold prices from Metals-API.

    Free tier provides:
    - Commodity prices for precious metals
    - Base currency conversion support

    API Docs: https://metals-api.com/

    Args:
        api_key: Metals-API access key

    Returns:
        dict with keys: price, bid, ask, change, change_pct, timestamp
        or None if request fails
    """
    if not api_key:
        logger.debug("Metals-API key not provided")
        return None

    try:
        url = "https://metals-api.com/api/latest"
        params = {
            'access_key': api_key,
            'base': 'XAU',
            'symbols': 'USD',
        }

        logger.debug(f"Fetching from Metals-API")
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()

        data = response.json()

        if not data.get('success'):
            logger.warning(f"Metals-API error: {data.get('error', {}).get('info')}")
            return None

        price = data['rates'].get('USD')
        if price is None:
            logger.warning("No USD rate in Metals-API response")
            return None

        logger.info(f"Metals-API success: ${price:.2f}")

        return {
            'price': float(price),
            'bid': float(price * 0.995),  # Approximate bid (0.5% spread)
            'ask': float(price * 1.005),  # Approximate ask (0.5% spread)
            'change': 0.0,  # Not provided by free tier
            'change_pct': 0.0,
            'timestamp': datetime.now(timezone.utc),
            'source': 'MetalsAPI',
        }
    except requests.exceptions.RequestException as e:
        logger.warning(f"Metals-API request failed: {e}")
        return None
    except (KeyError, ValueError) as e:
        logger.warning(f"Metals-API parse error: {e}")
        return None


def _fetch_yfinance_fallback() -> Optional[Dict[str, Any]]:
    """
    Fetch gold prices from yfinance as fallback.

    Uses the GC=F ticker (COMEX Gold Futures) as a proxy for spot prices.

    Note: yfinance data is delayed by ~15-20 minutes and has lower update frequency.
    Use this only as fallback when API keys are not available.

    API Docs: https://github.com/ranaroussi/yfinance

    Returns:
        dict with keys: price, bid, ask, change, change_pct, timestamp
        or None if fetch fails
    """
    if yf is None:
        logger.warning("yfinance not installed")
        return None

    try:
        logger.debug("Fetching gold price from yfinance (GC=F)")
        ticker = yf.Ticker("GC=F")
        data = ticker.history(period="1d")

        if data.empty:
            logger.warning("yfinance returned no data")
            return None

        latest = data.iloc[-1]
        price = float(latest['Close'])
        prev_close = float(data.iloc[-2]['Close']) if len(data) > 1 else price
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close != 0 else 0

        logger.info(f"yfinance success: ${price:.2f}")

        return {
            'price': price,
            'bid': float(latest['Low']),
            'ask': float(latest['High']),
            'change': change,
            'change_pct': change_pct,
            'high_24h': float(latest['High']),
            'low_24h': float(latest['Low']),
            'timestamp': datetime.now(timezone.utc),
            'source': 'yfinance',
        }
    except Exception as e:
        logger.warning(f"yfinance fallback failed: {e}")
        return None


# ============================================================================
# MAIN PRICE FETCHER
# ============================================================================

def get_realtime_price(
    goldapi_key: Optional[str] = None,
    metals_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch real-time gold prices with multi-source fallback strategy.

    This function implements a cascading fallback strategy:
    1. GoldAPI.io (real-time, free tier)
    2. Metals-API (real-time, free tier)
    3. yfinance (delayed, open-source fallback)

    Results are cached with TTL to avoid excessive API calls:
    - Real-time APIs: 30 second cache
    - yfinance fallback: 300 second cache

    Args:
        goldapi_key: GoldAPI.io access token (optional, from environment or config)
        metals_api_key: Metals-API access key (optional, from environment or config)

    Returns:
        dict with keys:
        {
            'price': float,           # Current XAU/USD spot price
            'bid': float,             # Bid price
            'ask': float,             # Ask price
            'change': float,          # Daily change in dollars
            'change_pct': float,      # Daily change percentage
            'high_24h': float,        # 24h high (if available)
            'low_24h': float,         # 24h low (if available)
            'source': str,            # "GoldAPI", "MetalsAPI", or "yfinance"
            'timestamp': datetime,    # Time of price quote
            'is_realtime': bool,      # True if from paid API, False if yfinance
            'session': dict,          # Output of get_active_session()
        }

    Raises:
        RuntimeError: If all sources fail and cache is empty

    Example:
        >>> price_data = get_realtime_price(goldapi_key="YOUR_KEY")
        >>> print(f"Gold: ${price_data['price']:.2f}")
        >>> print(f"Session: {price_data['session']['name']}")
    """
    # Check cache first
    is_fallback_cached = _price_cache.data and _price_cache.data.get('source') == 'yfinance'
    cached = _price_cache.get(is_fallback=is_fallback_cached)

    if cached:
        cached['session'] = get_active_session()
        return cached

    # Try real-time sources first
    price_data = _fetch_goldapi(goldapi_key)
    if price_data:
        is_fallback = False
    else:
        price_data = _fetch_metals_api(metals_api_key)
        if price_data:
            is_fallback = False
        else:
            # Fall back to yfinance
            price_data = _fetch_yfinance_fallback()
            is_fallback = True

    if not price_data:
        # All sources failed - check if we have stale cache
        if _price_cache.data:
            logger.warning("All sources failed, returning stale cache")
            _price_cache.data['session'] = get_active_session()
            return _price_cache.data

        raise RuntimeError(
            "All gold price sources failed. "
            "No API keys provided and yfinance unavailable."
        )

    # Ensure all required keys exist
    result = {
        'price': price_data.get('price'),
        'bid': price_data.get('bid'),
        'ask': price_data.get('ask'),
        'change': price_data.get('change', 0.0),
        'change_pct': price_data.get('change_pct', 0.0),
        'high_24h': price_data.get('high_24h'),
        'low_24h': price_data.get('low_24h'),
        'source': price_data.get('source'),
        'timestamp': price_data.get('timestamp', datetime.now(timezone.utc)),
        'is_realtime': not is_fallback,
        'session': get_active_session(),
    }

    # Cache the result
    _price_cache.set(result)

    logger.info(
        f"Price fetched from {result['source']}: "
        f"${result['price']:.2f} ({result['session']['name']})"
    )

    return result


# ============================================================================
# CTRADER INTEGRATION STUB
# ============================================================================

class CTraderFeed:
    """
    Stub for ICMarkets cTrader Open API real-time quote integration.

    FUTURE: This class is designed to support WebSocket-based real-time gold prices
    from ICMarkets cTrader platform. Currently a placeholder with documented interfaces.

    cTrader Open API Documentation:
    https://help.ctrader.com/open-api/python-SDK/python-sdk-index/

    Requirements:
    - ICMarkets demo or live trading account
    - Client ID and Secret from cTrader API settings
    - Access token from OAuth2 authentication

    Example (future implementation):
        >>> ctrader = CTraderFeed()
        >>> ctrader.connect(
        ...     client_id="YOUR_CLIENT_ID",
        ...     client_secret="YOUR_CLIENT_SECRET",
        ...     access_token="YOUR_ACCESS_TOKEN"
        ... )
        >>> ctrader.subscribe_quotes(symbol="XAUUSD")
        >>> ctrader.on_quote(lambda q: print(f"${q['bid']}"))
    """

    def __init__(self):
        """Initialize cTrader feed connector."""
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.connected = False
        self.quotes_callbacks = []
        logger.debug("CTraderFeed initialized (stub)")

    def connect(
        self,
        client_id: str,
        client_secret: str,
        access_token: str,
    ) -> None:
        """
        Establish WebSocket connection to cTrader Open API.

        FUTURE: Implement OAuth2 token validation and WebSocket handshake.

        Args:
            client_id: OAuth2 client ID from cTrader settings
            client_secret: OAuth2 client secret (store securely)
            access_token: OAuth2 access token

        Raises:
            NotImplementedError: Currently a stub for future implementation
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        logger.warning("CTraderFeed.connect() is not yet implemented")
        raise NotImplementedError(
            "cTrader Open API integration coming soon. "
            "See: https://help.ctrader.com/open-api/python-SDK/python-sdk-index/"
        )

    def subscribe_quotes(self, symbol: str = "XAUUSD") -> None:
        """
        Subscribe to real-time quote updates for a symbol.

        FUTURE: Send subscription message to cTrader WebSocket and maintain feed.

        Args:
            symbol: Trading symbol (default: XAUUSD for gold)

        Raises:
            NotImplementedError: Currently a stub for future implementation
        """
        if not self.connected:
            raise RuntimeError("Not connected to cTrader. Call connect() first.")

        logger.warning(f"CTraderFeed.subscribe_quotes({symbol}) is not yet implemented")
        raise NotImplementedError(
            "Quote subscription coming soon. "
            "See: https://help.ctrader.com/open-api/python-SDK/python-sdk-index/"
        )

    def on_quote(self, callback) -> None:
        """
        Register callback for real-time quote updates.

        FUTURE: Store callback and invoke on each quote message from WebSocket.

        Args:
            callback: Function(quote_dict) called on each price update.
                     quote_dict contains: bid, ask, spread, timestamp, etc.

        Example:
            >>> def handle_quote(q):
            ...     print(f"XAUUSD: {q['bid']}/{q['ask']}")
            >>> ctrader.on_quote(handle_quote)
        """
        self.quotes_callbacks.append(callback)
        logger.debug(f"Registered quote callback: {callback.__name__}")


if __name__ == "__main__":
    # Example usage
    print("Gold Command - Real-time Feed Module")
    print("=" * 50)

    # Session detection example
    session = get_active_session()
    print(f"\nCurrent Session: {session['name']} ({session['status']})")
    if session['status'] == 'ACTIVE':
        print(f"Closes in: {session['closes_in']} minutes")
    else:
        print(f"Opens in: {session['opens_in']} minutes")

    # Price fetching example (without API keys, will use yfinance)
    try:
        price_data = get_realtime_price()
        print(f"\nGold Price: ${price_data['price']:.2f}")
        print(f"Bid/Ask: ${price_data['bid']:.2f} / ${price_data['ask']:.2f}")
        print(f"Change: {price_data['change']:+.2f} ({price_data['change_pct']:+.2f}%)")
        print(f"Source: {price_data['source']} (Real-time: {price_data['is_realtime']})")
        print(f"Timestamp: {price_data['timestamp'].isoformat()}")
    except RuntimeError as e:
        print(f"Error: {e}")
