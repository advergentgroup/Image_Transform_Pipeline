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
      1. AI img2img — subtle uniquification
      2. Vectorize + gradient bg  → saved for Archive 1
      3. AI 3D Pixar transform    → saved for Archive 2
      4. Hivedetect check on both outputs
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

            # ── Step 1: AI uniquification ──────────────────────────────
            uniquified_path = ai.img2img_unique(image_path, output_dir)

            # ── Step 2: Vectorize + gradient (Archive 1) ───────────────
            vector_path = os.path.join(vector_dir, f"{stem}_vector.png")
            img.vectorize_with_gradient(uniquified_path, vector_path)

            # ── Step 3: 3D Pixar style (Archive 2) ────────────────────
            threed_path = os.path.join(threed_dir, f"{stem}_3d.png")
            ai.img2img_3d(uniquified_path, threed_path)

            # ── Step 4: Hivedetect check ───────────────────────────────
            vector_score = hive.check(vector_path)
            threed_score = hive.check(threed_path)

            job_manager.increment_progress(job_id, {
                "filename": filename,
                "vector_file": f"{stem}_vector.png",
                "threed_file": f"{stem}_3d.png",
                "hive_vector": vector_score,   # % AI detection (lower = more human-like)
                "hive_3d": threed_score,
            })

        # ── Zip both archives ──────────────────────────────────────────
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
