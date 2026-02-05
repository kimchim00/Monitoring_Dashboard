"""
Helper Functions

This module contains utility functions used throughout the application.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dateutil import parser as dtparser


def parse_ts(x: Any) -> Optional[datetime]:
    """Parse timestamp from various formats"""
    if not x:
        return None
    try:
        dt = dtparser.isoparse(str(x))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def safe_int(x: Any) -> Optional[int]:
    """Safely convert to int"""
    try:
        return int(x) if x is not None else None
    except Exception:
        return None


def safe_float(x: Any) -> Optional[float]:
    """Safely convert to float"""
    try:
        return float(x) if x is not None else None
    except Exception:
        return None


def get_nested(d: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    """Safely read nested dict keys"""
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def quantile(sorted_vals: List[float], q: float) -> float:
    """Calculate percentile from sorted values"""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if n == 1:
        return float(sorted_vals[0])
    pos = (n - 1) * q
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return float(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac)
