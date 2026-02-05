"""
Monitoring Dashboard API

FastAPI application for monitoring log analytics.
"""

import os
from typing import Any, Dict, List

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from models.data_models import EndpointStat, HealthStatus, LogEntry, Metrics
from services.aggregator import Aggregator
from services.parser import LogParser
from services.storage import LogStore

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

API_PREFIX = "/api"
LOG_FILE_PATH = os.getenv("LOG_FILE", "./data/monitoring.jsonl")

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI Application
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Monitoring Dashboard API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components (Dependency Injection pattern)
log_store = LogStore(LOG_FILE_PATH)
log_parser = LogParser()
aggregator = Aggregator(log_store, log_parser)


# ──────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────────────────────────────────────


@app.post(f"{API_PREFIX}/upload-log")
async def upload_log_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload log file (JSONL, JSON array, or JSON object)"""
    try:
        content = await file.read()
        result = log_store.save_upload(content)

        return {
            "status": "ok",
            "saved_as": "jsonl",
            **result,
            "path": log_store.file_path,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get(f"{API_PREFIX}/health")
def health() -> Dict[str, Any]:
    """Health check endpoint"""
    status = log_store.stat()
    latest = aggregator.get_latest_timestamp()

    return {
        "status": status.status,
        "log_file": {
            "exists": status.log_file_exists,
            "path": status.path,
            "size_bytes": status.size_bytes,
            "total_lines": status.total_lines,
        },
        "latest_timestamp": latest.isoformat() if latest else None,
    }


@app.get(f"{API_PREFIX}/metrics")
def get_metrics(minutes: int = Query(60, ge=1, le=60 * 24 * 14)) -> Dict[str, Any]:
    """Get aggregated metrics for time window"""
    all_entries = aggregator.load_all_entries()
    windowed = aggregator.filter_by_window(all_entries, minutes)
    metrics = aggregator.compute_metrics(windowed)

    return {
        "metrics": {
            "total_requests": metrics.total_requests,
            "error_count": metrics.error_count,
            "error_rate": metrics.error_rate,
            "avg_response_time": metrics.avg_response_time,
            "p50_response_time": metrics.p50_response_time,
            "p95_response_time": metrics.p95_response_time,
            "p99_response_time": metrics.p99_response_time,
            "requests_by_status": metrics.requests_by_status,
            "requests_by_method": metrics.requests_by_method,
            "unique_users": metrics.unique_users,
            "authenticated_requests": metrics.authenticated_requests,
        }
    }


@app.get(f"{API_PREFIX}/endpoints")
def get_endpoints(
    minutes: int = Query(60, ge=1, le=60 * 24 * 14),
    limit: int = Query(10, ge=1, le=200),
    sort_by: str = Query("count"),
    order: str = Query("desc"),
) -> Dict[str, Any]:
    """Get per-endpoint statistics"""
    all_entries = aggregator.load_all_entries()
    windowed = aggregator.filter_by_window(all_entries, minutes)
    stats = aggregator.compute_endpoints(windowed, limit, sort_by, order)

    return {
        "endpoints": [
            {
                "path": s.path,
                "count": s.count,
                "errors": s.errors,
                "avg_response_time": s.avg_response_time,
                "p95_response_time": s.p95_response_time,
                "error_rate": s.error_rate,
            }
            for s in stats
        ]
    }


@app.get(f"{API_PREFIX}/errors")
def get_errors(limit: int = Query(20, ge=1, le=200)) -> Dict[str, Any]:
    """Get recent error entries"""
    all_entries = aggregator.load_all_entries()
    errors = aggregator.compute_errors(all_entries, limit)

    return {
        "errors": [
            {
                "timestamp": e.timestamp.isoformat(),
                "level": e.level,
                "method": e.method,
                "path": e.path,
                "status_code": e.status_code,
                "error_type": e.error_type,
                "error_message": e.error_message,
                "user_id": e.user_id,
            }
            for e in errors
        ]
    }


@app.get(f"{API_PREFIX}/traffic")
def get_traffic(minutes: int = Query(1440, ge=1, le=60 * 24 * 14)) -> Dict[str, Any]:
    """Get hourly traffic distribution"""
    all_entries = aggregator.load_all_entries()
    windowed = aggregator.filter_by_window(all_entries, minutes)
    hourly = aggregator.compute_traffic(windowed)

    return {"hourly_distribution": hourly}


@app.get(f"{API_PREFIX}/debug/sample")
def debug_sample(n: int = Query(5, ge=1, le=50)) -> Dict[str, Any]:
    """Debug endpoint: show sample of raw and parsed entries"""
    raw_samples: List[Dict[str, Any]] = []
    parsed_samples: List[Dict[str, Any]] = []

    i = 0
    for line in log_store.read_lines():
        raw = log_parser.parse_json(line)
        if raw:
            raw_samples.append(raw)

            entry = log_parser.normalize(raw)
            if entry:
                parsed_samples.append(
                    {
                        "timestamp": entry.timestamp.isoformat(),
                        "path": entry.path,
                        "method": entry.method,
                        "status_code": entry.status_code,
                        "duration_ms": entry.duration_ms,
                        "is_authenticated": entry.is_authenticated,
                        "level": entry.level,
                        "is_request": log_parser.is_request(entry),
                    }
                )

        i += 1
        if i >= n:
            break

    latest = aggregator.get_latest_timestamp()

    return {
        "raw": raw_samples,
        "parsed": parsed_samples,
        "latest_timestamp": latest.isoformat() if latest else None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Application entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
