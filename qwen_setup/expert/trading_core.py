#!/usr/bin/env python3
"""
trading_core.py

Deterministic signal engine + LLM gating for BTCUSDT on 1h timeframe.
Designed for Qwen2-1.5B on CPU and zero-cost data (Binance).

This module is PURE LOGIC: no network, no Qwen client inside.
Wire it from trading_orchestrator.py using your existing QwenClient.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Literal, Optional, Any
import math

# ---------- Types ----------

SignalType = Literal["long_trend", "flat"]

RegimeLabel = Literal[
    "trending_up",
    "trending_down",
    "range_choppy",
    "blowoff_top",
    "crash_down",
    "undefined",
]

RiskLevel = Literal["low", "medium", "high"]

@dataclass
class LLMSingleLabel:
    regime: RegimeLabel
    chop_risk: RiskLevel
    event_risk: RiskLevel
    confidence: int  # 1–10

@dataclass
class LLMLabels:
    regime: RegimeLabel
    chop_risk: RiskLevel
    event_risk: RiskLevel
    avg_confidence: float
    regime_agreement: float
    chop_agreement: float

# ---------- Basic indicators (no external libs) ----------

def ema(values: List[float], length: int) -> List[float]:
    """Exponential Moving Average"""
    if len(values) == 0:
        return []
    if length <= 1:
        return values[:]
    k = 2.0 / (length + 1.0)
    out: List[float] = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1.0 - k))
    return out

def true_range(
    highs: List[float],
    lows: List[float],
    closes: List[float],
) -> List[float]:
    """True Range for ATR calculation"""
    tr: List[float] = []
    for i in range(len(highs)):
        if i == 0:
            tr.append(highs[i] - lows[i])
        else:
            tr.append(
                max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1]),
                )
            )
    return tr

def atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    length: int,
) -> List[float]:
    """Average True Range"""
    tr = true_range(highs, lows, closes)
    return ema(tr, length)

def rsi(values: List[float], length: int) -> List[float]:
    """Relative Strength Index"""
    if len(values) < length + 1:
        return [50.0] * len(values)

    gains: List[float] = []
    losses: List[float] = []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))

    avg_gain = sum(gains[:length]) / length
    avg_loss = sum(losses[:length]) / length
    rsis: List[float] = [50.0] * length

    for i in range(length, len(gains)):
        avg_gain = (avg_gain * (length - 1) + gains[i]) / length
        avg_loss = (avg_loss * (length - 1) + losses[i]) / length
        if avg_loss == 0:
            rs = math.inf
            rsi_val = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_val = 100.0 - (100.0 / (1.0 + rs))
        rsis.append(rsi_val)

    # Pad to same length as values
    while len(rsis) < len(values):
        rsis.insert(0, 50.0)

    return rsis

# ---------- Deterministic signal engine ----------

def generate_signal(
    ohlcv: List[Dict[str, float]],
    symbol: str,
    timeframe: str = "1h",
) -> tuple[SignalType, Dict[str, Any]]:
    """
    Generate trading signal from OHLCV data.

    Args:
        ohlcv: List of dicts with keys: "t", "o", "h", "l", "c", "v"
        symbol: Trading symbol (e.g., "BTCUSDT")
        timeframe: Timeframe (e.g., "1h")

    Returns:
        (signal_type, metadata)
    """
    if len(ohlcv) < 220:
        return "flat", {"reason": "not_enough_data"}

    closes = [c["c"] for c in ohlcv]
    highs = [c["h"] for c in ohlcv]
    lows = [c["l"] for c in ohlcv]

    close = closes[-1]
    ema_fast_series = ema(closes, 50)
    ema_slow_series = ema(closes, 200)
    atr_series = atr(highs, lows, closes, 24)
    rsi_series = rsi(closes, 14)

    ema_fast_val = ema_fast_series[-1]
    ema_slow_val = ema_slow_series[-1]
    atr_val = atr_series[-1]
    rsi_val = rsi_series[-1]

    if atr_val <= 0:
        return "flat", {"reason": "atr_zero"}

    trend_strength = (close - ema_slow_val) / atr_val
    vol_regime = atr_val / close

    # Determine numeric regime
    if ema_fast_val > ema_slow_val and trend_strength > 1.0:
        numeric_regime = "trend_up"
    elif ema_fast_val < ema_slow_val and trend_strength < -1.0:
        numeric_regime = "trend_down"
    else:
        numeric_regime = "range"

    # Long-only trend-following entry
    if numeric_regime == "trend_up":
        last3 = closes[-3:]
        three_bar_up = (last3[0] < last3[1] < last3[2])

        if (
            three_bar_up
            and close > ema_fast_val
            and 0.01 <= vol_regime <= 0.06
            and 35.0 <= rsi_val <= 70.0
        ):
            meta = {
                "symbol": symbol,
                "timeframe": timeframe,
                "numeric_regime": numeric_regime,
                "ema_fast": ema_fast_val,
                "ema_slow": ema_slow_val,
                "atr": atr_val,
                "rsi": rsi_val,
                "trend_strength": trend_strength,
                "vol_regime": vol_regime,
                "close": close,
            }
            return "long_trend", meta

    return "flat", {
        "symbol": symbol,
        "timeframe": timeframe,
        "numeric_regime": numeric_regime,
        "ema_fast": ema_fast_val,
        "ema_slow": ema_slow_val,
        "atr": atr_val,
        "rsi": rsi_val,
        "trend_strength": trend_strength,
        "vol_regime": vol_regime,
        "close": close,
        "reason": "no_entry_match",
    }

# ---------- LLM prompt + aggregation helpers ----------

def compress_ohlcv_for_llm(
    ohlcv: List[Dict[str, float]],
    max_candles: int = 48,
) -> str:
    """
    Compress last max_candles into a short string:
    "c:92000 r:400 v:1.2B c:92100 r:350 v:1.1B ..."
    """
    tail = ohlcv[-max_candles:]
    parts: List[str] = []
    for c in tail:
        price = c["c"]
        rng = c["h"] - c["l"]
        vol = c["v"]
        vol_display = f"{vol:.0f}"
        parts.append(f"c:{price:.0f} r:{rng:.0f} v:{vol_display}")
    return " ".join(parts)

def build_regime_prompt(
    symbol: str,
    numeric_regime: str,
    vol_regime: float,
    compressed_data: str,
) -> str:
    """
    Few-shot prompt for Qwen2-1.5B to classify regime + risks.
    """
    rv_bucket = (
        "low" if vol_regime < 0.01
        else "medium" if vol_regime < 0.04
        else "high"
    )

    prompt = f"""You are a conservative crypto regime classifier.

