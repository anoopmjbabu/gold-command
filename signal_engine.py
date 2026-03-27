"""
GOLD COMMAND — Signal Engine
Price action signal detection: S/R levels, candle patterns,
multi-timeframe alignment, and scored trade signals.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import time as _time
import logging

_logger = logging.getLogger("signal_engine")


def _fetch_with_retry(symbol, period, interval, max_retries=3):
    """Fetch yfinance data with retry logic for rate limits."""
    for attempt in range(max_retries):
        try:
            t = yf.Ticker(symbol)
            df = t.history(period=period, interval=interval)
            df.index = df.index.tz_localize(None) if df.index.tz else df.index
            if len(df) > 0:
                return df
            return pd.DataFrame()
        except Exception as e:
            _logger.warning(f"Fetch {interval} attempt {attempt+1}/{max_retries}: {type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                _time.sleep(2 ** attempt)
    return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════
# DATA FETCHER — Multi-timeframe
# ═══════════════════════════════════════════════════════════════
def fetch_multi_timeframe(symbol="GC=F"):
    """Fetch gold data on daily, 4H (approx via 1H), and 15m timeframes."""
    data = {}

    # Daily — 6 months for trend context
    df = _fetch_with_retry(symbol, "6mo", "1d")
    if not df.empty:
        data['daily'] = df

    # 1H — 60 days (used to build 4H by resampling)
    df = _fetch_with_retry(symbol, "60d", "1h")
    if not df.empty:
        data['1h'] = df
        # Resample to 4H
        df_4h = df.resample('4h').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min',
            'Close': 'last', 'Volume': 'sum'
        }).dropna()
        data['4h'] = df_4h

    # 15m — last 60 days for entry signals
    df = _fetch_with_retry(symbol, "60d", "15m")
    if not df.empty:
        data['15m'] = df

    return data


# ═══════════════════════════════════════════════════════════════
# LAYER 1 — TREND DETECTION (Daily)
# ═══════════════════════════════════════════════════════════════
def detect_swing_points(df, lookback=5):
    """Detect swing highs and swing lows using local extrema.
    A swing high = a high that is higher than the `lookback` bars on each side.
    A swing low = a low that is lower than the `lookback` bars on each side.
    """
    highs = df['High'].values
    lows = df['Low'].values
    swing_highs = []
    swing_lows = []

    for i in range(lookback, len(df) - lookback):
        # Swing high
        if highs[i] == max(highs[i - lookback:i + lookback + 1]):
            swing_highs.append({
                'index': df.index[i],
                'price': highs[i],
                'bar_index': i,
            })
        # Swing low
        if lows[i] == min(lows[i - lookback:i + lookback + 1]):
            swing_lows.append({
                'index': df.index[i],
                'price': lows[i],
                'bar_index': i,
            })

    return swing_highs, swing_lows


def detect_trend(df, lookback=5):
    """Determine trend from price structure (higher highs/lows vs lower highs/lows)."""
    swing_highs, swing_lows = detect_swing_points(df, lookback)

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "NEUTRAL", swing_highs, swing_lows

    # Check last 3 swing points
    recent_highs = [s['price'] for s in swing_highs[-3:]]
    recent_lows = [s['price'] for s in swing_lows[-3:]]

    higher_highs = all(recent_highs[i] > recent_highs[i-1] for i in range(1, len(recent_highs)))
    higher_lows = all(recent_lows[i] > recent_lows[i-1] for i in range(1, len(recent_lows)))
    lower_highs = all(recent_highs[i] < recent_highs[i-1] for i in range(1, len(recent_highs)))
    lower_lows = all(recent_lows[i] < recent_lows[i-1] for i in range(1, len(recent_lows)))

    if higher_highs and higher_lows:
        trend = "BULLISH"
    elif lower_highs and lower_lows:
        trend = "BEARISH"
    elif higher_highs or higher_lows:
        trend = "WEAK_BULLISH"
    elif lower_highs or lower_lows:
        trend = "WEAK_BEARISH"
    else:
        trend = "NEUTRAL"

    return trend, swing_highs, swing_lows


# ═══════════════════════════════════════════════════════════════
# LAYER 2 — SUPPORT/RESISTANCE ZONES (4H)
# ═══════════════════════════════════════════════════════════════
def find_sr_levels(df, lookback=5, merge_threshold_pct=0.3):
    """Find support and resistance levels from swing points.
    Merge nearby levels within threshold % and score by touch count.
    """
    swing_highs, swing_lows = detect_swing_points(df, lookback)

    # Collect all reaction prices
    all_levels = []
    for s in swing_highs:
        all_levels.append({'price': s['price'], 'type': 'resistance', 'date': s['index']})
    for s in swing_lows:
        all_levels.append({'price': s['price'], 'type': 'support', 'date': s['index']})

    if not all_levels:
        return []

    # Sort by price
    all_levels.sort(key=lambda x: x['price'])

    # Merge nearby levels
    merged = []
    current_group = [all_levels[0]]

    for i in range(1, len(all_levels)):
        prev_price = current_group[-1]['price']
        curr_price = all_levels[i]['price']
        pct_diff = abs(curr_price - prev_price) / prev_price * 100

        if pct_diff <= merge_threshold_pct:
            current_group.append(all_levels[i])
        else:
            # Finalize current group
            avg_price = np.mean([l['price'] for l in current_group])
            touches = len(current_group)
            types = [l['type'] for l in current_group]
            level_type = 'support' if types.count('support') >= types.count('resistance') else 'resistance'
            latest_date = max(l['date'] for l in current_group)
            merged.append({
                'price': round(avg_price, 2),
                'type': level_type,
                'touches': touches,
                'latest_touch': latest_date,
                'strength': min(touches * 20, 100),  # 1 touch = 20, max 100
            })
            current_group = [all_levels[i]]

    # Don't forget the last group
    if current_group:
        avg_price = np.mean([l['price'] for l in current_group])
        touches = len(current_group)
        types = [l['type'] for l in current_group]
        level_type = 'support' if types.count('support') >= types.count('resistance') else 'resistance'
        latest_date = max(l['date'] for l in current_group)
        merged.append({
            'price': round(avg_price, 2),
            'type': level_type,
            'touches': touches,
            'latest_touch': latest_date,
            'strength': min(touches * 20, 100),
        })

    # Sort by strength (most touched first)
    merged.sort(key=lambda x: x['strength'], reverse=True)
    return merged


def find_nearby_levels(sr_levels, current_price, range_pct=1.5):
    """Find S/R levels within range_pct of current price."""
    nearby = []
    for level in sr_levels:
        distance_pct = abs(level['price'] - current_price) / current_price * 100
        if distance_pct <= range_pct:
            level['distance_pct'] = round(distance_pct, 2)
            level['distance'] = round(abs(level['price'] - current_price), 2)
            nearby.append(level)
    return sorted(nearby, key=lambda x: x['distance'])


# ═══════════════════════════════════════════════════════════════
# LAYER 3 — CANDLE PATTERN DETECTION (15m / 1H)
# ═══════════════════════════════════════════════════════════════
def detect_candle_patterns(df):
    """Detect key reversal candle patterns on each bar.
    Returns the dataframe with a 'pattern' column.
    """
    df = df.copy()
    df['body'] = abs(df['Close'] - df['Open'])
    df['upper_wick'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    df['lower_wick'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['full_range'] = df['High'] - df['Low']
    df['is_bullish'] = df['Close'] > df['Open']
    df['pattern'] = 'none'
    df['pattern_bias'] = 'none'  # bullish, bearish, or neutral

    for i in range(2, len(df)):
        body = df['body'].iloc[i]
        upper_wick = df['upper_wick'].iloc[i]
        lower_wick = df['lower_wick'].iloc[i]
        full_range = df['full_range'].iloc[i]
        is_bullish = df['is_bullish'].iloc[i]

        if full_range == 0:
            continue

        body_ratio = body / full_range
        upper_ratio = upper_wick / full_range
        lower_ratio = lower_wick / full_range

        prev_body = df['body'].iloc[i - 1]
        prev_bullish = df['is_bullish'].iloc[i - 1]
        prev_range = df['full_range'].iloc[i - 1]

        # ── DOJI ──
        # Body is less than 10% of range, both wicks present
        if body_ratio < 0.1 and upper_wick > 0 and lower_wick > 0:
            df.iloc[i, df.columns.get_loc('pattern')] = 'doji'
            df.iloc[i, df.columns.get_loc('pattern_bias')] = 'neutral'

        # ── HAMMER (bullish) ──
        # Small body at top, long lower wick (>60% of range), small upper wick
        elif lower_ratio > 0.6 and body_ratio < 0.3 and upper_ratio < 0.15:
            df.iloc[i, df.columns.get_loc('pattern')] = 'hammer'
            df.iloc[i, df.columns.get_loc('pattern_bias')] = 'bullish'

        # ── INVERTED HAMMER / SHOOTING STAR (bearish) ──
        # Small body at bottom, long upper wick (>60%), small lower wick
        elif upper_ratio > 0.6 and body_ratio < 0.3 and lower_ratio < 0.15:
            df.iloc[i, df.columns.get_loc('pattern')] = 'shooting_star'
            df.iloc[i, df.columns.get_loc('pattern_bias')] = 'bearish'

        # ── BULLISH ENGULFING ──
        # Current bullish candle body fully engulfs previous bearish candle body
        elif (is_bullish and not prev_bullish and
              body > prev_body * 1.1 and prev_body > 0 and
              df['Close'].iloc[i] > df['Open'].iloc[i - 1] and
              df['Open'].iloc[i] < df['Close'].iloc[i - 1] and
              df['Close'].iloc[i] >= df['High'].iloc[i - 1] and
              df['Open'].iloc[i] <= df['Low'].iloc[i - 1]):
            df.iloc[i, df.columns.get_loc('pattern')] = 'bullish_engulfing'
            df.iloc[i, df.columns.get_loc('pattern_bias')] = 'bullish'

        # ── BEARISH ENGULFING ──
        # Current bearish candle body fully engulfs previous bullish candle body
        elif (not is_bullish and prev_bullish and
              body > prev_body * 1.1 and prev_body > 0 and
              df['Open'].iloc[i] > df['Close'].iloc[i - 1] and
              df['Close'].iloc[i] < df['Open'].iloc[i - 1] and
              df['Open'].iloc[i] >= df['High'].iloc[i - 1] and
              df['Close'].iloc[i] <= df['Low'].iloc[i - 1]):
            df.iloc[i, df.columns.get_loc('pattern')] = 'bearish_engulfing'
            df.iloc[i, df.columns.get_loc('pattern_bias')] = 'bearish'

        # ── PIN BAR (bullish) ──
        # Lower wick > 2.5x body, small upper wick
        elif lower_wick > body * 2.5 and upper_ratio < 0.15 and body_ratio > 0.1:
            df.iloc[i, df.columns.get_loc('pattern')] = 'pin_bar_bull'
            df.iloc[i, df.columns.get_loc('pattern_bias')] = 'bullish'

        # ── PIN BAR (bearish) ──
        # Upper wick > 2.5x body, small lower wick
        elif upper_wick > body * 2.5 and lower_ratio < 0.15 and body_ratio > 0.1:
            df.iloc[i, df.columns.get_loc('pattern')] = 'pin_bar_bear'
            df.iloc[i, df.columns.get_loc('pattern_bias')] = 'bearish'

    return df


# ═══════════════════════════════════════════════════════════════
# SIGNAL SCORER — Cross-reference all layers
# ═══════════════════════════════════════════════════════════════
def compute_volume_score(df, index):
    """Score based on volume relative to 20-bar average."""
    vol = df['Volume'].iloc[index]
    avg_vol = df['Volume'].iloc[max(0, index - 20):index].mean()
    if avg_vol == 0:
        return 0
    ratio = vol / avg_vol
    if ratio >= 2.0:
        return 25  # Very high volume confirmation
    elif ratio >= 1.5:
        return 15
    elif ratio >= 1.0:
        return 5
    return 0


def _get_session_label(bar_time):
    """Classify a bar's time into a trading session."""
    if not hasattr(bar_time, 'hour'):
        return "Unknown"
    h = bar_time.hour
    if 7 <= h < 12:
        return "London"
    elif 12 <= h < 17:
        return "London/NY"
    elif 17 <= h < 21:
        return "New York"
    else:
        return "Asia"


