"""Startup checks for Python version and vtracer availability."""
import logging
import os
import subprocess
import sys
import tempfile

logger = logging.getLogger(__name__)

_VTRACER_PROBE = """
import sys
import vtracer
vtracer.convert_image_to_svg_py(sys.argv[1], sys.argv[2], colormode="color")
"""


def check_runtime() -> None:
    logger.info("Python executable: %s", sys.executable)

    version = sys.version_info
    if version >= (3, 14):
        logger.warning(
            "Python %s.%s: vtracer native module crashes on 3.14+. "
            "Use .\\run.ps1 or py app.py (auto-switches to .venv).",
            version.major,
            version.minor,
        )

    if probe_resvg_py():
        logger.info("resvg_py OK (SVG rasterization, no Cairo)")
    else:
        logger.error(
            "resvg_py missing — pip install -r requirements.txt in .venv"
        )

    if probe_vtracer():
        logger.info("vtracer OK (Python %s)", sys.version.split()[0])
    else:
        logger.warning(
            "vtracer unavailable — vector archive will use gradient fallback. "
            "Use .\\run.ps1 to create/run the Python 3.12 virtualenv."
        )


def probe_resvg_py() -> bool:
    try:
        import resvg_py  # noqa: F401

        return True
    except ImportError:
        return False


def probe_vtracer() -> bool:
    png = svg = None
    try:
        from PIL import Image

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            png = tmp.name
        Image.new("RGB", (8, 8), "red").save(png)
        svg = png.replace(".png", ".svg")

        result = subprocess.run(
            [sys.executable, "-c", _VTRACER_PROBE, png, svg],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return result.returncode == 0 and os.path.isfile(svg)
    except Exception:
        return False
    finally:
        for path in (png, svg):
            if path and os.path.isfile(path):
                os.remove(path)
