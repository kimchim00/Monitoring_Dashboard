"""
LogParser Class - Handles parsing and normalization

This module parses raw log lines into structured LogEntry objects.
"""

import json
from typing import Any, Dict, Optional

from models.data_models import LogEntry
from utils.helpers import get_nested, parse_ts, safe_float, safe_int


class LogParser:
    """
    Parses raw log lines into structured LogEntry objects.
    Responsibilities:
    - Parse JSON lines
    - Normalize various log formats
    - Classify log entries (request, error, etc.)
    """

    @staticmethod
    def parse_json(line: str) -> Optional[Dict[str, Any]]:
        """Parse JSON line, return None if invalid"""
        try:
            return json.loads(line)
        except Exception:
            return None

    @staticmethod
    def normalize(raw: Dict[str, Any]) -> Optional[LogEntry]:
        """
        Normalize raw log dict into structured LogEntry.
        Handles various log formats and nested structures.
        """
        # Parse timestamp (required field)
        ts = parse_ts(
            raw.get("timestamp")
            or raw.get("time")
            or get_nested(raw, ("meta", "timestamp"))
        )
        if ts is None:
            return None

        # Extract method
        method = (
            raw.get("method")
            or get_nested(raw, ("request", "method"))
            or get_nested(raw, ("http", "method"))
        )

        # Extract path
        path = (
            raw.get("path")
            or get_nested(raw, ("request", "path"))
            or get_nested(raw, ("http", "path"))
            or raw.get("endpoint")
        )

        # Extract status code
        status_raw = (
            raw.get("status_code")
            or raw.get("status")
            or get_nested(raw, ("response", "status_code"))
            or get_nested(raw, ("http", "status"))
        )

        # Extract duration
        duration_raw = (
            raw.get("duration_ms")
            or raw.get("latency_ms")
            or raw.get("response_time_ms")
            or get_nested(raw, ("timing", "duration_ms"))
        )

        # Extract authentication
        is_auth_raw = (
            raw.get("is_authenticated")
            or raw.get("authenticated")
            or get_nested(raw, ("auth", "is_authenticated"))
        )

        # Convert authentication to boolean
        if isinstance(is_auth_raw, bool):
            is_auth = is_auth_raw
        elif is_auth_raw is None:
            is_auth = None
        else:
            s = str(is_auth_raw).strip().lower()
            is_auth = (
                s in ("true", "1", "yes")
                if s in ("true", "1", "yes", "false", "0", "no")
                else None
            )

        return LogEntry(
            timestamp=ts,
            level=str(raw.get("level") or raw.get("severity") or ""),
            event_type=str(raw.get("event_type") or raw.get("type") or ""),
            method=str(method) if method is not None else None,
            path=str(path) if path is not None else None,
            status_code=safe_int(status_raw),
            duration_ms=safe_float(duration_raw),
            user_id=safe_int(raw.get("user_id") or get_nested(raw, ("user", "id"))),
            is_authenticated=is_auth,
            error_type=str(raw.get("error_type"))
            if raw.get("error_type") is not None
            else None,
            error_message=str(raw.get("error_message"))
            if raw.get("error_message") is not None
            else None,
        )

    @staticmethod
    def is_request(entry: LogEntry) -> bool:
        """Check if entry represents an HTTP request"""
        return bool(entry.path and entry.method)

    @staticmethod
    def is_error(entry: LogEntry) -> bool:
        """Check if entry represents an error (status >= 400 or ERROR level)"""
        if entry.status_code is not None and entry.status_code >= 400:
            return True
        if (entry.level or "").upper() == "ERROR":
            return True
        return False
