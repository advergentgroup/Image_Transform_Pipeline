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
      - Vector: 16-color posterize + gradient (Hive-safe, ~0-5%)
      - Turnaround: 5-view character sheet via FLUX Kontext (16:9) + cel-shader
    Pipeline mode: PIPELINE_MODE=turnaround (default) | legacy-3d
    """
    job_manager.update_status(job_id, "processing")

    ai = AIService(config)
    img = ImageService(config)
    hive = HivedetectService(config)

    unique_mode = config.get("UNIQUE_MODE", "pillow")
    pipeline_mode = str(config.get("PIPELINE_MODE", "turnaround")).lower()
    target_score = float(config.get("HIVEDETECT_TARGET_SCORE", "10.0"))
    max_retries = int(config.get("HIVEDETECT_MAX_RETRIES", "3"))

    output_dir = os.path.join(config["OUTPUT_FOLDER"], job_id)
    vector_dir = os.path.join(output_dir, "vector")
    second_dir = os.path.join(output_dir, "turnaround" if pipeline_mode == "turnaround" else "3d")
    os.makedirs(vector_dir, exist_ok=True)
    os.makedirs(second_dir, exist_ok=True)

    try:
        for image_path in image_paths:
            filename = os.path.basename(image_path)
            stem = os.path.splitext(filename)[0]

            source_path = image_path
            if unique_mode != "pillow":
                job_manager.set_step(job_id, 0)
                logger.info("AI uniquify (%s): %s", unique_mode, filename)
                source_path = ai.uniquify(image_path, output_dir)

            # ── Step 1: Vector ────────────────────────────────────────────
            job_manager.set_step(job_id, 1)
            vector_path = os.path.join(vector_dir, f"{stem}_vector.png")
            img.vectorize_with_gradient(source_path, vector_path)
            vector_score = hive.check(vector_path)
            logger.info("Vector Hive: %.1f%%", vector_score)

            # ── Step 2: Turnaround or legacy 3D ──────────────────────────
            job_manager.set_step(job_id, 2)

            if pipeline_mode == "turnaround":
                second_path = os.path.join(second_dir, f"{stem}_turnaround.png")
                second_score = _run_turnaround(
                    ai, img, hive, source_path, second_path, second_dir, stem,
                    config, target_score, max_retries,
                )
                second_key = "turnaround_file"
                second_file = f"{stem}_turnaround.png"
                second_hive_key = "hive_turnaround"
            else:
                second_path = os.path.join(second_dir, f"{stem}_3d.png")
                second_score = _run_legacy_3d(
                    ai, img, hive, source_path, second_path, second_dir, stem,
                    config, target_score,
                )
                second_key = "threed_file"
                second_file = f"{stem}_3d.png"
                second_hive_key = "hive_3d"

            # ── Step 3: Zip progress ──────────────────────────────────────
            job_manager.set_step(job_id, 3)
            job_manager.increment_progress(job_id, {
                "filename": filename,
                "vector_file": f"{stem}_vector.png",
                second_key: second_file,
                "hive_vector": vector_score,
                second_hive_key: second_score,
            })

            job = job_manager.get_job(job_id)
            if job and job["progress"] >= job["total"]:
                job_manager.set_step(job_id, 4)

        job_manager.set_step(job_id, 4)
        _zip_output(vector_dir, second_dir, os.path.join(output_dir, "output.zip"))
        job_manager.update_status(job_id, "done")

    except Exception as e:
        logger.exception("Pipeline failed for job %s", job_id)
        job_manager.set_error(job_id, str(e))


def _run_turnaround(
    ai: AIService,
    img: ImageService,
    hive: HivedetectService,
    source_path: str,
    output_path: str,
    work_dir: str,
    stem: str,
    config: dict,
    target_score: float,
    max_retries: int,
) -> float:
    """
    5-view turnaround sheet via FLUX Kontext (16:9).
    Input: posterized flat version of the source (mimics Illustrator pre-process).
    Post-process: cel shader retry loop for Hive reduction.
    """
    # Prepare a flat 16-color version of source as FLUX input.
    # Flat illustration style guides FLUX to generate in illustrator/cartoon mode
    # which tends to score better on Hive than photorealistic renders.
    flux_input_path = os.path.join(work_dir, f".{stem}_turnaround_input.png")
    posterized = img._prepare_posterized(source_path, colors=16, dither=False)
    posterized.save(flux_input_path, "PNG")

    try:
        ai.generate_turnaround(flux_input_path, output_path)
    finally:
        if os.path.isfile(flux_input_path):
            os.remove(flux_input_path)

    # Cel-shader retry loop — quantize to flat colors to reduce AI fingerprint
    cel_colors_list = [
        int(config.get("CEL_SHADER_COLORS", "24")),
        16,
        12,
    ]
    tmp_path = os.path.join(work_dir, f".{stem}_turnaround_cel.png")
    score = hive.check(output_path)
    logger.info("Turnaround raw Hive: %.1f%%", score)

    if score > target_score:
        for attempt, cel_colors in enumerate(cel_colors_list):
            img.apply_cel_shader(output_path, tmp_path, colors=cel_colors)
            os.replace(tmp_path, output_path)
            score = hive.check(output_path)
            logger.info(
                "Cel-shade attempt %d colors=%d → Hive %.1f%%",
                attempt + 1, cel_colors, score,
            )
            if score < 0 or score <= target_score:
                break

    return score


def _run_legacy_3d(
    ai: AIService,
    img: ImageService,
    hive: HivedetectService,
    source_path: str,
    output_path: str,
    work_dir: str,
    stem: str,
    config: dict,
    target_score: float,
) -> float:
    """Legacy depth-guided 3D mode (kept for backward compatibility)."""
    threed_mode = str(config.get("THREED_MODE", "kontext")).lower()

    if threed_mode == "depth-guided":
        depth_colors = int(config.get("DEPTH_GUIDED_COLORS", "48"))
        posterized = img._prepare_posterized(source_path, colors=depth_colors, dither=False)
        kontext_ref = os.path.join(work_dir, f".{stem}_kontext_ref.png")
        ai.transform_3d(source_path, kontext_ref)
        img.render_depth_guided_3d(
            posterized,
            kontext_ref,
            output_path,
            strength=float(config.get("DEPTH_GUIDED_STRENGTH", "1.5")),
            light_grid=int(config.get("DEPTH_GUIDED_GRID", "32")),
            white_background=str(config.get("THREED_WHITE_BACKGROUND", "0")).lower()
            in ("1", "true", "yes"),
        )
        if os.path.isfile(kontext_ref):
            os.remove(kontext_ref)
        return hive.check(output_path)
    else:
        ai.transform_3d(source_path, output_path)
        cel_colors_list = [int(config.get("CEL_SHADER_COLORS", "24")), 16, 12]
        tmp = os.path.join(work_dir, f".{stem}_3d_cel.png")
        score = 100.0
        for attempt, cel_colors in enumerate(cel_colors_list):
            img.apply_cel_shader(output_path, tmp, colors=cel_colors)
            os.replace(tmp, output_path)
            score = hive.check(output_path)
            logger.info("Cel-shade attempt %d colors=%d → Hive %.1f%%", attempt + 1, cel_colors, score)
            if score < 0 or score <= target_score:
                break
        return score


def _zip_output(first_dir: str, second_dir: str, zip_path: str):
    folder_name = os.path.basename(second_dir)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in os.listdir(first_dir):
            if not fname.startswith("."):
                zf.write(os.path.join(first_dir, fname), arcname=f"vector/{fname}")
        for fname in os.listdir(second_dir):
            if not fname.startswith("."):
                zf.write(os.path.join(second_dir, fname), arcname=f"{folder_name}/{fname}")
