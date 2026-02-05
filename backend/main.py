from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from dateutil import parser as dtparser
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

API_PREFIX = "/api"
LOG_FILE_PATH = os.getenv("LOG_FILE", "./data/monitoring.jsonl")  # saved normalized as JSONL

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def iter_jsonl(path: str) -> Iterable[Dict[str, Any]]:
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
    """
    Linear percentile on a sorted list (numpy-like).
    """
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
    ts = parse_ts(d.get("timestamp"))
    if ts is None:
        return None

    ia = d.get("is_authenticated")
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
        level=str(d.get("level") or ""),
        event_type=str(d.get("event_type") or ""),
        method=(str(d.get("method")) if d.get("method") is not None else None),
        path=(str(d.get("path")) if d.get("path") is not None else None),
        status_code=safe_int(d.get("status_code")),
        duration_ms=safe_float(d.get("duration_ms")),
        user_id=safe_int(d.get("user_id")),
        is_authenticated=is_auth,
        error_type=(str(d.get("error_type")) if d.get("error_type") is not None else None),
        error_message=(str(d.get("error_message")) if d.get("error_message") is not None else None),
    )


def is_request(r: Row) -> bool:
    """
    Your logs have both event_type="request" and event_type="user_action".
    For the dashboard, treat anything that has (path, method, status_code) as a request-like entry.
    """
    return bool(r.path and r.method and (r.status_code is not None))


def is_error_row(r: Row) -> bool:
    """
    Errors page rule: level=="ERROR" OR status_code>=400
    """
    if r.status_code is not None and r.status_code >= 400:
        return True
    if (r.level or "").upper() == "ERROR":
        return True
    return False


def load_window(minutes: int) -> List[Row]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=minutes)
    out: List[Row] = []
    for d in iter_jsonl(LOG_FILE_PATH):
        r = normalize(d)
        if r and r.timestamp >= start:
            out.append(r)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Monitoring (file-upload JSON/JSONL → dashboard APIs)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev OK; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Upload: receive a FILE from another site (JSONL or JSON array) and save as JSONL
# ──────────────────────────────────────────────────────────────────────────────

@app.post(f"{API_PREFIX}/upload-log")
async def upload_log_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Receives a log file from another site:
      - JSONL: each line is a JSON object
      - JSON: a JSON array of objects
    Saves it as JSONL to LOG_FILE_PATH (overwrite).
    """
    ensure_parent_dir(LOG_FILE_PATH)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    text = content.decode("utf-8", errors="ignore").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty file")

    # JSON array -> convert to JSONL
    if text.startswith("["):
        try:
            arr = json.loads(text)
            if not isinstance(arr, list):
                raise ValueError("JSON must be a list")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON array file")

        written = 0
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            for item in arr:
                if isinstance(item, dict):
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
                    written += 1

        return {
            "status": "ok",
            "saved_as": "jsonl",
            "mode": "converted_from_json_array",
            "written": written,
            "path": os.path.abspath(LOG_FILE_PATH),
        }

    # Otherwise: treat as JSONL and save
    with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(text + ("\n" if not text.endswith("\n") else ""))

    # count lines roughly
    line_count = sum(1 for _ in text.splitlines() if _.strip())
    return {
        "status": "ok",
        "saved_as": "jsonl",
        "mode": "raw_jsonl",
        "written": line_count,
        "path": os.path.abspath(LOG_FILE_PATH),
    }

# ──────────────────────────────────────────────────────────────────────────────
# Dashboard APIs (as used by your Dashboard.tsx)
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

    return {
        "status": "ok",
        "log_file": {
            "exists": exists,
            "path": os.path.abspath(LOG_FILE_PATH),
            "size_bytes": size_bytes,
            "total_lines": total_lines,
        },
    }


@app.get(f"{API_PREFIX}/metrics")
def metrics(minutes: int = Query(60, ge=1, le=60 * 24 * 14)) -> Dict[str, Any]:
    rows = load_window(minutes)
    reqs = [r for r in rows if is_request(r)]

    total_requests = len(reqs)

    durations = sorted([r.duration_ms for r in reqs if r.duration_ms is not None])
    avg_response_time = (sum(durations) / len(durations)) if durations else 0.0

    # Overview: Error Rate based on status_code >= 400
    error_count = sum(1 for r in reqs if (r.status_code is not None and r.status_code >= 400))
    error_rate = (error_count / total_requests * 100.0) if total_requests else 0.0

    # Percentiles
    p50 = quantile(durations, 0.50) if durations else 0.0
    p95 = quantile(durations, 0.95) if durations else 0.0
    p99 = quantile(durations, 0.99) if durations else 0.0

    # Charts
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

        # Use is_authenticated from your schema
        if r.is_authenticated is True:
            authenticated_requests += 1

    return {
        "metrics": {
            "total_requests": total_requests,
            "avg_response_time": avg_response_time,
            "error_rate": error_rate,
            "p50_response_time": p50,
            "p95_response_time": p95,
            "p99_response_time": p99,
            "unique_users": len(user_ids),
            "authenticated_requests": authenticated_requests,
            "requests_by_status": requests_by_status,
            "requests_by_method": requests_by_method,
        }
    }


@app.get(f"{API_PREFIX}/endpoints")
def endpoints(
    minutes: int = Query(60, ge=1, le=60 * 24 * 14),
    limit: int = Query(10, ge=1, le=100),
) -> Dict[str, Any]:
    rows = load_window(minutes)
    reqs = [r for r in rows if is_request(r) and r.path]

    buckets: Dict[str, List[Row]] = {}
    for r in reqs:
        buckets.setdefault(r.path, []).append(r)

    out = []
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

    # Top endpoints by request count (as your UI says)
    out.sort(key=lambda x: x["count"], reverse=True)
    return {"endpoints": out[:limit]}


@app.get(f"{API_PREFIX}/errors")
def errors(limit: int = Query(20, ge=1, le=200)) -> Dict[str, Any]:
    # For "latest N errors" it's simplest to scan all and sort by timestamp.
    # For huge logs you'd optimize this (tail/index), but keeping it simple here.
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


@app.get(f"{API_PREFIX}/traffic")
def traffic(minutes: int = Query(1440, ge=1, le=60 * 24 * 14)) -> Dict[str, Any]:
    rows = load_window(minutes)
    reqs = [r for r in rows if is_request(r)]

    # Hourly distribution (UTC hours "00".."23")
    hourly: Dict[str, int] = {}
    for r in reqs:
        h = r.timestamp.strftime("%H")
        hourly[h] = hourly.get(h, 0) + 1

    # Ensure all 24 hours exist
    for i in range(24):
        hourly.setdefault(f"{i:02d}", 0)

    hourly = dict(sorted(hourly.items(), key=lambda kv: kv[0]))
    return {"hourly_distribution": hourly}
