"""
Data Models (DTOs - Data Transfer Objects)

This module contains all dataclass definitions used throughout the application.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class LogEntry:  # Renamed from Row to match diagram
    """Represents a single normalized log entry"""
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


@dataclass
class HealthStatus:
    """Health check response"""
    status: str
    log_file_exists: bool
    path: str
    size_bytes: int
    total_lines: int
    latest_timestamp: Optional[str] = None


@dataclass
class Metrics:
    """Aggregated metrics"""
    total_requests: int
    error_count: int
    error_rate: float
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_by_status: Dict[str, int]
    requests_by_method: Dict[str, int]
    unique_users: int
    authenticated_requests: int


@dataclass
class EndpointStat:
    """Per-endpoint statistics"""
    path: str
    count: int
    errors: int
    avg_response_time: float
    p95_response_time: float
    error_rate: float
