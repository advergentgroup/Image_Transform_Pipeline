from flask import Blueprint, request, jsonify, send_file, render_template, current_app
from backend.core.job_manager import JobManager
from backend.core.pipeline import run_pipeline
from backend.utils.validators import validate_files
import threading
import os
import shutil

api_bp = Blueprint("api", __name__)
job_manager = JobManager()


@api_bp.route("/")
def index():
    return render_template("index.html", active_page="dashboard")


@api_bp.route("/new-job")
def new_job():
    return render_template("new_job.html", active_page="new_job")


@api_bp.route("/history")
def history():
    return render_template("history.html", active_page="history")


@api_bp.route("/api/upload", methods=["POST"])
def upload():
    """
    Accepts up to 10 JPG/PNG files.
    Returns: { job_id, file_count }
    """
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

    # Run pipeline in background thread (Celery in final version)
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=run_pipeline,
        args=(job_id, saved_paths, app.config, job_manager)
    )
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id, "file_count": len(saved_paths)})


@api_bp.route("/api/jobs")
def list_jobs():
    return jsonify({"jobs": job_manager.list_jobs()})


@api_bp.route("/api/stats")
def stats():
    return jsonify(job_manager.get_stats())


@api_bp.route("/api/status/<job_id>")
def status(job_id):
    """
    Returns current job status.
    { status, progress, total, results: [{filename, vector_pct, threed_pct, hive_score}] }
    """
    job = job_manager.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


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
