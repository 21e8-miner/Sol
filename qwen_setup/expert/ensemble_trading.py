#!/usr/bin/env python3
"""
Ensemble Trading with Multiple LLM Queries

Regime ensemble: multiple Qwen queries with different "personas"
to label regime + chop/event risk.

Returns a list of LLMSingleLabel that trading_core.aggregate_llm_labels
can consume.
"""

import json
from typing import List
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from client import QwenClient
except ImportError:
    print("Warning: client module not found. Using mock.")
    # Create minimal mock for testing
    class QwenClient:
        def __init__(self, base_url="http://localhost:8000"):
            self.base_url = base_url

        def complete(self, prompt, max_tokens=256, temperature=0.7):
            # Mock response
            return '{"regime": "trending_up", "chop_risk": "low", "event_risk": "medium", "confidence": 7}'

try:
    from trading_core import LLMSingleLabel
except ImportError:
    print("Warning: trading_core not found. Using stub.")
    # Stub for testing
    class LLMSingleLabel:
        def __init__(self, regime="undefined", chop_risk="high", event_risk="medium", confidence=5):
            self.regime = regime
            self.chop_risk = chop_risk
            self.event_risk = event_risk
            self.confidence = confidence


class RegimeEnsembleTrader:
    """
    Ensemble classifier for market regime using multiple LLM queries.

    Uses different "personalities" to get diverse perspectives,
    then aggregates via majority voting.
    """

    def __init__(self, base_client: QwenClient, num_models: int = 5):
        self.base_client = base_client
        self.num_models = num_models
        self.personalities = [
            "aggressive day trader",
            "conservative swing trader",
            "quantitative analyst",
            "momentum trader",
            "macro risk manager",
        ]

    def classify_regime(self, prompt: str) -> List[LLMSingleLabel]:
        """
        Classify market regime using ensemble of LLM queries.

        Args:
            prompt: Formatted prompt from build_regime_prompt()

        Returns:
            List of LLMSingleLabel objects (one per personality)
        """
        labels: List[LLMSingleLabel] = []

        for i in range(self.num_models):
            persona = self.personalities[i % len(self.personalities)]
            persona_prompt = (
                f"You are a {persona}.\n"
                f"Classify the regime and risks.\n\n" + prompt
            )

            try:
                raw = self.base_client.complete(
                    persona_prompt,
                    max_tokens=180,
                    temperature=0.3,
                )

                # Try to extract JSON
                j_start = raw.find("{")
                j_end = raw.rfind("}") + 1
                if j_start == -1 or j_end <= j_start:
                    raise ValueError("no-json")

                obj = json.loads(raw[j_start:j_end])
                labels.append(
                    LLMSingleLabel(
                        regime=obj.get("regime", "undefined"),
                        chop_risk=obj.get("chop_risk", "high"),
                        event_risk=obj.get("event_risk", "medium"),
                        confidence=int(obj.get("confidence", 5)),
                    )
                )
            except Exception as e:
                # Fallback: treat as undefined, low confidence
                print(f"Warning: LLM parsing failed for {persona}: {e}")
                labels.append(
                    LLMSingleLabel(
                        regime="undefined",
                        chop_risk="high",
                        event_risk="medium",
                        confidence=3,
                    )
                )

        return labels


if __name__ == "__main__":
    print("👥 Testing RegimeEnsembleTrader...")

    # Use mock client
    client = QwenClient()
    trader = RegimeEnsembleTrader(client, num_models=5)

    dummy_prompt = """
DATA: regime=trend_up rv=medium
PRICES: c:90000 r:300 v:1000000 c:91000 r:350 v:1100000 c:92000 r:320 v:1200000

LABELS:
"""

    labels = trader.classify_regime(dummy_prompt)
    print(f"\nGenerated {len(labels)} labels:")
    for i, label in enumerate(labels):
        print(f"  {i+1}. regime={label.regime}, chop={label.chop_risk}, "
              f"event={label.event_risk}, conf={label.confidence}")

    # Test aggregation
    try:
        from trading_core import aggregate_llm_labels
        agg = aggregate_llm_labels(labels)
        print(f"\nAggregated:")
        print(f"  Regime: {agg.regime} (agreement: {agg.regime_agreement:.1%})")
        print(f"  Chop Risk: {agg.chop_risk} (agreement: {agg.chop_agreement:.1%})")
        print(f"  Event Risk: {agg.event_risk}")
        print(f"  Avg Confidence: {agg.avg_confidence:.1f}/10")
    except ImportError:
        print("\nSkipping aggregation test (trading_core not available)")

    print("\n✅ RegimeEnsembleTrader test complete!")
