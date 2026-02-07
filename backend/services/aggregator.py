"""
Aggregator Class - Computes metrics and statistics

This module aggregates log entries into metrics and statistics.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from models.data_models import EndpointStat, LogEntry, Metrics
from services.parser import LogParser
from services.storage import LogStore
from utils.helpers import quantile


class Aggregator:
    """
    Aggregates log entries into metrics and statistics.
    Responsibilities:
    - Filter entries by time window
    - Compute overall metrics
    - Compute per-endpoint statistics
    - Compute error statistics
    - Compute traffic patterns
    """

    def __init__(self, log_store: LogStore, log_parser: LogParser):
        self.store = log_store
        self.parser = log_parser

    def filter_by_window(self, entries: List[LogEntry], minutes: int) -> List[LogEntry]:
        """
        Filter entries within time window.
        Window is anchored to latest timestamp in log (not system clock).
        """
        if not entries:
            return []

        latest = max(e.timestamp for e in entries)
        start = latest - timedelta(minutes=minutes)

        return [e for e in entries if start <= e.timestamp <= latest]

    def compute_metrics(self, entries: List[LogEntry]) -> Metrics:
        """Compute aggregated metrics from log entries"""
        requests = [e for e in entries if self.parser.is_request(e)]
        total = len(requests)

        # Calculate error metrics
        error_count = sum(1 for e in requests if e.status_code and e.status_code >= 400)
        error_rate = (error_count / total * 100.0) if total else 0.0

        # Calculate response time metrics
        durations = sorted([e.duration_ms for e in requests if e.duration_ms is not None])
        avg_response = (sum(durations) / len(durations)) if durations else 0.0
        p50 = quantile(durations, 0.50) if durations else 0.0
        p95 = quantile(durations, 0.95) if durations else 0.0
        p99 = quantile(durations, 0.99) if durations else 0.0

        # Group by status and method
        by_status: Dict[str, int] = {}
        by_method: Dict[str, int] = {}

        for e in requests:
            if e.status_code is not None:
                key = str(e.status_code)
                by_status[key] = by_status.get(key, 0) + 1

            if e.method:
                by_method[e.method] = by_method.get(e.method, 0) + 1

        # User metrics
        unique_users = len({e.user_id for e in requests if e.user_id is not None})
        authenticated = sum(1 for e in requests if e.is_authenticated is True)

        return Metrics(
            total_requests=total,
            error_count=error_count,
            error_rate=error_rate,
            avg_response_time=avg_response,
            p50_response_time=p50,
            p95_response_time=p95,
            p99_response_time=p99,
            requests_by_status=by_status,
            requests_by_method=by_method,
            unique_users=unique_users,
            authenticated_requests=authenticated,
        )

    def compute_endpoints(
        self,
        entries: List[LogEntry],
        limit: int = 10,
        sort_by: str = "count",
        order: str = "desc",
    ) -> List[EndpointStat]:
        """Compute per-endpoint statistics"""
        requests = [e for e in entries if self.parser.is_request(e) and e.path]

        # Group by endpoint path
        buckets: Dict[str, List[LogEntry]] = {}
        for e in requests:
            buckets.setdefault(e.path, []).append(e)

        # Calculate stats for each endpoint
        stats: List[EndpointStat] = []
        for path, items in buckets.items():
            count = len(items)
            errors = sum(1 for e in items if e.status_code and e.status_code >= 400)

            durs = sorted([e.duration_ms for e in items if e.duration_ms is not None])
            avg = (sum(durs) / len(durs)) if durs else 0.0
            p95 = quantile(durs, 0.95) if durs else 0.0

            error_rate = (errors / count * 100.0) if count else 0.0

            stats.append(
                EndpointStat(
                    path=path,
                    count=count,
                    errors=errors,
                    avg_response_time=avg,
                    p95_response_time=p95,
                    error_rate=error_rate,
                )
            )

        # Sort
        reverse = order.lower() != "asc"
        key_fn = (
            (lambda x: x.p95_response_time)
            if sort_by.lower() == "p95"
            else (lambda x: x.count)
        )
        stats.sort(key=key_fn, reverse=reverse)

        return stats[:limit]

    def compute_errors(self, entries: List[LogEntry], limit: int = 20) -> List[LogEntry]:
        """Get recent error entries"""
        errors = [e for e in entries if self.parser.is_error(e)]
        errors.sort(key=lambda e: e.timestamp, reverse=True)
        return errors[:limit]

    def compute_traffic(self, entries: List[LogEntry]) -> Dict[str, int]:
        """Compute hourly traffic distribution"""
        requests = [e for e in entries if self.parser.is_request(e)]

        hourly: Dict[str, int] = {}
        for e in requests:
            local_dt = e.timestamp.astimezone()  # Convert to local timezone
            hour = local_dt.strftime("%H")
            hourly[hour] = hourly.get(hour, 0) + 1

        # Fill in missing hours with 0
        for i in range(24):
            hourly.setdefault(f"{i:02d}", 0)

        return dict(sorted(hourly.items()))

    def load_all_entries(self) -> List[LogEntry]:
        """Load and parse all log entries from store"""
        entries: List[LogEntry] = []

        for line in self.store.read_lines():
            raw = self.parser.parse_json(line)
            if raw:
                entry = self.parser.normalize(raw)
                if entry:
                    entries.append(entry)

        return entries

    def get_latest_timestamp(self) -> Optional[datetime]:
        """Get latest timestamp from all entries"""
        entries = self.load_all_entries()
        return max((e.timestamp for e in entries), default=None) if entries else None
