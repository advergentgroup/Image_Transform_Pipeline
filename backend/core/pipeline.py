import logging
import os
import zipfile

from backend.core.job_manager import JobManager
from backend.services.ai_service import AIService
from backend.services.hivedetect_service import HivedetectService
from backend.services.image_service import ImageService

logger = logging.getLogger(__name__)


def run_pipeline(job_id: str, image_paths: list, config: dict, job_manager: JobManager):
    job_manager.update_status(job_id, "processing")

    ai = AIService(config)
    img = ImageService(config)
    hive = HivedetectService(config)

    unique_mode = config.get("UNIQUE_MODE", "flux-redux")
    hive_target = float(config.get("HIVEDETECT_TARGET_SCORE", 10))
    hive_max_retries = int(config.get("HIVEDETECT_MAX_RETRIES", 8))

    output_dir = os.path.join(config["OUTPUT_FOLDER"], job_id)
    vector_dir = os.path.join(output_dir, "vector")
    threed_dir = os.path.join(output_dir, "3d")
    os.makedirs(vector_dir, exist_ok=True)
    os.makedirs(threed_dir, exist_ok=True)

    try:
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            stem = os.path.splitext(filename)[0]

            job_manager.set_step(job_id, 0)
            master_path = os.path.join(output_dir, f"master_{stem}.png")
            img.apply_uniquify_filters(image_path, master_path)

            if unique_mode != "pillow":
                logger.info("AI uniquify on master (%s): %s", unique_mode, filename)
                uniquified = ai.uniquify(master_path, output_dir)
                os.replace(uniquified, master_path)

            job_manager.set_step(job_id, 1)
            vector_path = os.path.join(vector_dir, f"{stem}_vector.png")
            img.vectorize_with_gradient(master_path, vector_path)

            job_manager.set_step(job_id, 2)
            threed_path = os.path.join(threed_dir, f"{stem}_3d.png")
            ai.transform_3d(master_path, threed_path)

            threed_tmp = os.path.join(threed_dir, f".{stem}_3d_post.png")
            img.apply_threed_postprocess(
                threed_path, threed_tmp, intensity=1, blend_source=master_path
            )
            os.replace(threed_tmp, threed_path)

            job_manager.set_step(job_id, 3)
            vector_score = hive.check(vector_path)
            threed_score = hive.check(threed_path)

            attempt = 1
            while (
                threed_score > hive_target
                and threed_score >= 0
                and attempt < hive_max_retries
            ):
                attempt += 1
                logger.info(
                    "3D Hive %.1f%% > %.1f%% — humanize pass %d/%d for %s",
                    threed_score,
                    hive_target,
                    attempt,
                    hive_max_retries,
                    filename,
                )
                threed_tmp = os.path.join(threed_dir, f".{stem}_3d_retry.png")
                img.apply_threed_postprocess(
                    threed_path,
                    threed_tmp,
                    intensity=attempt,
                    blend_source=master_path,
                )
                os.replace(threed_tmp, threed_path)
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
