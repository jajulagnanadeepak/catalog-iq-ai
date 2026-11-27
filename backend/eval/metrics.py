"""Ranking metrics. Pure functions, no dependencies."""

from __future__ import annotations

import math


def dcg(gains: list[float]) -> float:
    return sum((2.0 ** g - 1.0) / math.log2(i + 2) for i, g in enumerate(gains))


def ideal_gains(gain_hist: dict[str, int], k: int) -> list[float]:
    ideal: list[float] = []
    for gain, count in sorted(((float(g), c) for g, c in gain_hist.items()), reverse=True):
        ideal.extend([gain] * min(count, k - len(ideal)))
        if len(ideal) >= k:
            break
    return ideal


def ndcg_at_k(gains: list[float], gain_hist: dict[str, int], k: int) -> float:
    ideal = dcg(ideal_gains(gain_hist, k))
    if ideal == 0:
        return 0.0
    return dcg(gains[:k]) / ideal


def mrr(relevant_flags: list[bool]) -> float:
    for i, ok in enumerate(relevant_flags, start=1):
        if ok:
            return 1.0 / i
    return 0.0


def precision_at_k(relevant_flags: list[bool], k: int) -> float:
    """Missing results count as non-relevant (a short list is penalised)."""
    return sum(1 for ok in relevant_flags[:k] if ok) / k


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * pct / 100.0
    low, high = math.floor(rank), math.ceil(rank)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