def generate_signals(mtf_data, max_signals=10):
    """
    Main signal generation — cross-references all 3 layers.

    Layer 1: Daily trend direction
    Layer 2: 4H support/resistance levels
    Layer 3: 15m candle patterns at those levels

    Returns a list of scored signals.
    """
    signals = []

    if 'daily' not in mtf_data or '4h' not in mtf_data:
        return signals

    entry_tf_key = '15m' if '15m' in mtf_data else '1h'
    if entry_tf_key not in mtf_data:
        return signals

    # Layer 1: Get daily trend
    daily_trend, daily_sh, daily_sl = detect_trend(mtf_data['daily'], lookback=5)

    # Layer 2: Get S/R from 4H
    sr_levels = find_sr_levels(mtf_data['4h'], lookback=5, merge_threshold_pct=0.4)

    # Layer 3: Detect patterns on entry timeframe
    entry_df = detect_candle_patterns(mtf_data[entry_tf_key])
    current_price = entry_df['Close'].iloc[-1]

    # Find S/R levels near current price
    nearby_levels = find_nearby_levels(sr_levels, current_price, range_pct=1.5)

    # Scan recent entry bars for patterns at levels
    scan_range = min(20, len(entry_df))  # Look at last 20 bars

    for i in range(-scan_range, 0):
        idx = len(entry_df) + i
        if idx < 2:
            continue

        bar = entry_df.iloc[idx]
        pattern = bar['pattern']
        pattern_bias = bar['pattern_bias']

        if pattern == 'none':
            continue

        bar_price = bar['Close']
        bar_low = bar['Low']
        bar_high = bar['High']
        bar_time = entry_df.index[idx]

        # ── SESSION FILTER ──
        # Only consider signals during active gold trading sessions:
        # London (07:00-16:00 UTC), New York (13:30-21:00 UTC)
        # Combined active window: 07:00-21:00 UTC covers both sessions
        if hasattr(bar_time, 'hour'):
            bar_hour = bar_time.hour
            if bar_hour < 7 or bar_hour >= 21:
                continue  # Skip Asia session — low liquidity, unreliable patterns

        # ── MINIMUM VOLUME FILTER ──
        # Skip candles with below-average volume — patterns need conviction
        bar_vol = bar.get('Volume', 0) if hasattr(bar, 'get') else bar['Volume'] if 'Volume' in entry_df.columns else 0
        if bar_vol > 0 and idx > 20:
            avg_vol = entry_df['Volume'].iloc[max(0, idx - 20):idx].mean()
            if avg_vol > 0 and (bar_vol / avg_vol) < 0.5:
                continue  # Skip very low volume bars — likely noise

        # Check if this pattern is near a S/R level
        for level in nearby_levels:
            level_price = level['price']
            distance_pct = abs(bar_price - level_price) / level_price * 100

            # Pattern must be within 0.5% of the level
            # Also check if the wick touched the level
            wick_touched = bar_low <= level_price <= bar_high
            close_to_level = distance_pct <= 0.5

            if not (wick_touched or close_to_level):
                continue

            # Direction must align with level type:
            # Bullish patterns belong at SUPPORT, bearish at RESISTANCE
            # Skip mismatches — they're noise, not signals
            if pattern_bias == 'bullish' and level['type'] == 'resistance':
                continue
            if pattern_bias == 'bearish' and level['type'] == 'support':
                continue

            # ── SCORE THE SIGNAL ──
            score = 0
            reasons = []

            # Pattern quality (20-30 points)
            if pattern in ['bullish_engulfing', 'bearish_engulfing']:
                score += 30
                reasons.append(f"{pattern.replace('_', ' ').title()} pattern")
            elif pattern in ['hammer', 'shooting_star']:
                score += 25
                reasons.append(f"{pattern.replace('_', ' ').title()} pattern")
            elif pattern in ['pin_bar_bull', 'pin_bar_bear']:
                score += 25
                reasons.append("Pin bar rejection")
            elif pattern == 'doji':
                score += 15
                reasons.append("Doji indecision")

            # Level strength (10-25 points)
            level_strength = level['strength']
            if level_strength >= 80:
                score += 25
                reasons.append(f"Very strong level (tested {level['touches']}x)")
            elif level_strength >= 60:
                score += 20
                reasons.append(f"Strong level (tested {level['touches']}x)")
            elif level_strength >= 40:
                score += 15
                reasons.append(f"Moderate level (tested {level['touches']}x)")
            else:
                score += 10
                reasons.append(f"Weak level (tested {level['touches']}x)")

            # Trend alignment (15-25 points)
            trend_aligned = False
            if pattern_bias == 'bullish' and daily_trend in ['BULLISH', 'WEAK_BULLISH'] and level['type'] == 'support':
                score += 25
                reasons.append("Aligned with daily uptrend at support")
                trend_aligned = True
            elif pattern_bias == 'bearish' and daily_trend in ['BEARISH', 'WEAK_BEARISH'] and level['type'] == 'resistance':
                score += 25
                reasons.append("Aligned with daily downtrend at resistance")
                trend_aligned = True
            elif pattern_bias == 'bullish' and level['type'] == 'support':
                score += 10
                reasons.append("At support (but trend not confirmed)")
            elif pattern_bias == 'bearish' and level['type'] == 'resistance':
                score += 10
                reasons.append("At resistance (but trend not confirmed)")
            elif pattern_bias == 'neutral':  # doji
                score += 5
                reasons.append("Indecision at key level")

            # Volume confirmation (0-25 points)
            vol_score = compute_volume_score(entry_df, idx)
            score += vol_score
            if vol_score >= 15:
                reasons.append("High volume confirmation")
            elif vol_score >= 5:
                reasons.append("Normal volume")

            # Age penalty — older signals score lower
            bars_ago = scan_range + i  # i is negative, so this gives bars from end
            age_penalty = min(bars_ago * 1.5, 20)  # Max 20 point penalty
            score -= int(age_penalty)

            # Only generate signal if score >= 50
            if score < 50:
                continue

            # Determine direction
            if pattern_bias == 'bullish':
                direction = 'BUY'
            elif pattern_bias == 'bearish':
                direction = 'SELL'
            else:
                # Doji — use trend context
                if daily_trend in ['BULLISH', 'WEAK_BULLISH'] and level['type'] == 'support':
                    direction = 'BUY'
                elif daily_trend in ['BEARISH', 'WEAK_BEARISH'] and level['type'] == 'resistance':
                    direction = 'SELL'
                else:
                    continue  # Skip doji without trend confirmation

            # Compute entry, stop loss, take profit
            # Use ATR from the entry timeframe but ensure sensible distances
            atr_raw = (entry_df['High'] - entry_df['Low']).tail(14).mean()
            # Scale ATR to a reasonable trade distance (min 0.3% of price)
            min_distance = bar_price * 0.003  # 0.3% minimum risk
            atr = max(atr_raw * 2, min_distance, bar_price * 0.005)  # At least 0.5% of price

            if direction == 'BUY':
                entry = round(bar_price, 2)
                # SL below the pattern low and the level, whichever is lower
                sl_anchor = min(bar_low, level_price)
                stop_loss = round(sl_anchor - atr * 0.5, 2)
                # Ensure SL is always below entry
                if stop_loss >= entry:
                    stop_loss = round(entry - atr, 2)
                risk = round(entry - stop_loss, 2)
                if risk <= 0:
                    continue  # Skip signal — no room for stop loss
                take_profit = round(entry + risk * 2, 2)  # 1:2 R:R
                reward = round(take_profit - entry, 2)
            elif direction == 'SELL':
                entry = round(bar_price, 2)
                # SL above the pattern high and the level, whichever is higher
                sl_anchor = max(bar_high, level_price)
                stop_loss = round(sl_anchor + atr * 0.5, 2)
                # Ensure SL is always above entry
                if stop_loss <= entry:
                    stop_loss = round(entry + atr, 2)
                risk = round(stop_loss - entry, 2)
                if risk <= 0:
                    continue  # Skip signal — no room for stop loss
                take_profit = round(entry - risk * 2, 2)  # 1:2 R:R
                reward = round(entry - take_profit, 2)
            else:
                continue  # Should not reach here

            if risk <= 0 or reward <= 0:
                continue  # Skip signals with invalid risk/reward
            rr_ratio = round(reward / risk, 1)

            # Confidence label
            if score >= 80:
                confidence = "HIGH"
            elif score >= 65:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"

            signal = {
                'time': bar_time,
                'direction': direction,
                'pattern': pattern,
                'pattern_name': pattern.replace('_', ' ').title(),
                'price_at_signal': round(bar_price, 2),
                'level_price': level_price,
                'level_type': level['type'],
                'level_touches': level['touches'],
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk': risk,
                'reward': reward,
                'rr_ratio': rr_ratio,
                'score': min(score, 100),
                'confidence': confidence,
                'daily_trend': daily_trend,
                'trend_aligned': trend_aligned,
                'volume_confirmed': vol_score >= 15,
                'reasons': reasons,
                'timeframe': entry_tf_key,
                'session': _get_session_label(bar_time),
            }
            signals.append(signal)

    # Deduplicate — if multiple patterns at same level within 4 bars, keep highest score
    if signals:
        signals.sort(key=lambda x: x['score'], reverse=True)
        seen_times = set()
        unique = []
        for s in signals:
            time_key = s['time'].strftime('%Y-%m-%d %H') if hasattr(s['time'], 'strftime') else str(s['time'])[:13]
            if time_key not in seen_times:
                seen_times.add(time_key)
                unique.append(s)
        signals = unique[:max_signals]

    return signals


