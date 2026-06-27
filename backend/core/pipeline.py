import logging
import os
import shutil
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

            # Vector retry — intensities 4, 6, 8 (higher than before)
            if 0 < vector_score and vector_score > target_score:
                vector_tmp = os.path.join(vector_dir, f".{stem}_vector_post.png")
                for attempt in range(max_retries):
                    if vector_score <= target_score:
                        break
                    intensity = min(10, 4 + attempt * 2)   # 4 → 6 → 8
                    logger.info(
                        "Vector retry %d/%d intensity=%d Hive=%.1f%%",
                        attempt + 1, max_retries, intensity, vector_score,
                    )
                    img.apply_threed_postprocess(vector_path, vector_tmp, intensity=intensity)
                    os.replace(vector_tmp, vector_path)
                    vector_score = hive.check(vector_path)

            # ── Step 2: Turnaround or legacy 3D ──────────────────────────
            job_manager.set_step(job_id, 2)

            if pipeline_mode == "turnaround":
                second_path = os.path.join(second_dir, f"{stem}_turnaround.png")
                second_score = _run_turnaround(
                    ai, img, hive, source_path, second_path, second_dir, stem,
                    config, target_score,
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

            # ── Step 3: Progress ──────────────────────────────────────────
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
) -> float:
    """
    5-view turnaround via FLUX Kontext (16:9).

    Post-process chain (stops as soon as Hive passes):
      1. apply_illustration_style: 16 colors + grain σ=1.0 + JPEG 93.
         Same chain as vector — no dots, clean flat look.
         Fast pass: works for images where FLUX generates in flat style.

      2. depth-guided: posterize FLUX output as color base, FLUX as depth reference.
         Same technique as depth-guided 3D — 100% algorithmic output pixels.
         Guaranteed < 5% Hive. Adds subtle shading (appropriate for reference sheets).

      3. cel-shader FS fallback (should rarely/never be needed after step 2).
    """
    # Prepare flat 16-color version as FLUX input (guides FLUX to flat illustration style)
    flux_input_path = os.path.join(work_dir, f".{stem}_turnaround_input.png")
    posterized_src = img._prepare_posterized(source_path, colors=16, dither=False)
    posterized_src.save(flux_input_path, "PNG")

    try:
        ai.generate_turnaround(flux_input_path, output_path)
    finally:
        if os.path.isfile(flux_input_path):
            os.remove(flux_input_path)

    # Keep a copy of the raw FLUX output as depth reference for step 2
    flux_ref = os.path.join(work_dir, f".{stem}_turnaround_flux.png")
    shutil.copy(output_path, flux_ref)
    tmp = os.path.join(work_dir, f".{stem}_turnaround_tmp.png")

    try:
        # ── Pass 1: illustration style (vector chain) ─────────────────────
        img.apply_illustration_style(output_path, tmp)
        os.replace(tmp, output_path)
        score = hive.check(output_path)
        logger.info("Turnaround illustration-style Hive: %.1f%%", score)
        if score < 0 or score <= target_score:
            return score

        # ── Pass 2: depth-guided (100% algorithmic pixels, same as 3D mode) ─
        # Uses raw FLUX as depth/normal reference; derives color palette from
        # FLUX posterized to 16 flat colors. Output pixels are 100% algorithmic
        # — same guarantee as depth-guided 3D (<5% Hive).
        posterized_flux = img._prepare_posterized(flux_ref, colors=16, dither=False)
        img.render_depth_guided_3d(
            posterized_flux,
            flux_ref,
            tmp,
            strength=0.7,    # subtle shading — appropriate for reference sheets
            light_grid=32,
            white_background=True,
        )
        os.replace(tmp, output_path)
        score = hive.check(output_path)
        logger.info("Turnaround depth-guided Hive: %.1f%%", score)
        if score < 0 or score <= target_score:
            return score

        # ── Pass 3: cel-shader FS (last resort, rarely needed) ───────────
        for colors in (12, 8):
            img.apply_cel_shader(output_path, tmp, colors=colors, dither=True, grain_sigma=3.0)
            os.replace(tmp, output_path)
            score = hive.check(output_path)
            logger.info("Turnaround cel-FS colors=%d Hive: %.1f%%", colors, score)
            if score < 0 or score <= target_score:
                return score

    finally:
        for p in (flux_ref, tmp):
            if os.path.isfile(p):
                os.remove(p)

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
        tmp = os.path.join(work_dir, f".{stem}_3d_cel.png")
        score = 100.0
        for cel_colors in (int(config.get("CEL_SHADER_COLORS", "24")), 16, 12):
            img.apply_cel_shader(output_path, tmp, colors=cel_colors)
            os.replace(tmp, output_path)
            score = hive.check(output_path)
            logger.info("Cel-shade colors=%d Hive: %.1f%%", cel_colors, score)
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
