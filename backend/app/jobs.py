from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    status: JobStatus = JobStatus.PENDING
    images_processed: int = 0
    images_total: int = 0
    faces_stored: int = 0
    current_file: str = ""
    preview_images: list[dict] = field(default_factory=list)
    skipped_files: list[dict] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "job_id": self.id,
            "status": self.status.value,
            "images_processed": self.images_processed,
            "images_total": self.images_total,
            "faces_stored": self.faces_stored,
            "current_file": self.current_file,
            "preview_images": self.preview_images,
            "skipped_files": self.skipped_files,
            "error": self.error,
        }


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def create_job() -> Job:
    job = Job(id=uuid4().hex)
    with _lock:
        _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)
