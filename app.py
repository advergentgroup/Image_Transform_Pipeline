import os
import sys
from pathlib import Path


def _venv_python() -> Path | None:
    root = Path(__file__).resolve().parent
    if sys.platform == "win32":
        candidate = root / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = root / ".venv" / "bin" / "python"
    return candidate if candidate.is_file() else None


def _reexec_in_venv_if_needed() -> None:
    """Always run in project .venv when present (vtracer + resvg_py deps)."""
    if os.environ.get("IMAGE_TRANSFORM_VENV"):
        return

    venv_py = _venv_python()
    if venv_py is None:
        return

    if Path(sys.executable).resolve() == venv_py.resolve():
        os.environ["IMAGE_TRANSFORM_VENV"] = "1"
        return

    env = os.environ.copy()
    env["IMAGE_TRANSFORM_VENV"] = "1"

    if sys.platform == "win32":
        import subprocess

        raise SystemExit(subprocess.call([str(venv_py), *sys.argv], env=env))

    os.execve(str(venv_py), [str(venv_py), *sys.argv], env)


_reexec_in_venv_if_needed()

from flask import Flask
from backend.api.routes import api_bp
from backend.utils.runtime_check import check_runtime
from config import Config
import logging

logging.basicConfig(level=logging.INFO)


def create_app(config=Config):
    app = Flask(
        __name__,
        template_folder="frontend/templates",
        static_folder="frontend/static",
    )
    app.config.from_object(config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)

    app.register_blueprint(api_bp)

    return app


app = create_app()
check_runtime()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port, use_reloader=False)
