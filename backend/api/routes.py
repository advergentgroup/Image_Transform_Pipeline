from flask import Blueprint, request, jsonify, send_file, render_template, current_app
from backend.core.job_manager import JobManager
from backend.core.pipeline import run_pipeline
from backend.utils.validators import validate_files
import threading
import os

api_bp = Blueprint("api", __name__)
job_manager = JobManager()


@api_bp.route("/")
def index():
    return render_template("index.html")


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


@api_bp.route("/api/download/<job_id>/<archive_type>")
def download(job_id, archive_type):
    """
    archive_type: 'vector' | '3d'
    Returns ZIP file for download.
    """
    if archive_type not in ("vector", "3d"):
        return jsonify({"error": "Invalid archive type"}), 400

    job = job_manager.get_job(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "Job not ready"}), 404

    output_dir = current_app.config["OUTPUT_FOLDER"]
    zip_path = os.path.join(output_dir, job_id, f"{archive_type}.zip")

    if not os.path.exists(zip_path):
        return jsonify({"error": "Archive not found"}), 404

    filename = f"images_{archive_type}_{job_id[:8]}.zip"
    return send_file(zip_path, as_attachment=True, download_name=filename)
