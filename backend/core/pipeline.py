import logging
import os
import zipfile

from backend.core.job_manager import JobManager
from backend.services.ai_service import AIService
from backend.services.hivedetect_service import HivedetectService
from backend.services.image_service import ImageService

logger = logging.getLogger(__name__)


def run_pipeline(job_id: str, image_paths: list, config: dict, job_manager: JobManager):
    """
    Per image:
      - Vector: posterize 16-color + gradient
      - 3D: FLUX Kontext (real 3D render) — default
      - 3D pseudo3d: optional flat shading mode (passes Hive, not real 3D)
    """
    job_manager.update_status(job_id, "processing")

    ai = AIService(config)
    img = ImageService(config)
    hive = HivedetectService(config)

    unique_mode = config.get("UNIQUE_MODE", "pillow")
    threed_mode = str(config.get("THREED_MODE", "kontext")).lower()

    output_dir = os.path.join(config["OUTPUT_FOLDER"], job_id)
    vector_dir = os.path.join(output_dir, "vector")
    threed_dir = os.path.join(output_dir, "3d")
    os.makedirs(vector_dir, exist_ok=True)
    os.makedirs(threed_dir, exist_ok=True)

    try:
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            stem = os.path.splitext(filename)[0]

            source_path = image_path
            if unique_mode != "pillow":
                job_manager.set_step(job_id, 0)
                logger.info("AI uniquify (%s): %s", unique_mode, filename)
                source_path = ai.uniquify(image_path, output_dir)

            job_manager.set_step(job_id, 1)
            vector_path = os.path.join(vector_dir, f"{stem}_vector.png")
            img.vectorize_with_gradient(source_path, vector_path)

            job_manager.set_step(job_id, 2)
            threed_path = os.path.join(threed_dir, f"{stem}_3d.png")

            if threed_mode == "pseudo3d":
                posterized = img._prepare_posterized(source_path)
                img.render_pseudo_3d(posterized, threed_path)
            else:
                ai.transform_3d(source_path, threed_path)

            threed_tmp = os.path.join(threed_dir, f".{stem}_3d_clean.png")
            img.strip_image_metadata(threed_path, threed_tmp)
            os.replace(threed_tmp, threed_path)

            job_manager.set_step(job_id, 3)
            vector_score = hive.check(vector_path)
            threed_score = hive.check(threed_path)

            job_manager.increment_progress(job_id, {
                "filename": filename,
                "vector_file": f"{stem}_vector.png",
                "threed_file": f"{stem}_3d.png",
                "hive_vector": vector_score,
                "hive_3d": threed_score,
            })

            job = job_manager.get_job(job_id)
            if job and job["progress"] >= job["total"]:
                job_manager.set_step(job_id, 4)

        job_manager.set_step(job_id, 4)
        _zip_output(vector_dir, threed_dir, os.path.join(output_dir, "output.zip"))
        job_manager.update_status(job_id, "done")

    except Exception as e:
        logger.exception("Pipeline failed for job %s", job_id)
        job_manager.set_error(job_id, str(e))


def _zip_output(vector_dir: str, threed_dir: str, zip_path: str):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in os.listdir(vector_dir):
            zf.write(os.path.join(vector_dir, fname), arcname=f"vector/{fname}")
        for fname in os.listdir(threed_dir):
            if fname.startswith("."):
                continue
            zf.write(os.path.join(threed_dir, fname), arcname=f"3d/{fname}")
