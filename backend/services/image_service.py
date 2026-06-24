"""
ImageService — Pillow-фільтри для унікалізації + vtracer векторизація.
"""
import hashlib
import logging
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageEnhance
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

logger = logging.getLogger(__name__)

_VTRACER_SCRIPT = """
import sys
import vtracer

vtracer.convert_image_to_svg_py(
    sys.argv[1],
    sys.argv[2],
    colormode="color",
    filter_speckle=4,
    color_precision=6,
    layer_difference=16,
    mode="spline",
    corner_threshold=60,
    length_threshold=4.0,
    splice_threshold=45,
    path_precision=3,
)
"""


class ImageService:
    def __init__(self, config: dict):
        self.config = config

    def apply_uniquify_filters(self, input_path: str, output_path: str):
        """
        Deterministic micro-adjustments: hue, saturation, contrast, sharpness.
        Changes pixel fingerprint without warping faces (unlike SD img2img).
        """
        with open(input_path, "rb") as f:
            seed = int(hashlib.md5(f.read()).hexdigest()[:8], 16)

        img = Image.open(input_path).convert("RGB")

        img = ImageEnhance.Color(img).enhance(0.96 + (seed % 9) * 0.01)
        img = ImageEnhance.Contrast(img).enhance(0.97 + (seed % 7) * 0.01)
        img = ImageEnhance.Brightness(img).enhance(0.98 + (seed % 5) * 0.01)
        img = ImageEnhance.Sharpness(img).enhance(1.0 + (seed % 6) * 0.02)

        hsv = np.array(img.convert("HSV"))
        hue_shift = ((seed % 11) - 5) * 2  # ±10°
        hsv[:, :, 0] = (hsv[:, :, 0].astype(np.int16) + hue_shift) % 256
        img = Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, "PNG")

    def vectorize_with_gradient(self, input_path: str, output_path: str):
        """
        1. Векторизація через vtracer (окремий subprocess — не вбиває Flask при segfault)
        2. Растеризація SVG → PNG (svglib + reportlab)
        3. Накладення радіального градієнтного фону (#E0FFFF → #40E0D0)
        """
        work_dir = os.path.dirname(output_path) or "."
        stem = os.path.splitext(os.path.basename(input_path))[0]
        svg_path = os.path.join(work_dir, f".{stem}_vec.svg")
        raw_png_path = os.path.join(work_dir, f".{stem}_vec_raw.png")

        try:
            if not self._run_vtracer_subprocess(input_path, svg_path):
                logger.warning("vtracer failed for %s — using gradient fallback", input_path)
                self._fallback_composite(input_path, output_path)
                return

            self._svg_to_png(svg_path, raw_png_path, scale=2.0)

            vec_img = Image.open(raw_png_path).convert("RGBA")
            vec_img = self._white_to_transparent(vec_img)

            width, height = vec_img.size
            bg = self._make_radial_gradient(
                width,
                height,
                center_color=(224, 255, 255),  # #E0FFFF
                edge_color=(64, 224, 208),    # #40E0D0
            )
            bg.paste(vec_img, (0, 0), vec_img)
            bg.convert("RGB").save(output_path, "PNG")
        finally:
            for path in (svg_path, raw_png_path):
                if os.path.exists(path):
                    os.remove(path)

    def _run_vtracer_subprocess(self, input_path: str, svg_path: str) -> bool:
        """Isolate vtracer in a child process (native crash must not kill Flask)."""
        try:
            result = subprocess.run(
                [sys.executable, "-c", _VTRACER_SCRIPT, input_path, svg_path],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.error("vtracer timed out for %s", input_path)
            return False

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            logger.error("vtracer exit %s for %s: %s", result.returncode, input_path, detail)
            return False

        if not os.path.isfile(svg_path):
            logger.error("vtracer produced no SVG for %s", input_path)
            return False

        return True

    def _fallback_composite(self, input_path: str, output_path: str):
        """Simple composite when vtracer is unavailable (e.g. Python 3.14 on Windows)."""
        img = Image.open(input_path).convert("RGBA")
        width, height = img.size
        bg = self._make_radial_gradient(
            width,
            height,
            center_color=(224, 255, 255),
            edge_color=(64, 224, 208),
        )
        bg.paste(img, (0, 0), img)
        bg.convert("RGB").save(output_path, "PNG")

    def _svg_to_png(self, svg_path: str, png_path: str, scale: float = 2.0):
        drawing = svg2rlg(svg_path)
        if drawing is None:
            raise RuntimeError(f"Could not parse SVG: {svg_path}")

        if scale != 1.0:
            drawing.width *= scale
            drawing.height *= scale
            drawing.scale(scale, scale)

        renderPM.drawToFile(drawing, png_path, fmt="PNG")

    def _white_to_transparent(self, img: Image.Image, tolerance: int = 30) -> Image.Image:
        """Make near-white pixels transparent so gradient shows through."""
        data = np.array(img)
        r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]
        white_mask = (r > 255 - tolerance) & (g > 255 - tolerance) & (b > 255 - tolerance)
        data[:, :, 3] = np.where(white_mask, 0, data[:, :, 3])
        return Image.fromarray(data, "RGBA")

    def _make_radial_gradient(
        self,
        width: int,
        height: int,
        center_color: tuple,
        edge_color: tuple,
    ) -> Image.Image:
        """Create radial gradient background image."""
        cx, cy = width // 2, height // 2
        max_dist = ((cx**2 + cy**2) ** 0.5)

        img_array = np.zeros((height, width, 3), dtype=np.uint8)
        y_indices, x_indices = np.mgrid[0:height, 0:width]

        dist = np.sqrt((x_indices - cx) ** 2 + (y_indices - cy) ** 2)
        t = np.clip(dist / max_dist, 0, 1)

        for c in range(3):
            img_array[:, :, c] = (
                center_color[c] * (1 - t) + edge_color[c] * t
            ).astype(np.uint8)

        return Image.fromarray(img_array, "RGB")
