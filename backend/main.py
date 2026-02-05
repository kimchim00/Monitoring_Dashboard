from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from dateutil import parser as dtparser
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

API_PREFIX = "/api"
LOG_FILE_PATH = os.getenv("LOG_FILE", "./data/monitoring.jsonl")  # stored as JSONL

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def iter_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    """Reads JSONL (one JSON object per line). Invalid lines are skipped."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue
    except FileNotFoundError:
        return


def parse_ts(x: Any) -> Optional[datetime]:
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
    try:
        if x is None:
            return None
        return int(x)
    except Exception:
        return None


def safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def quantile(sorted_vals: List[float], q: float) -> float:
    """Linear percentile on a sorted list (numpy-like)."""
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


def get_nested(d: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    """Safely read nested keys, e.g. get_nested(d, ("http", "method"))"""
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


# ──────────────────────────────────────────────────────────────────────────────
# Domain model + normalization
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Row:
    timestamp: datetime
    level: str
    event_type: str
    method: Optional[str]
    path: Optional[str]
    status_code: Optional[int]
    duration_ms: Optional[float]
    user_id: Optional[int]
    is_authenticated: Optional[bool]
    error_type: Optional[str]
    error_message: Optional[str]


def normalize(d: Dict[str, Any]) -> Optional[Row]:
    """
    Normalize raw log dict to Row.
    Supports common variants/nesting.
    """
    ts = parse_ts(d.get("timestamp") or d.get("time") or get_nested(d, ("meta", "timestamp")))
    if ts is None:
        return None

    method = d.get("method") or get_nested(d, ("request", "method")) or get_nested(d, ("http", "method"))
    path = d.get("path") or get_nested(d, ("request", "path")) or get_nested(d, ("http", "path")) or d.get("endpoint")

    status_raw = d.get("status_code")
    if status_raw is None:
        status_raw = d.get("status") or get_nested(d, ("response", "status_code")) or get_nested(d, ("http", "status"))

    dur_raw = d.get("duration_ms")
    if dur_raw is None:
        dur_raw = d.get("latency_ms") or d.get("response_time_ms") or get_nested(d, ("timing", "duration_ms"))

    ia = d.get("is_authenticated")
    if ia is None:
        ia = d.get("authenticated") or get_nested(d, ("auth", "is_authenticated"))

    if isinstance(ia, bool):
        is_auth = ia
    elif ia is None:
        is_auth = None
    else:
        s = str(ia).strip().lower()
        if s in ("true", "1", "yes"):
            is_auth = True
        elif s in ("false", "0", "no"):
            is_auth = False
        else:
            is_auth = None

    return Row(
        timestamp=ts,
        level=str(d.get("level") or d.get("severity") or ""),
        event_type=str(d.get("event_type") or d.get("type") or ""),
        method=(str(method) if method is not None else None),
        path=(str(path) if path is not None else None),
        status_code=safe_int(status_raw),
        duration_ms=safe_float(dur_raw),
        user_id=safe_int(d.get("user_id") or get_nested(d, ("user", "id"))),
        is_authenticated=is_auth,
        error_type=(str(d.get("error_type")) if d.get("error_type") is not None else None),
        error_message=(str(d.get("error_message")) if d.get("error_message") is not None else None),
    )


def is_request(r: Row) -> bool:
    """Request-like entry for dashboard: must have path + method."""
    return bool(r.path and r.method)


def is_error_row(r: Row) -> bool:
    """Errors rule: level=='ERROR' OR status_code>=400"""
    if r.status_code is not None and r.status_code >= 400:
        return True
    if (r.level or "").upper() == "ERROR":
        return True
    return False


def get_latest_timestamp() -> Optional[datetime]:
    """
    IMPORTANT FIX:
    Use latest timestamp in the log file as the "now" anchor,
    so dashboards work even if logs are historical (e.g., 2025) while system time is 2026.
    """
    latest: Optional[datetime] = None
    for d in iter_jsonl(LOG_FILE_PATH):
        r = normalize(d)
        if not r:
            continue
        if latest is None or r.timestamp > latest:
            latest = r.timestamp
    return latest


def load_window(minutes: int) -> List[Row]:
    """
    Window is anchored to latest log timestamp (not system clock).
    Returns rows where start <= timestamp <= latest.
    """
    latest = get_latest_timestamp()
    if latest is None:
        return []

    start = latest - timedelta(minutes=minutes)

    out: List[Row] = []
    for d in iter_jsonl(LOG_FILE_PATH):
        r = normalize(d)
        if r and start <= r.timestamp <= latest:
            out.append(r)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Monitoring (Upload Logs → Dashboard APIs)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev OK; lock down in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Upload endpoint (robust)
# ──────────────────────────────────────────────────────────────────────────────

@app.post(f"{API_PREFIX}/upload-log")
async def upload_log_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Accepts:
      - JSONL
      - JSON array
      - Single JSON object
      - JSON object containing list under keys: logs/events/entries/data/items
      - Pretty/multiline JSON
    Stores as JSONL (overwrite).
    """
    ensure_parent_dir(LOG_FILE_PATH)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    text = content.decode("utf-8", errors="ignore").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty file")

    def write_jsonl(items: List[dict]) -> int:
        written = 0
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            for it in items:
                if isinstance(it, dict):
                    f.write(json.dumps(it, ensure_ascii=False) + "\n")
                    written += 1
        return written

    # Try parse whole file as JSON first (handles multiline JSON)
    try:
        obj = json.loads(text)

        if isinstance(obj, list):
            written = write_jsonl(obj)
            return {"status": "ok", "saved_as": "jsonl", "mode": "json_array", "written": written, "path": os.path.abspath(LOG_FILE_PATH)}

        if isinstance(obj, dict):
            for key in ("logs", "events", "entries", "data", "items"):
                if key in obj and isinstance(obj[key], list):
                    written = write_jsonl(obj[key])
                    return {"status": "ok", "saved_as": "jsonl", "mode": f"json_object.{key}_list", "written": written, "path": os.path.abspath(LOG_FILE_PATH)}

            written = write_jsonl([obj])
            return {"status": "ok", "saved_as": "jsonl", "mode": "single_json_object", "written": written, "path": os.path.abspath(LOG_FILE_PATH)}
    except Exception:
        pass

    # Fallback: treat as JSONL
    with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(text + ("\n" if not text.endswith("\n") else ""))

    line_count = sum(1 for ln in text.splitlines() if ln.strip())
    return {"status": "ok", "saved_as": "jsonl", "mode": "raw_jsonl_fallback", "written": line_count, "path": os.path.abspath(LOG_FILE_PATH)}


