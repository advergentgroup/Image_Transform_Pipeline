import uuid
import time
from threading import Lock


class JobManager:
    """
    In-memory job store for MVP.
    Replace with Redis in final version.
    """

    def __init__(self):
        self._jobs = {}
        self._lock = Lock()

    def create_job(self, file_count: int) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "pending",   # pending | processing | done | error
                "progress": 0,
                "total": file_count,
                "results": [],
                "created_at": time.time(),
                "error": None,
            }
        return job_id

    def get_job(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)

    def update_status(self, job_id: str, status: str):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = status

    def increment_progress(self, job_id: str, result: dict):
        """Called after each file finishes processing."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job["progress"] += 1
                job["results"].append(result)

    def set_error(self, job_id: str, message: str):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "error"
                self._jobs[job_id]["error"] = message
