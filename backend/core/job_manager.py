import uuid
import time
import os
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
                "files": [],
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

    def set_files(self, job_id: str, filenames: list[str]):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["files"] = filenames

    def sync_files_from_disk(self, job_id: str, upload_folder: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.get("files"):
                return

            job_dir = os.path.join(upload_folder, job_id)
            if not os.path.isdir(job_dir):
                return

            names = sorted(
                name for name in os.listdir(job_dir)
                if os.path.isfile(os.path.join(job_dir, name))
                and name.lower().rsplit(".", 1)[-1] in ("jpg", "jpeg", "png")
            )
            if names:
                job["files"] = names

    def sync_all_files_from_disk(self, upload_folder: str):
        with self._lock:
            job_ids = list(self._jobs.keys())

        for job_id in job_ids:
            self.sync_files_from_disk(job_id, upload_folder)

    def delete_job(self, job_id: str) -> bool:
        with self._lock:
            if job_id not in self._jobs:
                return False
            del self._jobs[job_id]
            return True

    def list_jobs(self) -> list[dict]:
        with self._lock:
            jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j["created_at"], reverse=True)
        return [self._summarize(j) for j in jobs]

    def get_stats(self) -> dict:
        with self._lock:
            jobs = list(self._jobs.values())

        images_processed = 0
        successful_jobs = 0
        failed_jobs = 0
        hive_scores = []

        for job in jobs:
            if job["status"] == "done":
                successful_jobs += 1
                images_processed += job["total"]
            elif job["status"] == "error":
                failed_jobs += 1

            for result in job["results"]:
                if "hive_vector" in result:
                    hive_scores.append(result["hive_vector"])
                if "hive_3d" in result:
                    hive_scores.append(result["hive_3d"])

        avg_hive = round(sum(hive_scores) / len(hive_scores), 1) if hive_scores else None

        return {
            "images_processed": images_processed,
            "successful_jobs": successful_jobs,
            "failed_jobs": failed_jobs,
            "avg_hive_score": avg_hive,
        }

    def _summarize(self, job: dict) -> dict:
        hive_scores = []
        for result in job["results"]:
            if "hive_vector" in result:
                hive_scores.append(result["hive_vector"])
            if "hive_3d" in result:
                hive_scores.append(result["hive_3d"])

        avg_hive = round(sum(hive_scores) / len(hive_scores), 1) if hive_scores else None

        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "progress": job["progress"],
            "total": job["total"],
            "created_at": job["created_at"],
            "error": job["error"],
            "avg_hive": avg_hive,
            "files": job.get("files", []),
        }
