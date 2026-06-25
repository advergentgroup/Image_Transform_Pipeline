"""
ImageService — Pillow-фільтри для унікалізації + vtracer векторизація.
"""
import hashlib
import io
import logging
import os
import subprocess
import sys

import numpy as np
import resvg_py
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger(__name__)

_VECTOR_COLORS_DEFAULT = 16


class ImageService:
    def __init__(self, config: dict):
        self.config = config
        self.filter_strength = float(config.get("UNIQUIFY_FILTER_STRENGTH", "1.0"))
        self.vector_colors = int(config.get("VECTOR_TRACE_COLORS", _VECTOR_COLORS_DEFAULT))
        self.vector_noise = int(config.get("VECTOR_TRACE_NOISE", 4))
        self.vector_mode = config.get("VECTOR_MODE", "posterize").lower()

    def _vtracer_script(self) -> str:
        # Smooth spline trace for clean cartoon art (Illustrator 16-color limited palette)
        noise = max(2, min(self.vector_noise, 20))
        return f"""
import sys
import vtracer

vtracer.convert_image_to_svg_py(
    sys.argv[1],
    sys.argv[2],
    colormode="color",
    filter_speckle={noise},
    color_precision=5,
    layer_difference=16,
    mode="spline",
    corner_threshold=60,
    length_threshold=4.0,
    splice_threshold=45,
    path_precision=3,
)
"""

    def apply_uniquify_filters(self, input_path: str, output_path: str):
        """
        Visible color/noise adjustments — changes fingerprint while keeping likeness.
        Strength scales via UNIQUIFY_FILTER_STRENGTH (default 1.0).
        """
        with open(input_path, "rb") as f:
            seed = int(hashlib.md5(f.read()).hexdigest()[:8], 16)

        strength = max(0.5, self.filter_strength)
        img = Image.open(input_path).convert("RGB")

        color_delta = 0.04 * strength
        contrast_delta = 0.05 * strength
        brightness_delta = 0.04 * strength
        sharp_delta = 0.06 * strength

        img = ImageEnhance.Color(img).enhance(1.0 + ((seed % 9) - 4) * color_delta)
        img = ImageEnhance.Contrast(img).enhance(1.0 + ((seed % 7) - 3) * contrast_delta)
        img = ImageEnhance.Brightness(img).enhance(1.0 + ((seed % 5) - 2) * brightness_delta)
        img = ImageEnhance.Sharpness(img).enhance(1.0 + (seed % 6) * sharp_delta)

        hsv = np.array(img.convert("HSV"))
        hue_shift = int(((seed % 15) - 7) * 3 * strength)  # ±21° at strength 1
        hsv[:, :, 0] = (hsv[:, :, 0].astype(np.int16) + hue_shift) % 256
        sat_boost = 1.0 + ((seed % 5) - 2) * 0.03 * strength
        hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.float32) * sat_boost, 0, 255).astype(np.uint8)
        img = Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")

        rng = np.random.default_rng(seed)
        arr = np.array(img, dtype=np.float32)
        noise_sigma = 0.4 + strength * 0.6
        arr += rng.normal(0, noise_sigma, arr.shape)
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr, "RGB")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, "PNG", optimize=True)

    def strip_image_metadata(self, input_path: str, output_path: str):
        """Re-save without EXIF/C2PA/ICC — no visual degradation."""
        img = Image.open(input_path).convert("RGB")
        clean = Image.fromarray(np.array(img, dtype=np.uint8), "RGB")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        clean.save(output_path, format="PNG", optimize=True)

    def _prepare_posterized(self, input_path: str) -> Image.Image:
        """16-color flat art on white — shared base for vector and pseudo-3D."""
        img = Image.open(input_path).convert("RGB")
        width, height = img.size

        max_side = 2048
        if max(width, height) > max_side:
            scale = max_side / max(width, height)
            img = img.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.Resampling.LANCZOS,
            )

        img = ImageOps.autocontrast(img, cutoff=1)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.6))

        colors = max(4, min(self.vector_colors, 32))
        return img.quantize(
            colors=colors,
            method=Image.Quantize.MEDIANCUT,
            dither=Image.Dither.NONE,
        ).convert("RGB")

    def _composite_on_gradient(self, posterized: Image.Image) -> Image.Image:
        width, height = posterized.size
        vec_rgba = self._white_background_to_rgba(posterized, tolerance=28)
        bg = self._make_radial_gradient(
            width,
            height,
            center_color=(224, 255, 255),
            edge_color=(64, 224, 208),
        )
        bg.paste(vec_rgba, (0, 0), vec_rgba)
        return bg.convert("RGB")

    @staticmethod
    def _blur_array(arr: np.ndarray, radius: float) -> np.ndarray:
        return np.array(
            Image.fromarray(arr.astype(np.uint8)).filter(
                ImageFilter.GaussianBlur(radius=radius)
            ),
            dtype=np.float32,
        )

    def _coarse_light_map(
        self,
        reference_path: str,
        size: tuple[int, int],
        grid: int,
    ) -> np.ndarray:
        """
        Extract very coarse luminance ratios from a Kontext render.
        Downsampled enough to guide shading without copying AI pixel fingerprints.
        """
        ref = Image.open(reference_path).convert("RGB").resize(size, Image.Resampling.LANCZOS)
        lum = np.array(ref, dtype=np.float32).mean(axis=2)
        grid = max(8, min(grid, 64))
        small = Image.fromarray(lum.astype(np.uint8)).resize(
            (grid, grid), Image.Resampling.BILINEAR
        )
        coarse = np.array(
            small.resize(size, Image.Resampling.BILINEAR),
            dtype=np.float32,
        )
        base = float(coarse.mean()) or 1.0
        return np.clip(coarse / base, 0.82, 1.18)

    def render_pseudo_3d(
        self,
        posterized: Image.Image,
        output_path: str,
        light_reference_path: str | None = None,
        light_strength: float = 0.45,
        light_grid: int = 20,
        shading_strength: float = 1.0,
    ):
        """
        Algorithmic 2.5D shading on posterized art — passes Hive (~5%) while
        adding depth, specular highlights, edge bevel, and floor shadow.
        Optional coarse Kontext luminance nudges lighting without AI pixels.
        """
        img = posterized.convert("RGB")
        width, height = img.size
        arr = np.array(img, dtype=np.float32)
        gray = arr.mean(axis=2)

        height_map = self._blur_array(gray, 4.0 * shading_strength)
        gy, gx = np.gradient(height_map)
        nx = -gx * 1.2
        ny = -gy * 1.2
        nz = np.ones_like(gray) * 12.0
        norm = np.sqrt(nx * nx + ny * ny + nz * nz)
        nx, ny, nz = nx / norm, ny / norm, nz / norm

        lights = (
            (0.4, -0.5, 0.75, 0.5),
            (-0.35, 0.25, 0.88, 0.25),
        )
        diffuse = np.zeros_like(gray)
        for lx, ly, lz, weight in lights:
            ln = (lx * lx + ly * ly + lz * lz) ** 0.5
            diffuse += weight * np.clip(
                nx * lx / ln + ny * ly / ln + nz * lz / ln, 0, 1
            )
        diffuse = np.clip(diffuse * shading_strength + 0.35, 0.25, 1.0)

        if light_reference_path and os.path.isfile(light_reference_path):
            ratio = self._coarse_light_map(light_reference_path, (width, height), light_grid)
            diffuse *= 1.0 + (ratio - 1.0) * light_strength

        shaded = arr * diffuse[..., None]
        spec = np.clip(diffuse, 0, 1) ** 4
        shaded += spec[..., None] * (28 * shading_strength)

        rgba = self._white_background_to_rgba(img, tolerance=28)
        alpha = np.array(rgba.split()[-1], dtype=np.float32) / 255.0
        edge = np.clip(
            self._blur_array(alpha, 1.5) - self._blur_array(alpha, 4.0), 0, 1
        )
        shaded += edge[..., None] * (20 * shading_strength)
        shaded = np.clip(shaded, 0, 255)

        bg = np.array(
            self._make_radial_gradient(
                width, height, center_color=(224, 255, 255), edge_color=(64, 224, 208)
            ),
            dtype=np.float32,
        )
        contact = np.zeros_like(alpha)
        offset = max(8, int(min(width, height) * 0.012))
        contact[offset:, :] += alpha[:-offset, :] * 0.42
        bg *= 1.0 - self._blur_array(alpha, 16)[..., None] * 0.18
        bg *= 1.0 - contact[..., None] * 0.28

        mask = alpha[..., None]
        out = bg * (1.0 - mask) + shaded * mask
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB").save(
            output_path, "PNG"
        )

    def apply_threed_postprocess(
        self,
        input_path: str,
        output_path: str,
        intensity: int = 1,
        blend_source: str | None = None,
    ):
        """
        Light humanize for Hive retries only. Fresh FLUX 3D must not pass through this.
        """
        level = max(1, min(intensity, 8))
        with open(input_path, "rb") as f:
            raw = f.read()
        seed = int(hashlib.md5(raw).hexdigest()[:8], 16) + level * 9973

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        width, height = img.size
        rng = np.random.default_rng(seed)

        img = ImageEnhance.Color(img).enhance(1.0 + ((seed % 7) - 3) * 0.02 * level)
        img = ImageEnhance.Contrast(img).enhance(1.0 + ((seed % 5) - 2) * 0.02 * level)

        if level >= 2:
            small_w = max(1, int(width * (0.97 - level * 0.005)))
            small_h = max(1, int(height * (0.97 - level * 0.005)))
            img = img.resize((small_w, small_h), Image.Resampling.BILINEAR)
            img = img.resize((width, height), Image.Resampling.LANCZOS)

        if level >= 3:
            arr = np.array(img, dtype=np.float32)
            arr += rng.normal(0, 0.8 + level * 0.4, arr.shape)
            arr = np.clip(arr, 0, 255).astype(np.uint8)
            img = Image.fromarray(arr, "RGB")

        if level >= 4:
            jpeg_buf = io.BytesIO()
            q = max(78, 94 - level * 2)
            img.save(jpeg_buf, format="JPEG", quality=q, optimize=True)
            jpeg_buf.seek(0)
            img = Image.open(jpeg_buf).convert("RGB")

        if blend_source and os.path.isfile(blend_source) and level >= 3:
            master = Image.open(blend_source).convert("RGB")
            if master.size != img.size:
                master = master.resize(img.size, Image.Resampling.LANCZOS)
            alpha = min(0.06 + level * 0.03, 0.22)
            img = Image.blend(img, master, alpha)

        clean = Image.fromarray(np.array(img, dtype=np.uint8), "RGB")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        clean.save(output_path, format="PNG", optimize=True)

    def vectorize_with_gradient(self, input_path: str, output_path: str):
        """
        Illustrator 16-color look + radial gradient background.
        posterize = clean flat fills (default for cartoons)
        vtracer = SVG trace path
        """
        if self.vector_mode == "vtracer":
            self._vectorize_vtracer(input_path, output_path)
        else:
            self._vectorize_posterize(input_path, output_path)

    def _vectorize_posterize(self, input_path: str, output_path: str):
        """16-color posterize + gradient — no vtracer jaggy artifacts."""
        posterized = self._prepare_posterized(input_path)
        result = self._composite_on_gradient(posterized)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        result.save(output_path, "PNG")

    def _vectorize_vtracer(self, input_path: str, output_path: str):
        work_dir = os.path.dirname(output_path) or "."
        stem = os.path.splitext(os.path.basename(input_path))[0]
        prep_path = os.path.join(work_dir, f".{stem}_prep.png")
        svg_path = os.path.join(work_dir, f".{stem}_vec.svg")
        raw_png_path = os.path.join(work_dir, f".{stem}_vec_raw.png")

        try:
            self._prepare_for_vector(input_path, prep_path)

            if not self._run_vtracer_subprocess(prep_path, svg_path):
                logger.warning("vtracer failed for %s — using stylized fallback", input_path)
                self._fallback_composite(prep_path, output_path)
                return

            self._svg_to_png(svg_path, raw_png_path, scale=2.0)

            vec_img = Image.open(raw_png_path).convert("RGBA")
            vec_img = self._white_to_transparent(vec_img)

            width, height = vec_img.size
            bg = self._make_radial_gradient(
                width,
                height,
                center_color=(224, 255, 255),
                edge_color=(64, 224, 208),
            )
            bg.paste(vec_img, (0, 0), vec_img)
            bg.convert("RGB").save(output_path, "PNG")
        finally:
            for path in (prep_path, svg_path, raw_png_path):
                if path and os.path.exists(path):
                    os.remove(path)

    def _prepare_for_vector(self, input_path: str, output_path: str):
        """16-color posterize for trace — keep edges clean, drop micro-shading only."""
        img = Image.open(input_path).convert("RGB")
        width, height = img.size

        max_side = 2048
        if max(width, height) > max_side:
            scale = max_side / max(width, height)
            img = img.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.Resampling.LANCZOS,
            )

        img = ImageOps.autocontrast(img, cutoff=1)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.4))

        colors = max(4, min(self.vector_colors, 32))
        img = img.quantize(
            colors=colors,
            method=Image.Quantize.MEDIANCUT,
            dither=Image.Dither.FLOYDSTEINBERG,
        ).convert("RGB")

        img = ImageEnhance.Sharpness(img).enhance(1.15)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, "PNG")

    def _run_vtracer_subprocess(self, input_path: str, svg_path: str) -> bool:
        """Isolate vtracer in a child process (native crash must not kill Flask)."""
        try:
            result = subprocess.run(
                [sys.executable, "-c", self._vtracer_script(), input_path, svg_path],
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
        """Stylized composite when vtracer is unavailable."""
        img = Image.open(input_path).convert("RGB")
        img = ImageOps.autocontrast(img, cutoff=1)
        colors = max(4, min(self.vector_colors, 32))
        img = img.quantize(colors=colors, method=Image.Quantize.MEDIANCUT).convert("RGB")
        img = ImageEnhance.Sharpness(img).enhance(1.6)
        img = img.convert("RGBA")

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
        png_bytes = resvg_py.svg_to_bytes(svg_path=svg_path, zoom=scale)
        os.makedirs(os.path.dirname(png_path) or ".", exist_ok=True)
        with open(png_path, "wb") as f:
            f.write(png_bytes)

    def _white_background_to_rgba(self, img: Image.Image, tolerance: int = 28) -> Image.Image:
        """Knock out white/near-white background for gradient composite."""
        rgba = img.convert("RGBA")
        data = np.array(rgba)
        r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]
        white_mask = (r > 255 - tolerance) & (g > 255 - tolerance) & (b > 255 - tolerance)
        data[:, :, 3] = np.where(white_mask, 0, 255)
        return Image.fromarray(data, "RGBA")

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
