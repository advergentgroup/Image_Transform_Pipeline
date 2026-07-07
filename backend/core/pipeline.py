import logging
import os
import shutil
import threading
import zipfile

from backend.core.job_manager import JobManager
from backend.utils.image_output import (
    find_index_path,
    image_index,
    is_output_image,
    output_filename,
)
from backend.services.ai_service import AIService, ReplicateBalanceError, ReplicateThrottleError
from backend.services.hivedetect_service import HivedetectService

logger = logging.getLogger(__name__)

_REPLICATE_STOP_ERRORS = (ReplicateBalanceError, ReplicateThrottleError)
_zip_lock = threading.Lock()


def run_pipelined_job(job_id: str, config: dict, job_manager: JobManager):
    """Reference + turnaround pipelined: turnaround #N starts in background while #N+1 ref runs."""
    job_manager.update_status(job_id, "processing")
    job_manager.set_phase(job_id, "pipelined")

    ai = AIService(config)
    output_dir = os.path.join(config["OUTPUT_FOLDER"], job_id)
    upload_dir = os.path.join(config["UPLOAD_FOLDER"], job_id)
    reference_dir = os.path.join(output_dir, "reference")
    turnaround_dir = os.path.join(output_dir, "turnaround")
    os.makedirs(reference_dir, exist_ok=True)
    os.makedirs(turnaround_dir, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    job = job_manager.get_job(job_id)
    total = job["total"] if job else 1
    start_index = job.get("reference_done", 0) if job else 0

    preview_files = list(job.get("files", [])) if job else []
    style_refs = _list_style_refs(upload_dir)
    catalog_order = list(job.get("catalog_order") or [])
    if not catalog_order:
        catalog_order = AIService.shuffle_catalog_prompt_indices(total)
        job_manager.set_catalog_order(job_id, catalog_order)

    stopped_early = False
    warning = None
    turnaround_threads: list[threading.Thread] = []

    try:
        for index in range(start_index + 1, total + 1):
            ref_name = output_filename(index, config)
            ref_output = os.path.join(reference_dir, ref_name)
            preview_path = os.path.join(upload_dir, ref_name)
            style_path = style_refs[(index - 1) % len(style_refs)] if style_refs else None

            job_manager.set_step(job_id, 0)
            if style_path:
                logger.info(
                    "Generating reference %s/%s (style: %s)",
                    index,
                    total,
                    os.path.basename(style_path),
                )
            else:
                logger.info("Generating reference %s/%s", index, total)
            catalog_slot = catalog_order[index - 1]
            catalog_prompt = ai.product_reference_prompt_for_catalog_slot(catalog_slot)
            if catalog_prompt:
                logger.info(
                    "Catalog prompt image %s/%s (catalog #%s): %s",
                    index,
                    total,
                    catalog_slot,
                    catalog_prompt[:80],
                )
            try:
                ai.generate_product_reference(
                    ref_output,
                    prompt=catalog_prompt,
                    style_ref_path=style_path,
                    catalog_mode=catalog_prompt is not None,
                )
            except _REPLICATE_STOP_ERRORS as exc:
                stopped_early = True
                warning = str(exc)
                logger.warning("Replicate stop at reference %s: %s", index, exc)
                break

            shutil.copy2(ref_output, preview_path)
            if ref_name not in preview_files:
                preview_files.append(ref_name)

            job_manager.increment_progress(job_id, {
                "index": index,
                "filename": ref_name,
                "reference_file": ref_name,
                "turnaround_file": None,
            })
            job_manager.set_reference_done(job_id, index)
            _zip_output(reference_dir, turnaround_dir, os.path.join(output_dir, "output.zip"))

            thread = threading.Thread(
                target=_turnaround_for_index,
                args=(job_id, index, config, job_manager),
                daemon=True,
            )
            thread.start()
            turnaround_threads.append(thread)

            if index < total:
                ai.wait_between_requests()

        for thread in turnaround_threads:
            thread.join()

        job_manager.set_files(job_id, preview_files)
        _zip_output(reference_dir, turnaround_dir, os.path.join(output_dir, "output.zip"))

        job = job_manager.get_job(job_id) or {}
        ref_done = job.get("reference_done", 0)
        turn_done = job.get("turnaround_done", 0)

        if ref_done == 0:
            job_manager.set_error(
                job_id,
                warning or "Could not generate any references. Check Replicate balance.",
            )
            return

        if warning:
            job_manager.set_warning(job_id, warning)

        if turn_done == 0:
            job_manager.set_error(
                job_id,
                warning or "Could not generate any turnaround sheets.",
            )
            return

        job_manager.set_step(job_id, 3)
        job_manager.update_status(job_id, "done")

    except Exception as e:
        logger.exception("Pipelined job failed for %s", job_id)
        for thread in turnaround_threads:
            thread.join()
        job = job_manager.get_job(job_id) or {}
        if (job.get("turnaround_done") or 0) > 0 or (job.get("reference_done") or 0) > 0:
            job_manager.set_warning(job_id, str(e))
            _zip_output(reference_dir, turnaround_dir, os.path.join(output_dir, "output.zip"))
            job_manager.update_status(job_id, "done")
        else:
            job_manager.set_error(job_id, str(e))


def run_turnaround_phase(job_id: str, config: dict, job_manager: JobManager):
    """Legacy phase 2 — turnaround for jobs stuck at awaiting_continue."""
    job = job_manager.get_job(job_id)
    if not job:
        return
    if job["status"] not in ("awaiting_continue", "processing"):
        return

    job_manager.update_status(job_id, "processing")
    job_manager.set_phase(job_id, "turnaround")
    job_manager.set_step(job_id, 1)

    output_dir = os.path.join(config["OUTPUT_FOLDER"], job_id)
    reference_dir = os.path.join(output_dir, "reference")
    turnaround_dir = os.path.join(output_dir, "turnaround")
    os.makedirs(turnaround_dir, exist_ok=True)

    indices = _reference_indices(reference_dir)
    if not indices:
        job_manager.set_error(job_id, "No reference images found to process.")
        return

    existing_turn = sum(
        1 for index in indices
        if find_index_path(turnaround_dir, index, config)
    )
    job_manager.set_turnaround_done(job_id, existing_turn)

    threads = []
    for index in indices:
        turn_path = os.path.join(turnaround_dir, output_filename(index, config))
        if find_index_path(turnaround_dir, index, config):
            continue
        thread = threading.Thread(
            target=_turnaround_for_index,
            args=(job_id, index, config, job_manager),
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    _zip_output(reference_dir, turnaround_dir, os.path.join(output_dir, "output.zip"))
    turnaround_count = job_manager.get_job(job_id).get("turnaround_done", 0)
    if turnaround_count == 0:
        job_manager.set_error(job_id, "Could not generate any turnaround sheets.")
        return
    job_manager.set_step(job_id, 3)
    job_manager.update_status(job_id, "done")


def _turnaround_for_index(job_id: str, index: int, config: dict, job_manager: JobManager):
    output_dir = os.path.join(config["OUTPUT_FOLDER"], job_id)
    reference_dir = os.path.join(output_dir, "reference")
    turnaround_dir = os.path.join(output_dir, "turnaround")
    ref_name = output_filename(index, config)
    ref_path = find_index_path(reference_dir, index, config)
    turn_path = os.path.join(turnaround_dir, ref_name)

    if find_index_path(turnaround_dir, index, config):
        logger.info("Turnaround already exists, skip: %s", ref_name)
        job_manager.increment_turnaround_done(job_id)
        return

    if not ref_path:
        logger.warning("Reference missing for turnaround #%s", index)
        job_manager.set_warning(job_id, f"Reference #{index} not found for turnaround.")
        return

    ai = AIService(config)
    hive = HivedetectService(config)

    try:
        job_manager.set_step(job_id, 2)
        logger.info("Generating turnaround #%s", index)
        ai.generate_turnaround(ref_path, turn_path)

        ref_score = hive.check(ref_path)
        turn_score = hive.check(turn_path)
        logger.info(
            "Hive #%s — reference: %.1f%%, turnaround: %.1f%%",
            index,
            ref_score,
            turn_score,
        )

        job_manager.update_result(job_id, index, {
            "index": index,
            "filename": ref_name,
            "reference_file": ref_name,
            "turnaround_file": ref_name,
            "hive_reference": ref_score,
            "hive_turnaround": turn_score,
        })
        job_manager.increment_turnaround_done(job_id)
        _zip_output(reference_dir, turnaround_dir, os.path.join(output_dir, "output.zip"))
    except _REPLICATE_STOP_ERRORS as exc:
        logger.warning("Replicate stop at turnaround #%s: %s", index, exc)
        job_manager.set_warning(job_id, str(exc))
    except Exception as exc:
        logger.exception("Turnaround failed for #%s job %s", index, job_id)
        job_manager.set_warning(job_id, str(exc))


def _list_style_refs(upload_dir: str) -> list[str]:
    style_dir = os.path.join(upload_dir, "style_refs")
    if not os.path.isdir(style_dir):
        return []
    names = sorted(
        n for n in os.listdir(style_dir)
        if n.lower().endswith((".png", ".jpg", ".jpeg")) and not n.startswith(".")
    )
    return [os.path.join(style_dir, n) for n in names]


def _reference_indices(reference_dir: str) -> list[int]:
    if not os.path.isdir(reference_dir):
        return []
    indices = []
    for name in os.listdir(reference_dir):
        if name.startswith("."):
            continue
        idx = image_index(name)
        if idx is not None:
            indices.append(idx)
    return sorted(indices)


def _zip_output(reference_dir: str, turnaround_dir: str | None, zip_path: str):
    with _zip_lock:
        folders = [(reference_dir, "reference")]
        if turnaround_dir and os.path.isdir(turnaround_dir):
            folders.append((turnaround_dir, "turnaround"))

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for folder, prefix in folders:
                if not os.path.isdir(folder):
                    continue
                names = [
                    f for f in os.listdir(folder)
                    if is_output_image(f)
                ]
                names.sort(key=lambda n: image_index(n) or n)
                for fname in names:
                    zf.write(os.path.join(folder, fname), arcname=f"{prefix}/{fname}")