You see hourly candles for {symbol}.
Each candle has:
- c = close price
- r = high-low range
- v = volume (unitless, only relative size matters)

You must output ONE JSON object with keys:
- "regime": one of ["trending_up","trending_down","range_choppy","blowoff_top","crash_down","undefined"]
- "chop_risk": one of ["low","medium","high"]
- "event_risk": one of ["low","medium","high"]
- "confidence": integer 1–10

Examples:
DATA: regime=trend_up rv=medium
PRICES: c:40000 r:300 v:1000000 c:40500 r:350 v:1100000 c:41000 r:320 v:1200000
LABELS: {{"regime":"trending_up","chop_risk":"low","event_risk":"medium","confidence":7}}

DATA: regime=range rv=high
PRICES: c:45000 r:800 v:1500000 c:44950 r:900 v:1600000 c:45020 r:850 v:1700000
LABELS: {{"regime":"range_choppy","chop_risk":"high","event_risk":"low","confidence":8}}

Now classify the current situation.

DATA: regime={numeric_regime} rv={rv_bucket}
PRICES: {compressed_data}

LABELS:
"""
    return prompt

def aggregate_llm_labels(
    labels: List[LLMSingleLabel],
) -> LLMLabels:
    """Aggregate multiple LLM labels into consensus"""
    if not labels:
        return LLMLabels(
            regime="undefined",
            chop_risk="high",
            event_risk="high",
            avg_confidence=0.0,
            regime_agreement=0.0,
            chop_agreement=0.0,
        )

    def majority(xs: List[str]) -> tuple[str, float]:
        from collections import Counter
        c = Counter(xs)
        val, cnt = c.most_common(1)[0]
        return val, cnt / len(xs)

    def median_level(xs: List[RiskLevel]) -> RiskLevel:
        mapping = {"low": 1, "medium": 2, "high": 3}
        inv = {1: "low", 2: "medium", 3: "high"}
        nums = sorted(mapping[x] for x in xs)
        mid = nums[len(nums) // 2]
        return inv[mid]

    regimes = [l.regime for l in labels]
    chops = [l.chop_risk for l in labels]
    events = [l.event_risk for l in labels]
    confs = [l.confidence for l in labels]

    maj_regime, regime_agree = majority(regimes)
    maj_chop, chop_agree = majority(chops)
    med_event = median_level(events)
    avg_conf = sum(confs) / len(confs)

    return LLMLabels(
        regime=maj_regime,
        chop_risk=maj_chop,
        event_risk=med_event,
        avg_confidence=avg_conf,
        regime_agreement=regime_agree,
        chop_agreement=chop_agree,
    )

# ---------- Policy mapper (numeric core + LLM overlay) ----------

def policy_mapper(
    signal: SignalType,
    signal_meta: Dict[str, Any],
    llm_labels: LLMLabels,
    equity: float,
    base_risk_pct: float = 0.0075,  # 0.75% of equity
) -> Optional[Dict[str, Any]]:
    """
    Map (numeric signal + LLM regime labels) → final trade object.

    Args:
        signal: Signal type from generate_signal
        signal_meta: Metadata from generate_signal
        llm_labels: Aggregated LLM labels
        equity: Current equity for position sizing
        base_risk_pct: Base risk percentage per trade

    Returns:
        Trade order dict or None if trade is gated
    """

    if signal == "flat":
        return None

    # Gating on label quality
    if llm_labels.avg_confidence < 6.0:
        return None
    if llm_labels.regime_agreement < 0.6:
        return None

    # Hard event veto
    if llm_labels.event_risk == "high":
        return None

    # Signal ↔ regime alignment
    if signal == "long_trend":
        if not (
            llm_labels.regime in ("trending_up", "blowoff_top")
            and llm_labels.chop_risk != "high"
        ):
            return None
    else:
        return None

    # Risk multipliers
    event_mult_map = {"low": 1.0, "medium": 0.5, "high": 0.25}
    event_mult = event_mult_map[llm_labels.event_risk]
    conf_mult = 0.5 + (llm_labels.avg_confidence / 20.0)  # 0.5–1.0

    risk_frac = base_risk_pct * event_mult * conf_mult
    if risk_frac < 0.001:  # < 0.1% equity
        return None

    atr_val = float(signal_meta["atr"])
    close = float(signal_meta["close"])
    if atr_val <= 0:
        return None

    # Stops & targets
    stop_loss = close - 1.5 * atr_val
    # Reward ≈ 3R
    take_profit = close + 3.0 * (close - stop_loss)

    risk_usd = equity * risk_frac
    stop_dist = close - stop_loss
    if stop_dist <= 0:
        return None
    qty = risk_usd / stop_dist

    order = {
        "action": "buy",
        "symbol": signal_meta.get("symbol", "BTCUSDT"),
        "qty": qty,
        "entry_price": close,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk_usd": risk_usd,
        "risk_frac": risk_frac,
        "max_holding_bars": 24 * 7,  # 7 days on 1h
        "reason": (
            f"long_trend: numeric_regime={signal_meta.get('numeric_regime')}, "
            f"llm_regime={llm_labels.regime}, "
            f"conf={llm_labels.avg_confidence:.1f}"
        ),
    }
    return order


if __name__ == "__main__":
    # Test with dummy data
    print("Testing trading_core.py...")

    # Generate 250 candles of dummy data
    import random
    base_price = 45000.0
    ohlcv = []

    for i in range(250):
        base_price += random.uniform(-100, 150)  # Uptrend bias
        high = base_price + random.uniform(50, 200)
        low = base_price - random.uniform(50, 150)
        close = base_price + random.uniform(-50, 50)
        volume = random.uniform(1_000_000, 3_000_000)

        ohlcv.append({
            "t": i * 3600000,  # 1h intervals
            "o": base_price,
            "h": high,
            "l": low,
            "c": close,
            "v": volume,
        })

    signal, meta = generate_signal(ohlcv, "BTCUSDT", "1h")
    print(f"\nSignal: {signal}")
    print(f"Metadata: {meta}")

    if signal != "flat":
        compressed = compress_ohlcv_for_llm(ohlcv)
        print(f"\nCompressed data length: {len(compressed)} chars")

        prompt = build_regime_prompt(
            "BTCUSDT",
            meta["numeric_regime"],
            meta["vol_regime"],
            compressed[:200] + "..."  # Show first 200 chars
        )
        print(f"\nPrompt preview:\n{prompt[:500]}...")

    print("\n✅ trading_core.py test complete!")
