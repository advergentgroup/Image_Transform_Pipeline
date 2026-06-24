import os
import zipfile
from backend.services.ai_service import AIService
from backend.services.image_service import ImageService
from backend.services.hivedetect_service import HivedetectService
from backend.core.job_manager import JobManager


def run_pipeline(job_id: str, image_paths: list, config: dict, job_manager: JobManager):
    """
    Full processing pipeline for one job.
    Called in background thread (MVP) or Celery task (final).

    Steps per image:
      1. Pillow filters — deterministic uniquification (no face warp)
      2. Optional AI variation (flux-redux) if UNIQUE_MODE != pillow
      3. Vectorize + gradient bg  → Archive 1
      4. FLUX Kontext 3D Pixar    → Archive 2
      5. Hivedetect check on both outputs
    Then zips output into a single archive.
    """
    job_manager.update_status(job_id, "processing")

    ai = AIService(config)
    img = ImageService(config)
    hive = HivedetectService(config)

    output_dir = os.path.join(config["OUTPUT_FOLDER"], job_id)
    vector_dir = os.path.join(output_dir, "vector")
    threed_dir = os.path.join(output_dir, "3d")
    os.makedirs(vector_dir, exist_ok=True)
    os.makedirs(threed_dir, exist_ok=True)

    try:
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            stem = os.path.splitext(filename)[0]

            # ── Step 1: Pillow uniquify filters (always) ───────────────
            job_manager.set_step(job_id, 0)
            filtered_path = os.path.join(output_dir, f"filtered_{filename}")
            img.apply_uniquify_filters(image_path, filtered_path)

            # ── Step 2: Optional AI variation layer ────────────────────
            if config.get("UNIQUE_MODE", "pillow") != "pillow":
                work_path = ai.uniquify(filtered_path, output_dir)
            else:
                work_path = filtered_path

            # ── Step 3: Vectorize + gradient (Archive 1) ───────────────
            job_manager.set_step(job_id, 1)
            vector_path = os.path.join(vector_dir, f"{stem}_vector.png")
            img.vectorize_with_gradient(work_path, vector_path)

            # ── Step 4: 3D Pixar style (Archive 2) ────────────────────
            job_manager.set_step(job_id, 2)
            threed_path = os.path.join(threed_dir, f"{stem}_3d.png")
            ai.transform_3d(work_path, threed_path)

            # ── Step 5: Hivedetect check ───────────────────────────────
            job_manager.set_step(job_id, 3)
            vector_score = hive.check(vector_path)
            threed_score = hive.check(threed_path)

            job_manager.increment_progress(job_id, {
                "filename": filename,
                "vector_file": f"{stem}_vector.png",
                "threed_file": f"{stem}_3d.png",
                "hive_vector": vector_score,   # % AI detection (lower = more human-like)
                "hive_3d": threed_score,
            })

            job = job_manager.get_job(job_id)
            if job and job["progress"] >= job["total"]:
                job_manager.set_step(job_id, 4)

        # ── Zip both archives ──────────────────────────────────────────
        job_manager.set_step(job_id, 4)
        _zip_output(vector_dir, threed_dir, os.path.join(output_dir, "output.zip"))

        job_manager.update_status(job_id, "done")

    except Exception as e:
        job_manager.set_error(job_id, str(e))


def _zip_output(vector_dir: str, threed_dir: str, zip_path: str):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in os.listdir(vector_dir):
            zf.write(os.path.join(vector_dir, fname), arcname=f"vector/{fname}")
        for fname in os.listdir(threed_dir):
            zf.write(os.path.join(threed_dir, fname), arcname=f"3d/{fname}")
