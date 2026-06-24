from flask import Blueprint, request, jsonify, send_file, render_template, current_app
from werkzeug.utils import secure_filename
from backend.core.job_manager import JobManager
from backend.core.pipeline import run_pipeline
from backend.core.settings_store import PROMPT_KEYS, load_prompts, save_prompts
from backend.utils.validators import validate_files
from config import Config
import threading
import os
import shutil

api_bp = Blueprint("api", __name__)
job_manager = JobManager()


def init_app(app):
    """Load saved prompts into app config."""
    prompts = load_prompts(app.config["SETTINGS_FILE"])
    for key, value in prompts.items():
        app.config[key] = value


def _pipeline_config(app) -> dict:
    cfg = {k: getattr(Config, k) for k in dir(Config) if k.isupper()}
    for key, value in app.config.items():
        if isinstance(key, str) and key.isupper():
            cfg[key] = value
    return cfg


@api_bp.route("/")
def index():
    return render_template("index.html", active_page="dashboard")


@api_bp.route("/new-job")
def new_job():
    return render_template("new_job.html", active_page="new_job")


@api_bp.route("/history")
def history():
    return render_template("history.html", active_page="history")


@api_bp.route("/settings")
def settings_page():
    return render_template("settings.html", active_page="settings")


@api_bp.route("/api/upload", methods=["POST"])
def upload():
    files = request.files.getlist("images")

    error = validate_files(files, current_app.config)
    if error:
        return jsonify({"error": error}), 400

    job_id = job_manager.create_job(len(files))

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], job_id)
    os.makedirs(upload_dir, exist_ok=True)

    saved_paths = []
    for f in files:
        path = os.path.join(upload_dir, f.filename)
        f.save(path)
        saved_paths.append(path)

    job_manager.set_files(job_id, [os.path.basename(p) for p in saved_paths])

    app = current_app._get_current_object()
    thread = threading.Thread(
        target=run_pipeline,
        args=(job_id, saved_paths, _pipeline_config(app), job_manager),
    )
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id, "file_count": len(saved_paths)})


@api_bp.route("/api/jobs")
def list_jobs():
    job_manager.sync_all_files_from_disk(current_app.config["UPLOAD_FOLDER"])
    return jsonify({"jobs": job_manager.list_jobs()})


@api_bp.route("/api/stats")
def stats():
    return jsonify(job_manager.get_stats())


@api_bp.route("/api/status/<job_id>")
def status(job_id):
    job = job_manager.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    job_manager.sync_files_from_disk(job_id, current_app.config["UPLOAD_FOLDER"])
    job = job_manager.get_job(job_id)
    return jsonify(job)


@api_bp.route("/api/jobs/<job_id>/file/<path:filename>")
def job_file(job_id, filename):
    job = job_manager.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    job_manager.sync_files_from_disk(job_id, current_app.config["UPLOAD_FOLDER"])
    job = job_manager.get_job(job_id)

    safe_name = secure_filename(os.path.basename(filename))
    if not safe_name or safe_name not in job.get("files", []):
        return jsonify({"error": "File not found"}), 404

    path = os.path.join(current_app.config["UPLOAD_FOLDER"], job_id, safe_name)
    if not os.path.isfile(path):
        return jsonify({"error": "File not found"}), 404

    return send_file(path)


@api_bp.route("/api/download/<job_id>")
def download(job_id):
    job = job_manager.get_job(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "Job not ready"}), 404

    output_dir = current_app.config["OUTPUT_FOLDER"]
    zip_path = os.path.join(output_dir, job_id, "output.zip")

    if not os.path.exists(zip_path):
        return jsonify({"error": "Archive not found"}), 404

    filename = f"images_{job_id[:8]}.zip"
    return send_file(zip_path, as_attachment=True, download_name=filename)


@api_bp.route("/api/jobs/<job_id>", methods=["DELETE"])
def delete_job(job_id):
    job = job_manager.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], job_id)
    output_dir = os.path.join(current_app.config["OUTPUT_FOLDER"], job_id)
    for folder in (upload_dir, output_dir):
        if os.path.isdir(folder):
            shutil.rmtree(folder, ignore_errors=True)

    job_manager.delete_job(job_id)
    return jsonify({"ok": True})


@api_bp.route("/api/settings", methods=["GET"])
def get_settings():
    prompts = load_prompts(current_app.config["SETTINGS_FILE"])
    return jsonify({"prompts": prompts})


@api_bp.route("/api/settings", methods=["PUT"])
def update_settings():
    data = request.get_json(silent=True) or {}
    prompts_in = data.get("prompts", data)
    if not isinstance(prompts_in, dict):
        return jsonify({"error": "Invalid payload"}), 400

    saved = save_prompts(current_app.config["SETTINGS_FILE"], prompts_in)
    for key in PROMPT_KEYS:
        if key in saved:
            current_app.config[key] = saved[key]

    return jsonify({"ok": True, "prompts": saved})