def format_signal_for_beginner(signal):
    """Format a signal into plain English for a beginner."""
    if signal['direction'] == 'BUY':
        action = "Consider BUYING"
        emoji = "🟢"
        sl_text = f"If it drops below ${signal['stop_loss']:,.2f}, exit (your risk: ${signal['risk']:,.2f})"
        tp_text = f"Target: ${signal['take_profit']:,.2f} (potential gain: ${signal['reward']:,.2f})"
    elif signal['direction'] == 'SELL':
        action = "Consider SELLING"
        emoji = "🔴"
        sl_text = f"If it rises above ${signal['stop_loss']:,.2f}, exit (your risk: ${signal['risk']:,.2f})"
        tp_text = f"Target: ${signal['take_profit']:,.2f} (potential gain: ${signal['reward']:,.2f})"
    else:
        return {
            'emoji': '🟡',
            'headline': 'WAIT — No clear entry right now',
            'explanation': f"A {signal['pattern_name']} candle appeared at ${signal['level_price']:,.2f}, but the trend isn't confirming a direction. Stay patient.",
            'entry': None, 'sl': None, 'tp': None, 'rr': None,
        }

    # Build beginner explanation
    level_word = "support" if signal['level_type'] == 'support' else "resistance"
    explanation = (
        f"Gold hit a {level_word} zone at ${signal['level_price']:,.2f} that has held "
        f"{signal['level_touches']} time{'s' if signal['level_touches'] > 1 else ''} before, "
        f"and just printed a {signal['pattern_name']} candle on the {signal['timeframe']} chart."
    )

    if signal['trend_aligned']:
        explanation += f" The daily trend is {signal['daily_trend'].lower().replace('_', ' ')}, which supports this trade."

    if signal['volume_confirmed']:
        explanation += " Volume is above average, confirming real interest at this level."

    return {
        'emoji': emoji,
        'headline': f"{action} at ${signal['entry']:,.2f}",
        'confidence': signal['confidence'],
        'score': signal['score'],
        'explanation': explanation,
        'entry': f"${signal['entry']:,.2f}",
        'sl': sl_text,
        'tp': tp_text,
        'rr': f"1:{signal['rr_ratio']}",
        'reasons': signal['reasons'],
    }