# ──────────────────────────────────────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────────────────────────────────────

@app.get(f"{API_PREFIX}/health")
def health() -> Dict[str, Any]:
    exists = os.path.exists(LOG_FILE_PATH)
    size_bytes = os.path.getsize(LOG_FILE_PATH) if exists else 0
    total_lines = 0
    if exists:
        try:
            with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
                for _ in f:
                    total_lines += 1
        except Exception:
            total_lines = 0

    latest = get_latest_timestamp()
    return {
        "status": "ok",
        "log_file": {
            "exists": exists,
            "path": os.path.abspath(LOG_FILE_PATH),
            "size_bytes": size_bytes,
            "total_lines": total_lines,
        },
        "latest_timestamp": (latest.isoformat() if latest else None),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Metrics + Charts (per screenshots)
# ──────────────────────────────────────────────────────────────────────────────

@app.get(f"{API_PREFIX}/metrics")
def metrics(minutes: int = Query(60, ge=1, le=60 * 24 * 14)) -> Dict[str, Any]:
    rows = load_window(minutes)
    reqs = [r for r in rows if is_request(r)]

    total_requests = len(reqs)

    durations = sorted([r.duration_ms for r in reqs if r.duration_ms is not None])
    avg_response_time = (sum(durations) / len(durations)) if durations else 0.0

    # Error rate = COUNT(status_code >= 400) / COUNT(total_requests) * 100
    error_count = sum(1 for r in reqs if (r.status_code is not None and r.status_code >= 400))
    error_rate = (error_count / total_requests * 100.0) if total_requests else 0.0

    p50 = quantile(durations, 0.50) if durations else 0.0
    p95 = quantile(durations, 0.95) if durations else 0.0
    p99 = quantile(durations, 0.99) if durations else 0.0

    # Charts: group-by counts
    requests_by_status: Dict[str, int] = {}
    requests_by_method: Dict[str, int] = {}

    # Users
    user_ids = set()
    authenticated_requests = 0

    for r in reqs:
        if r.status_code is not None:
            k = str(r.status_code)
            requests_by_status[k] = requests_by_status.get(k, 0) + 1

        if r.method:
            requests_by_method[r.method] = requests_by_method.get(r.method, 0) + 1

        if r.user_id is not None:
            user_ids.add(r.user_id)

        if r.is_authenticated is True:
            authenticated_requests += 1

    return {
        "metrics": {
            "total_requests": total_requests,
            "error_count": error_count,
            "error_rate": error_rate,
            "avg_response_time": avg_response_time,
            "p50_response_time": p50,
            "p95_response_time": p95,
            "p99_response_time": p99,
            "requests_by_status": requests_by_status,
            "requests_by_method": requests_by_method,
            "unique_users": len(user_ids),
            "authenticated_requests": authenticated_requests,
        }
    }


# ──────────────────────────────────────────────────────────────────────────────
# API Performance (per screenshots) + sort options
# ──────────────────────────────────────────────────────────────────────────────

@app.get(f"{API_PREFIX}/endpoints")
def endpoints(
    minutes: int = Query(60, ge=1, le=60 * 24 * 14),
    limit: int = Query(10, ge=1, le=200),
    sort_by: str = Query("count"),  # "count" or "p95"
    order: str = Query("desc"),     # "asc" or "desc"
) -> Dict[str, Any]:
    rows = load_window(minutes)
    reqs = [r for r in rows if is_request(r) and r.path]

    buckets: Dict[str, List[Row]] = {}
    for r in reqs:
        buckets.setdefault(r.path, []).append(r)

    out: List[Dict[str, Any]] = []
    for path, items in buckets.items():
        count = len(items)
        errors = sum(1 for r in items if (r.status_code is not None and r.status_code >= 400))

        durs = sorted([r.duration_ms for r in items if r.duration_ms is not None])
        avg = (sum(durs) / len(durs)) if durs else 0.0
        p95 = quantile(durs, 0.95) if durs else 0.0

        error_rate = (errors / count * 100.0) if count else 0.0

        out.append(
            {
                "path": path,
                "count": count,
                "errors": errors,
                "avg_response_time": avg,
                "p95_response_time": p95,
                "error_rate": error_rate,
            }
        )

    reverse = (order.lower() != "asc")
    key_fn = (lambda x: x["p95_response_time"]) if sort_by.lower() == "p95" else (lambda x: x["count"])
    out.sort(key=key_fn, reverse=reverse)

    return {"endpoints": out[:limit]}


# ──────────────────────────────────────────────────────────────────────────────
# Errors page
# ──────────────────────────────────────────────────────────────────────────────

@app.get(f"{API_PREFIX}/errors")
def errors(limit: int = Query(20, ge=1, le=200)) -> Dict[str, Any]:
    rows: List[Row] = []
    for d in iter_jsonl(LOG_FILE_PATH):
        r = normalize(d)
        if r:
            rows.append(r)

    err_rows = [r for r in rows if is_error_row(r)]
    err_rows.sort(key=lambda r: r.timestamp, reverse=True)
    err_rows = err_rows[:limit]

    return {
        "errors": [
            {
                "timestamp": r.timestamp.isoformat(),
                "level": r.level,
                "method": r.method,
                "path": r.path,
                "status_code": r.status_code,
                "error_type": r.error_type,
                "error_message": r.error_message,
                "user_id": r.user_id,
            }
            for r in err_rows
        ]
    }


# ──────────────────────────────────────────────────────────────────────────────
# Traffic analysis (per screenshots)
# ──────────────────────────────────────────────────────────────────────────────

@app.get(f"{API_PREFIX}/traffic")
def traffic(minutes: int = Query(1440, ge=1, le=60 * 24 * 14)) -> Dict[str, Any]:
    rows = load_window(minutes)
    reqs = [r for r in rows if is_request(r)]

    hourly: Dict[str, int] = {}
    for r in reqs:
        local_dt = r.timestamp.astimezone()  # server local time
        h = local_dt.strftime("%H")
        hourly[h] = hourly.get(h, 0) + 1

    for i in range(24):
        hourly.setdefault(f"{i:02d}", 0)

    hourly = dict(sorted(hourly.items(), key=lambda kv: kv[0]))
    return {"hourly_distribution": hourly}


# ──────────────────────────────────────────────────────────────────────────────
# Debug endpoint
# ──────────────────────────────────────────────────────────────────────────────

@app.get(f"{API_PREFIX}/debug/sample")
def debug_sample(n: int = Query(5, ge=1, le=50)) -> Dict[str, Any]:
    raw: List[Dict[str, Any]] = []
    parsed: List[Dict[str, Any]] = []

    i = 0
    for d in iter_jsonl(LOG_FILE_PATH):
        raw.append(d)
        r = normalize(d)
        if r:
            parsed.append(
                {
                    "timestamp": r.timestamp.isoformat(),
                    "path": r.path,
                    "method": r.method,
                    "status_code": r.status_code,
                    "duration_ms": r.duration_ms,
                    "is_authenticated": r.is_authenticated,
                    "level": r.level,
                    "event_type": r.event_type,
                    "is_request": is_request(r),
                }
            )
        i += 1
        if i >= n:
            break

    latest = get_latest_timestamp()
    return {"raw": raw, "parsed": parsed, "latest_timestamp": (latest.isoformat() if latest else None)}
