"""
LogStore Class - Handles file I/O operations

This module manages log file storage and retrieval.
"""

import json
import os
from typing import Any, Dict, Iterable, List

from models.data_models import HealthStatus


class LogStore:
    """
    Manages log file storage and retrieval.
    Responsibilities:
    - Save uploaded log files
    - Read log file lines
    - Provide file statistics
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def save_upload(self, content: bytes) -> Dict[str, Any]:
        """
        Save uploaded log file (supports JSONL, JSON array, or JSON object)
        Returns metadata about saved file
        """
        self._ensure_parent_dir()

        if not content:
            raise ValueError("Empty file content")

        text = content.decode("utf-8", errors="ignore").strip()
        if not text:
            raise ValueError("Empty file after decoding")

        # Try parsing as JSON first (handles multiline JSON)
        try:
            obj = json.loads(text)

            # JSON array
            if isinstance(obj, list):
                written = self._write_jsonl(obj)
                return {"mode": "json_array", "written": written}

            # JSON object with list under common keys
            if isinstance(obj, dict):
                for key in ("logs", "events", "entries", "data", "items"):
                    if key in obj and isinstance(obj[key], list):
                        written = self._write_jsonl(obj[key])
                        return {"mode": f"json_object.{key}", "written": written}

                # Single JSON object
                written = self._write_jsonl([obj])
                return {"mode": "single_json_object", "written": written}
        except Exception:
            pass

        # Fallback: treat as raw JSONL
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(text + ("\n" if not text.endswith("\n") else ""))

        line_count = sum(1 for ln in text.splitlines() if ln.strip())
        return {"mode": "raw_jsonl", "written": line_count}

    def read_lines(self) -> Iterable[str]:
        """Iterator over raw lines in log file"""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        yield line
        except FileNotFoundError:
            return

    def stat(self) -> HealthStatus:
        """Get file statistics"""
        exists = os.path.exists(self.file_path)
        size_bytes = os.path.getsize(self.file_path) if exists else 0
        total_lines = 0

        if exists:
            try:
                total_lines = sum(1 for _ in self.read_lines())
            except Exception:
                pass

        return HealthStatus(
            status="ok",
            log_file_exists=exists,
            path=os.path.abspath(self.file_path),
            size_bytes=size_bytes,
            total_lines=total_lines,
        )

    def _ensure_parent_dir(self) -> None:
        """Create parent directories if needed"""
        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)

    def _write_jsonl(self, items: List[dict]) -> int:
        """Write list of dicts as JSONL"""
        written = 0
        with open(self.file_path, "w", encoding="utf-8") as f:
            for item in items:
                if isinstance(item, dict):
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
                    written += 1
        return written
