from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


@dataclass
class JobState:
    job_id: str
    label: str
    status: str = "processing"  # processing | complete | error
    total_chunks: Optional[int] = None
    processed_chunks: int = 0
    message: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        percent = None
        if self.total_chunks and self.total_chunks > 0:
            percent = max(
                0,
                min(100, int((self.processed_chunks / self.total_chunks) * 100)),
            )
        return {
            "job_id": self.job_id,
            "label": self.label,
            "status": self.status,
            "total_chunks": self.total_chunks,
            "processed_chunks": self.processed_chunks,
            "percent_complete": percent,
            "message": self.message,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


_lock = threading.Lock()
_jobs: Dict[str, JobState] = {}


def start_job(job_id: str, label: str, message: str | None = None) -> None:
    with _lock:
        _jobs[job_id] = JobState(
            job_id=job_id,
            label=label,
            message=message,
        )


def update_job(
    job_id: str,
    *,
    processed_chunks: Optional[int] = None,
    total_chunks: Optional[int] = None,
    message: Optional[str] = None,
    status: Optional[str] = None,
) -> None:
    with _lock:
        state = _jobs.get(job_id)
        if not state:
            return
        if processed_chunks is not None:
            state.processed_chunks = processed_chunks
        if total_chunks is not None:
            state.total_chunks = total_chunks
        if message is not None:
            state.message = message
        if status is not None:
            state.status = status
        state.updated_at = datetime.now(timezone.utc)


def complete_job(job_id: str, *, message: Optional[str] = None) -> None:
    with _lock:
        state = _jobs.get(job_id)
        if not state:
            return
        if state.total_chunks is not None:
            state.processed_chunks = state.total_chunks
        if message is not None:
            state.message = message
        state.status = "complete"
        state.updated_at = datetime.now(timezone.utc)


def fail_job(job_id: str, *, message: Optional[str] = None) -> None:
    with _lock:
        state = _jobs.get(job_id)
        if not state:
            return
        state.status = "error"
        if message is not None:
            state.message = message
        state.updated_at = datetime.now(timezone.utc)


def list_jobs(
    *,
    include_finished: bool = True,
    max_age_seconds: int = 3600,
    limit: Optional[int] = 20,
) -> List[Dict[str, Any]]:
    """Return recent ingestion jobs ordered by start time (newest first)."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
    with _lock:
        obsolete = [
            job_id
            for job_id, state in _jobs.items()
            if state.status in {"complete", "error"} and state.updated_at < cutoff
        ]
        for job_id in obsolete:
            _jobs.pop(job_id, None)

        states = list(_jobs.values())

    if not include_finished:
        states = [state for state in states if state.status not in {"complete", "error"}]

    states.sort(key=lambda state: state.started_at, reverse=True)

    if limit is not None:
        states = states[:limit]

    return [state.to_dict() for state in states]


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        state = _jobs.get(job_id)
        return state.to_dict() if state else None


def clear_all() -> None:
    """Testing helper to reset tracker."""
    with _lock:
        _jobs.clear()

