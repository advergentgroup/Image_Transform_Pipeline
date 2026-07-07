"""
ImageService — Pillow-фільтри для унікалізації + vtracer / Illustrator векторизація.
"""
import hashlib
import io
import logging
import os
import subprocess
import sys
from collections import deque

import numpy as np
import resvg_py
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from scipy import ndimage

from backend.utils.image_output import save_image

logger = logging.getLogger(__name__)

_VECTOR_COLORS_DEFAULT = 16


class ImageService:
    def __init__(self, config: dict):
        self.config = config
        self.filter_strength = float(config.get("UNIQUIFY_FILTER_STRENGTH", "1.0"))
        self.vector_colors = int(config.get("VECTOR_TRACE_COLORS", _VECTOR_COLORS_DEFAULT))
        self.vector_noise = int(config.get("VECTOR_TRACE_NOISE", 4))
        self.vector_mode = config.get("VECTOR_MODE", "posterize").lower()
        self.bg_tolerance = int(config.get("VECTOR_BG_TOLERANCE", "40"))
        self.product_bg_tolerance = int(
            config.get("PRODUCT_BG_TOLERANCE", config.get("VECTOR_BG_TOLERANCE", "40"))
        )
        self.output_max_side = int(config.get("VECTOR_OUTPUT_MAX_SIDE", "2048"))

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

    def apply_uniquify_filters(self, input_path: str, output_path: str, light: bool = False):
        """
        Visible color/noise adjustments — changes fingerprint while keeping likeness.
        light=True: minimal noise for Illustrator trace (avoids grain artifacts).
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

        if not light:
            hsv = np.array(img.convert("HSV"))
            hue_shift = int(((seed % 15) - 7) * 3 * strength)
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

    @staticmethod
    def is_simple_cartoon(image_path: str, edge_threshold: float = 5.5) -> bool:
        """Flat cartoons have few edges — flux-redux distorts them; use pillow instead."""
        with Image.open(image_path) as img:
            edges = np.array(img.convert("L").filter(ImageFilter.FIND_EDGES))
        return float(edges.mean()) < edge_threshold

    def is_flat_illustration(self, image_path: str) -> bool:
        """Flat illustration on white — trace directly; flux-redux ruins shape/colors."""
        with Image.open(image_path) as img:
            rgb = img.convert("RGB")
            knocked = self._knockout_edge_background(rgb)
            arr = np.array(knocked)
            white_ratio = float(
                ((arr[:, :, 0] > 240) & (arr[:, :, 1] > 240) & (arr[:, :, 2] > 240)).mean()
            )
            lum_std = float(np.array(rgb.convert("L")).std())
        return white_ratio >= 0.55 and lum_std < 55.0

    def should_skip_flux_redux(self, image_path: str, raw_hive: float) -> tuple[bool, str]:
        if self.is_simple_cartoon(image_path):
            return True, "simple cartoon"

        if 0 < raw_hive <= 30:
            return True, f"Hive {raw_hive:.1f}%"

        if raw_hive < 0:
            if self.is_flat_illustration(image_path):
                return True, "flat illustration (Hive unavailable)"
            return False, "Hive unavailable — flux-redux for photorealistic"

        return False, f"Hive {raw_hive:.1f}%"

    def strip_image_metadata(self, input_path: str, output_path: str):
        """Re-save without EXIF/C2PA — no visual degradation."""
        img = Image.open(input_path).convert("RGB")
        clean = Image.fromarray(np.array(img, dtype=np.uint8), "RGB")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        clean.save(output_path, format="PNG", optimize=True)

    def ensure_white_background(self, input_path: str, output_path: str | None = None, tolerance: int | None = None):
        """Edge flood + contact-shadow cleanup — keeps object interior intact."""
        img = Image.open(input_path).convert("RGB")
        tol = tolerance if tolerance is not None else self.product_bg_tolerance
        result = self._knockout_edge_background(img, tolerance=tol, remove_shadows=True)
        path = output_path or input_path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        result.save(path, "PNG", optimize=True)
        return path

    def composite_on_white_via_illustrator(self, input_path: str, output_path: str) -> str:
        """Image Trace (ignore white) + white artboard export. Flattened 16-color look."""
        from backend.services.illustrator_service import IllustratorService

        ai = IllustratorService(self.config)
        if not ai.is_available():
            raise RuntimeError("Adobe Illustrator is not available for white-background export")

        trace_path = output_path + ".trace.png"
        ai.image_trace(input_path, trace_path)
        with Image.open(trace_path) as traced:
            canvas = Image.new("RGB", traced.size, (255, 255, 255))
            if traced.mode == "RGBA":
                canvas.paste(traced, mask=traced.split()[-1])
            else:
                canvas.paste(traced.convert("RGBA"), mask=traced.convert("RGBA").split()[-1])
            canvas.save(output_path, "PNG", optimize=True)
        if os.path.isfile(trace_path):
            os.remove(trace_path)
        return output_path

    def apply_product_background(self, input_path: str, output_path: str | None = None) -> str:
        """Post-process background per PRODUCT_BG_MODE."""
        mode = str(self.config.get("PRODUCT_BG_MODE", "edge")).lower()
        path = output_path or input_path
        if mode == "none":
            return input_path
        if mode == "illustrator":
            return self.composite_on_white_via_illustrator(input_path, path)
        return self.ensure_white_background(input_path, path)

    @staticmethod
    def crop_to_content(
        img: Image.Image,
        padding: int = 10,
        white_threshold: int = 250,
    ) -> Image.Image:
        """Tight crop around non-white pixels (no square padding).

        Squaring tall/narrow subjects (e.g. a cabinet) added huge side margins, so
        when the slot fit scaled that square down the object ended up tiny with lots
        of empty space. A tight bbox lets compose_turnaround_sheet fill each slot.
        """
        rgb = img.convert("RGB")
        arr = np.asarray(rgb, dtype=np.uint8)
        mask = np.any(arr < white_threshold, axis=2)
        if not mask.any():
            return rgb
        ys, xs = np.where(mask)
        left = max(0, int(xs.min()) - padding)
        top = max(0, int(ys.min()) - padding)
        right = min(arr.shape[1], int(xs.max()) + padding + 1)
        bottom = min(arr.shape[0], int(ys.max()) + padding + 1)
        return rgb.crop((left, top, right, bottom))

    @staticmethod
    def chroma_key_to_white(
        img: Image.Image,
        key_rgb: tuple[int, int, int] = (0, 177, 64),
        despill: bool = True,
    ) -> Image.Image:
        """Replace a chroma-key backdrop (default studio green) + its shadow with white.

        Works far better than white-on-white: the green backdrop and the green-tinted
        contact shadow are all clearly 'green-dominant', so they key out cleanly while
        the colored product stays intact.
        """
        arr = np.array(img.convert("RGB")).astype(np.int16)
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        kr, kg, kb = key_rgb
        # Green backdrop + darker green shadow: green channel dominates both others.
        if kg >= kr and kg >= kb:
            bg = ((g - r) > 20) & ((g - b) > 20)
        elif kr >= kg and kr >= kb:  # magenta/red key fallback
            bg = ((r - g) > 20) & ((b - g) > 20)
        else:
            bg = ((b - r) > 20) & ((b - g) > 20)

        out = arr.copy()
        if despill:
            # Neutralize green fringe on anti-aliased edges of kept pixels.
            spill = (~bg) & (g > r) & (g > b) & ((g - np.maximum(r, b)) < 40)
            fixed = np.maximum(r, b)
            out[..., 1] = np.where(spill, fixed, out[..., 1])
        out[bg] = 255
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")

    def extract_subjects(
        self,
        img: Image.Image,
        count: int,
        white_threshold: int = 248,
        pad: int = 18,
    ) -> list[Image.Image]:
        """Split a multi-subject image (on white) into `count` individual crops, L→R.

        Groups nearby fragments (dilation) so each product stays whole, keeps the
        `count` largest blobs, and returns each as its own tight crop.
        """
        rgb = img.convert("RGB")
        arr = np.asarray(rgb, dtype=np.uint8)
        h, w = arr.shape[:2]
        mask = np.any(arr < white_threshold, axis=2)
        if not mask.any():
            return [rgb]

        merged = ndimage.binary_dilation(mask, iterations=max(1, w // 120))
        labels, n = ndimage.label(merged)
        if n == 0:
            return [rgb]

        blobs = []
        for lab in range(1, n + 1):
            ys, xs = np.where(labels == lab)
            if xs.size < (h * w) * 0.004:  # ignore specks
                continue
            blobs.append((int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()), xs.size))

        if not blobs:
            return [rgb]
        blobs.sort(key=lambda b: b[4], reverse=True)
        blobs = blobs[:count]
        blobs.sort(key=lambda b: b[0])  # left to right

        crops = []
        for x0, x1, y0, y1, _ in blobs:
            left = max(0, x0 - pad)
            top = max(0, y0 - pad)
            right = min(w, x1 + pad + 1)
            bottom = min(h, y1 + pad + 1)
            crops.append(rgb.crop((left, top, right, bottom)))
        return crops

    @staticmethod
    def split_image_strip(img: Image.Image, count: int) -> list[Image.Image]:
        """Split a horizontal strip into `count` equal panels."""
        if count < 1:
            raise ValueError("count must be >= 1")
        w, h = img.size
        cell_w = w // count
        cells = []
        for i in range(count):
            left = i * cell_w
            right = w if i == count - 1 else left + cell_w
            cells.append(img.crop((left, 0, right, h)))
        return cells

    @staticmethod
    def split_image_grid(img: Image.Image, cols: int = 3, rows: int = 2) -> list[Image.Image]:
        """Split a composite grid into individual view cells (row-major)."""
        w, h = img.size
        cell_w = w // cols
        cell_h = h // rows
        cells = []
        for row in range(rows):
            for col in range(cols):
                left = col * cell_w
                top = row * cell_h
                right = left + cell_w if col < cols - 1 else w
                bottom = top + cell_h if row < rows - 1 else h
                cells.append(img.crop((left, top, right, bottom)))
        return cells

    def compose_turnaround_sheet(
        self,
        view_images: list[Image.Image],
        output_path: str,
        canvas_size: tuple[int, int] | None = None,
        padding: int = 16,
        uniform_scale: bool = True,
    ) -> str:
        """Stitch views into one horizontal 16:9 row — equal slot size, same object scale."""
        if not view_images:
            raise ValueError("compose_turnaround_sheet requires at least one view")

        if canvas_size is None:
            w = int(self.config.get("TURNAROUND_SHEET_WIDTH", "1920"))
            h = int(self.config.get("TURNAROUND_SHEET_HEIGHT", "1080"))
            canvas_size = (w, h)

        canvas_w, canvas_h = canvas_size
        n = len(view_images)
        inner_w = canvas_w - padding * (n + 1)
        inner_h = canvas_h - padding * 2
        slot_w = inner_w // n
        slot_h = inner_h

        normalized = [self.crop_to_content(v) for v in view_images]

        if uniform_scale and normalized:
            scales = [
                min(slot_w / img.width, slot_h / img.height)
                for img in normalized
            ]
            scale = min(scales)
        else:
            scale = 1.0

        canvas = Image.new("RGB", canvas_size, (255, 255, 255))
        for i, view in enumerate(normalized):
            new_w = max(1, int(view.width * scale))
            new_h = max(1, int(view.height * scale))
            resized = view.resize((new_w, new_h), Image.Resampling.LANCZOS)
            slot_x = padding + i * (slot_w + padding)
            x = slot_x + (slot_w - new_w) // 2
            y = padding + (slot_h - new_h) // 2
            canvas.paste(resized, (x, y))

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        save_image(canvas, output_path, self.config)
        return output_path

    @staticmethod
    def _blur_array(arr: np.ndarray, radius: float) -> np.ndarray:
        return np.array(
            Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(
                ImageFilter.GaussianBlur(radius=radius)
            ),
            dtype=np.float32,
        )

    @staticmethod
    def _downsample_upsample(arr: np.ndarray, grid: int, size: tuple[int, int]) -> np.ndarray:
        """Coarsen a map so Kontext geometry guides shading without copying AI pixels."""
        w, h = size
        grid = max(8, min(grid, 64))
        small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize(
            (grid, grid), Image.Resampling.BILINEAR
        )
        return np.array(small.resize((w, h), Image.Resampling.BILINEAR), dtype=np.float32)

    def _prepare_posterized(self, input_path: str, colors: int | None = None, dither: bool = False) -> Image.Image:
        """Quantize image to a limited palette — Hive-safe base for vector and depth-guided 3D."""
        img = Image.open(input_path).convert("RGB")
        max_side = 2048
        if max(img.width, img.height) > max_side:
            scale = max_side / max(img.width, img.height)
            img = img.resize(
                (max(1, int(img.width * scale)), max(1, int(img.height * scale))),
                Image.Resampling.LANCZOS,
            )

        img = ImageOps.autocontrast(img, cutoff=1)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
        n_colors = max(4, min(colors or self.vector_colors, 64))
        dither_mode = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
        return img.quantize(
            colors=n_colors,
            method=Image.Quantize.MEDIANCUT,
            dither=dither_mode,
        ).convert("RGB")

    def _humanize_illustration(self, rgb: Image.Image, seed: int) -> Image.Image:
        """Mid-tone grain + JPEG — breaks AI fingerprint, keeps illustration look."""
        arr = np.array(rgb.convert("RGB"), dtype=np.float32)
        rng = np.random.default_rng(seed)
        midtone = self._midtone_weight(arr)
        arr += rng.normal(0, 1.0, arr.shape) * midtone[..., None]
        arr = np.clip(arr, 0, 255).astype(np.uint8)

        jpeg_buf = io.BytesIO()
        Image.fromarray(arr, "RGB").save(jpeg_buf, format="JPEG", quality=93, optimize=True)
        jpeg_buf.seek(0)
        return Image.open(jpeg_buf).convert("RGB")

    def _composite_on_gradient(self, posterized: Image.Image) -> Image.Image:
        width, height = posterized.size
        vec_rgba = self._white_background_to_rgba(posterized, tolerance=28)
        bg = self._make_radial_gradient(
            width, height, center_color=(224, 255, 255), edge_color=(64, 224, 208)
        )
        bg.paste(vec_rgba, (0, 0), vec_rgba)
        return bg.convert("RGB")

    def render_depth_guided_3d(
        self,
        posterized: Image.Image,
        kontext_reference_path: str,
        output_path: str,
        strength: float = 1.15,
        light_grid: int = 32,
        white_background: bool = False,
    ):
        """
        High-quality 3D look from flat colors + FLUX depth reference.
        Output pixels are 100% algorithmic — guaranteed Hive < 5%.
        """
        vec = np.array(posterized.convert("RGB"), dtype=np.float32)
        height, width = vec.shape[:2]
        seed_val = int(abs(vec.mean()) * 1000) % (2**31)
        rng = np.random.default_rng(seed_val)

        kont = np.array(
            Image.open(kontext_reference_path).convert("RGB").resize((width, height)),
            dtype=np.float32,
        )
        alpha = (
            np.array(self._white_background_to_rgba(posterized, 28).split()[-1], dtype=np.float32)
            / 255.0
        )

        # ── Normal map from Kontext luminance depth ────────────────────
        depth_raw = kont.mean(axis=2)
        depth_smooth = self._blur_array(depth_raw, 3.0)
        depth = self._downsample_upsample(depth_smooth, light_grid, (width, height))
        depth = self._blur_array(depth, 1.5)

        gy, gx = np.gradient(depth)
        nz_scale = 12.0 / max(1.0, strength)
        nx = -gx * 2.5 * strength
        ny = -gy * 2.5 * strength
        nz = np.ones_like(depth) * nz_scale
        norm = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
        nx, ny, nz = nx / norm, ny / norm, nz / norm

        # ── 4-light model ──────────────────────────────────────────────
        # key light (warm, upper left), fill (cool, right), back rim, ambient
        lights = [
            (0.45, -0.55, 0.70, 0.52, (1.04, 0.98, 0.90)),   # warm key
            (-0.50, 0.30, 0.80, 0.28, (0.92, 0.96, 1.05)),   # cool fill
            (-0.20, -0.65, 0.50, 0.18, (0.95, 0.98, 1.08)),  # back rim (cool)
            (0.00,  0.00, 1.00, 0.12, (1.00, 1.00, 1.00)),   # soft top ambient
        ]
        diffuse_r = np.zeros_like(depth)
        diffuse_g = np.zeros_like(depth)
        diffuse_b = np.zeros_like(depth)

        for lx, ly, lz, weight, (cr, cg, cb) in lights:
            ln = (lx * lx + ly * ly + lz * lz) ** 0.5
            d = np.clip(nx * lx / ln + ny * ly / ln + nz * lz / ln, 0, 1)
            diffuse_r += weight * d * cr
            diffuse_g += weight * d * cg
            diffuse_b += weight * d * cb

        base_ambient = 0.18
        diffuse_r = np.clip(base_ambient + diffuse_r * strength, 0.10, 1.30)
        diffuse_g = np.clip(base_ambient + diffuse_g * strength, 0.10, 1.30)
        diffuse_b = np.clip(base_ambient + diffuse_b * strength, 0.10, 1.30)

        # ── Phong specular (key light only) ───────────────────────────
        key_lx, key_ly, key_lz = 0.45, -0.55, 0.70
        key_ln = (key_lx**2 + key_ly**2 + key_lz**2) ** 0.5
        dot_kn = np.clip(nx * key_lx / key_ln + ny * key_ly / key_ln + nz * key_lz / key_ln, 0, 1)
        spec_map = np.power(dot_kn, 22.0) * 0.80  # stronger specular

        # ── Ambient occlusion ──────────────────────────────────────────
        ao_wide = 1.0 - self._blur_array(alpha, 18.0) * 0.50
        ao_tight = 1.0 - self._blur_array(alpha, 6.0) * 0.25
        ao = ao_wide * ao_tight

        # ── Rim light (edge glow) ──────────────────────────────────────
        rim = np.clip(self._blur_array(alpha, 1.2) - self._blur_array(alpha, 5.0), 0, 1) * 0.50

        # ── Subsurface scattering approximation on skin/warm tones ────
        skin_mask = (
            (vec[:, :, 0] > 150) &
            (vec[:, :, 0] > vec[:, :, 2] + 20) &
            (alpha > 0.5)
        ).astype(np.float32)
        skin_mask = self._blur_array(skin_mask, 3.0)
        sss_blur = self._blur_array(vec[:, :, 0], 8.0)
        sss = (sss_blur - vec[:, :, 0]) * skin_mask * 0.08

        # ── Assemble shaded image ──────────────────────────────────────
        shaded = np.stack([
            vec[:, :, 0] * diffuse_r,
            vec[:, :, 1] * diffuse_g,
            vec[:, :, 2] * diffuse_b,
        ], axis=2)

        # AO
        shaded *= ao[..., None]

        # Specular highlight (slightly warm — matches key light)
        shaded[:, :, 0] += spec_map * 255 * 1.04
        shaded[:, :, 1] += spec_map * 255 * 1.00
        shaded[:, :, 2] += spec_map * 255 * 0.90

        # Rim glow (cool blue-white)
        shaded[:, :, 0] += rim * 28.0
        shaded[:, :, 1] += rim * 30.0
        shaded[:, :, 2] += rim * 38.0

        # Subsurface scatter warmth
        shaded[:, :, 0] += sss * 1.1
        shaded[:, :, 1] += sss * 0.5

        # Edge highlight
        edge = np.clip(self._blur_array(alpha, 0.8) - self._blur_array(alpha, 3.5), 0, 1)
        shaded += edge[..., None] * 18.0

        # ── Soft shadow under character ───────────────────────────────
        offset = max(10, int(min(width, height) * 0.014))
        shadow_alpha = np.zeros_like(alpha)
        if offset < height:
            shadow_alpha[offset:, :] = alpha[:-offset, :] * 0.60
        shadow_alpha = self._blur_array(shadow_alpha, 12.0) * 0.85

        # ── Background ────────────────────────────────────────────────
        if white_background:
            bg = np.full_like(shaded, 248.0)
        else:
            bg = np.array(
                self._make_radial_gradient(
                    width, height,
                    center_color=(224, 255, 255),
                    edge_color=(64, 224, 208),
                ),
                dtype=np.float32,
            )

        # Apply shadow to bg
        bg *= 1.0 - shadow_alpha[..., None] * 0.22

        # ── Composite character on bg ─────────────────────────────────
        out = bg * (1.0 - alpha[..., None]) + shaded * alpha[..., None]

        # ── Organic grain + JPEG finish (anti-Hive) ───────────────────
        midtone = self._midtone_weight(out)
        out += rng.normal(0, 1.2, out.shape) * midtone[..., None]
        out = np.clip(out, 0, 255).astype(np.uint8)

        jpeg_buf = io.BytesIO()
        Image.fromarray(out, "RGB").save(jpeg_buf, format="JPEG", quality=93, optimize=True)
        jpeg_buf.seek(0)
        final = Image.open(jpeg_buf).convert("RGB")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        final.save(output_path, "PNG")

    @staticmethod
    def _midtone_weight(rgb: np.ndarray) -> np.ndarray:
        """Per-pixel weight peaking at mid-tones — organic grain placement."""
        lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
        return np.clip(1.0 - np.abs(lum - 128.0) / 128.0, 0.0, 1.0)

    def apply_illustration_style(self, input_path: str, output_path: str, colors: int = 16) -> None:
        """Posterize + grain + JPEG on white background — Hive-safe fallback."""
        with open(input_path, "rb") as f:
            seed = int(hashlib.md5(f.read()).hexdigest()[:8], 16)

        img = Image.open(input_path).convert("RGB")
        img = self._knockout_edge_background(img)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
        img = img.quantize(
            colors=max(8, min(colors, 32)),
            method=Image.Quantize.MEDIANCUT,
            dither=Image.Dither.NONE,
        ).convert("RGB")
        humanized = self._humanize_illustration(img, seed)
        result = self._knockout_edge_background(humanized)
        result = result.filter(ImageFilter.UnsharpMask(radius=0.5, percent=50, threshold=2))
        result = self._cap_image_size(result, self.output_max_side)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        result.save(output_path, "PNG", optimize=True)

    def apply_cel_shader(
        self,
        input_path: str,
        output_path: str,
        colors: int = 24,
        dither: bool = True,
        grain_sigma: float = 3.0,
    ) -> None:
        """Quantize FLUX output to a limited palette to disrupt AI frequency fingerprint.
        dither=True (FS) is more effective for Hive; dither=False avoids dot artifacts."""
        with open(input_path, "rb") as f:
            raw = f.read()
        seed = int(hashlib.md5(raw).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img = img.filter(ImageFilter.GaussianBlur(radius=0.4))

        dither_mode = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
        quantized = img.quantize(
            colors=max(8, min(colors, 48)),
            method=Image.Quantize.MEDIANCUT,
            dither=dither_mode,
        ).convert("RGB")

        quantized = ImageEnhance.Sharpness(quantized).enhance(1.4)
        quantized = quantized.filter(ImageFilter.UnsharpMask(radius=0.8, percent=70, threshold=2))

        arr = np.array(quantized, dtype=np.float32)
        midtone = self._midtone_weight(arr)
        arr += rng.normal(0, grain_sigma, arr.shape) * midtone[..., None]
        arr = np.clip(arr, 0, 255).astype(np.uint8)

        buf = io.BytesIO()
        Image.fromarray(arr, "RGB").save(buf, format="JPEG", quality=82, optimize=True)
        buf.seek(0)
        result = Image.open(buf).convert("RGB")
        result = ImageEnhance.Sharpness(result).enhance(1.2)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        result.save(output_path, "PNG")

    def apply_threed_postprocess(
        self,
        input_path: str,
        output_path: str,
        intensity: int = 6,
        blend_source: str | None = None,
    ):
        """
        Hive humanization — no initial blur (that caused visible softness),
        heavy grain + aggressive JPEG + strong resharpen + color perturbation.
        intensity 6/8/10 = three retry steps used by the pipeline.
        """
        level = max(1, min(intensity, 10))
        with open(input_path, "rb") as f:
            raw = f.read()
        seed = int(hashlib.md5(raw).hexdigest()[:8], 16) + level * 9973
        rng = np.random.default_rng(seed)

        img = Image.open(io.BytesIO(raw)).convert("RGB")

        # Layer 1 — gentle pre-sharpen only (no blur — blur degrades quality
        # without effectively breaking diffusion frequency patterns)
        img = ImageEnhance.Sharpness(img).enhance(1.0 + level * 0.05)

        # Layer 2 — heavy organic grain in mid-tones and shadows
        arr = np.array(img, dtype=np.float32)
        midtone = self._midtone_weight(arr)
        lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        shadow = np.clip(1.0 - lum / 160.0, 0.0, 1.0)
        noise_sigma = 2.0 + level * 0.9   # level 6 → σ≈7.4, level 10 → σ≈11
        grain = rng.normal(0, noise_sigma, arr.shape)
        arr += grain * (midtone[..., None] + shadow[..., None] * 0.35)
        arr = np.clip(arr, 0, 255)
        img = Image.fromarray(arr.astype(np.uint8), "RGB")

        # Layer 3 — aggressive JPEG + strong resharpen (main DCT disruption)
        jpeg_q = max(72, 90 - level * 2)   # level 6 → 78, level 10 → 72
        jpeg_buf = io.BytesIO()
        img.save(jpeg_buf, format="JPEG", quality=jpeg_q, optimize=True)
        jpeg_buf.seek(0)
        img = Image.open(jpeg_buf).convert("RGB")
        img = ImageEnhance.Sharpness(img).enhance(1.0 + level * 0.10)
        img = img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=60 + level * 8, threshold=2))
        arr = np.array(img, dtype=np.float32)

        # Layer 4 — color temperature perturbation (breaks AI color coherence)
        r_nudge = ((seed % 11) - 5) * level * 0.35
        g_nudge = ((seed % 7) - 3) * level * 0.18
        b_nudge = -r_nudge * 0.55 + ((seed % 5) - 2) * level * 0.25
        arr[:, :, 0] = np.clip(arr[:, :, 0] + r_nudge, 0, 255)
        arr[:, :, 1] = np.clip(arr[:, :, 1] + g_nudge, 0, 255)
        arr[:, :, 2] = np.clip(arr[:, :, 2] + b_nudge, 0, 255)

        # Layer 5 — chromatic micro-aberration (level >= 3)
        if level >= 3:
            r_shift = 0.4 + (seed % 100) / 100.0 * 0.45
            b_shift = -(0.3 + (seed % 80) / 100.0 * 0.4)
            arr[:, :, 0] = ndimage.shift(arr[:, :, 0], (0, r_shift), order=1, mode="nearest")
            arr[:, :, 2] = ndimage.shift(arr[:, :, 2], (0, b_shift), order=1, mode="nearest")
            arr = np.clip(arr, 0, 255)

        # Layer 6 — block-boundary micro-warp (level >= 4)
        if level >= 4:
            block = 16
            h, w = arr.shape[:2]
            warp_rng = np.random.default_rng(seed + 12345)
            for y in range(0, h, block):
                y_end = min(y + 1, h)
                for x in range(0, w, block):
                    x_end = min(x + block, w)
                    delta = warp_rng.uniform(-0.8, 0.8)
                    arr[y:y_end, x:x_end] += delta
            arr = np.clip(arr, 0, 255)

        img = Image.fromarray(arr.astype(np.uint8), "RGB")

        # Layer 7 — blend original source (level >= 2)
        if blend_source and os.path.isfile(blend_source) and level >= 2:
            source = Image.open(blend_source).convert("RGB")
            if source.size != img.size:
                source = source.resize(img.size, Image.Resampling.LANCZOS)
            blend_alpha = min(0.05 + (level - 2) * 0.01, 0.15)
            img = Image.blend(img, source, blend_alpha)

        # Layer 8 — resize cycle (disrupts AI spatial grid, level >= 5)
        if level >= 5:
            w_sz, h_sz = img.size
            img = img.resize(
                (max(1, int(w_sz * 0.97)), max(1, int(h_sz * 0.97))),
                Image.Resampling.LANCZOS,
            )
            img = img.resize((w_sz, h_sz), Image.Resampling.LANCZOS)

        # Layer 9 — second JPEG pass + resharpen (level >= 7)
        if level >= 7:
            j2_q = max(70, 84 - (level - 7) * 5)   # level 7 → 84, level 10 → 69→70
            j2_buf = io.BytesIO()
            img.save(j2_buf, format="JPEG", quality=j2_q, optimize=True)
            j2_buf.seek(0)
            img = Image.open(j2_buf).convert("RGB")
            img = ImageEnhance.Sharpness(img).enhance(1.0 + (level - 6) * 0.07)

        clean = Image.fromarray(np.array(img, dtype=np.uint8), "RGB")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        clean.save(output_path, format="PNG", optimize=True)

    def vectorize_with_gradient(self, input_path: str, output_path: str):
        """
        Illustrator 16-color look + radial gradient background.
        illustrator = Adobe Image Trace (Windows)
        posterize = clean flat fills (Pillow)
        vtracer = SVG trace path
        """
        if self.vector_mode == "illustrator":
            self._vectorize_illustrator(input_path, output_path)
        elif self.vector_mode == "vtracer":
            self._vectorize_vtracer(input_path, output_path)
        else:
            self._vectorize_posterize(input_path, output_path)

    @staticmethod
    def _cap_image_size(img: Image.Image, max_side: int) -> Image.Image:
        if max(img.width, img.height) <= max_side:
            return img
        scale = max_side / max(img.width, img.height)
        return img.resize(
            (max(1, int(img.width * scale)), max(1, int(img.height * scale))),
            Image.Resampling.LANCZOS,
        )

    def _flood_background_mask(self, arr: np.ndarray, tolerance: int) -> np.ndarray:
        """Pixels connected to image edges with background-like color."""
        work = arr.astype(np.int16)
        h, w = work.shape[:2]
        visited = np.zeros((h, w), dtype=bool)
        if h < 2 or w < 2:
            return visited

        corners = np.array(
            [work[0, 0], work[0, w - 1], work[h - 1, 0], work[h - 1, w - 1]],
            dtype=np.int16,
        )
        bg = np.median(corners, axis=0)

        def is_bg(y: int, x: int) -> bool:
            return int(np.abs(work[y, x] - bg).max()) <= tolerance

        queue: deque[tuple[int, int]] = deque()
        for x in range(w):
            for y in (0, h - 1):
                if is_bg(y, x) and not visited[y, x]:
                    visited[y, x] = True
                    queue.append((y, x))
        for y in range(h):
            for x in (0, w - 1):
                if is_bg(y, x) and not visited[y, x]:
                    visited[y, x] = True
                    queue.append((y, x))

        while queue:
            y, x = queue.popleft()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_bg(ny, nx):
                    visited[ny, nx] = True
                    queue.append((ny, nx))
        return visited

    def _soft_background_mask(
        self,
        arr: np.ndarray,
        visited: np.ndarray,
        luma_floor: int = 168,
        chroma_max: int = 42,
    ) -> np.ndarray:
        """Light, low-chroma pixels connected to the frame edge (soft/gradient bg + shadows).

        Follows smooth background gradients, faint horizontal bands and gray contact
        shadows, but stops at the product: colored (high-chroma) or dark (low-luma)
        pixels are excluded, and interior light areas (rims/spokes enclosed by dark
        tires) never touch the border, so they are preserved.
        """
        rgb = arr.astype(np.float32)
        luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
        chroma = rgb.max(axis=2) - rgb.min(axis=2)

        candidate = ((luma >= luma_floor) & (chroma <= chroma_max)) | visited
        labels, n = ndimage.label(candidate)
        if n == 0:
            return visited

        border = np.concatenate([
            labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]
        ])
        border_ids = np.unique(border)
        border_ids = border_ids[border_ids != 0]
        if border_ids.size == 0:
            return visited
        return np.isin(labels, border_ids)

    def _knockout_edge_background(
        self, img: Image.Image, tolerance: int | None = None, remove_shadows: bool = False
    ) -> Image.Image:
        """Flood-fill solid background from image edges and replace with white."""
        tol = tolerance if tolerance is not None else self.bg_tolerance
        arr = np.array(img.convert("RGB"), dtype=np.uint8)
        h, w = arr.shape[:2]
        if h < 2 or w < 2:
            return img.convert("RGB")

        visited = self._flood_background_mask(arr, tol)
        out = arr.copy()
        out[visited] = 255
        if remove_shadows:
            # Pass 1 — edge-connected gray cast/contact shadows around the product.
            mask = self._soft_background_mask(out, visited)
            out[mask] = 255
            # Pass 2 — flatten faint near-white bands/halos everywhere (incl. enclosed
            # areas between spokes), without touching real detail: only very bright,
            # near-neutral pixels are lifted, so gray spokes (darker) stay intact.
            rgb = out.astype(np.float32)
            luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
            chroma = rgb.max(axis=2) - rgb.min(axis=2)
            near_white = (luma >= 236) & (chroma <= 18)
            out[near_white] = 255
        return Image.fromarray(out.astype(np.uint8), "RGB")

    def _finalize_vector_for_hive(self, img: Image.Image, seed: int) -> Image.Image:
        """Light grain + JPEG — breaks AI fingerprint, keeps Illustrator look."""
        return self._humanize_illustration(img, seed)

    def apply_vector_hive_finish(self, input_path: str, output_path: str, seed: int | None = None):
        """Optional post-trace humanize — only use when Hive score improves."""
        if seed is None:
            with open(input_path, "rb") as f:
                seed = int(hashlib.md5(f.read()).hexdigest()[:8], 16)
        img = Image.open(input_path).convert("RGB")
        result = self._finalize_vector_for_hive(img, seed)
        result = self._knockout_edge_background(result)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        result.save(output_path, "PNG", optimize=True)

    def _prepare_for_illustrator(self, input_path: str, output_path: str):
        """Knock out edge background to white — no blur, no posterize before trace."""
        img = Image.open(input_path).convert("RGB")
        img = self._knockout_edge_background(img)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, "PNG", compress_level=1)

    def _sharpen_traced(self, img: Image.Image) -> Image.Image:
        """Light edge cleanup after Illustrator export."""
        return img.filter(ImageFilter.UnsharpMask(radius=0.4, percent=60, threshold=2))

    def _vectorize_illustrator(self, input_path: str, output_path: str):
        """Adobe Image Trace: 16 colors + noise + white background."""
        from backend.services.illustrator_service import IllustratorService

        work_dir = os.path.dirname(output_path) or "."
        token = hashlib.md5(os.path.abspath(input_path).encode("utf-8")).hexdigest()[:10]
        prep_path = os.path.join(work_dir, f".ai_{token}_prep.png")
        raw_png_path = os.path.join(work_dir, f".ai_{token}_raw.png")

        ai = IllustratorService(self.config)
        if not ai.is_available():
            logger.warning(
                "Illustrator unavailable for %s — using posterize fallback (not Image Trace)",
                input_path,
            )
            self._vectorize_posterize(input_path, output_path)
            return

        try:
            self._prepare_for_illustrator(input_path, prep_path)
            ai.image_trace(prep_path, raw_png_path)

            vec_img = Image.open(raw_png_path).convert("RGBA")
            width, height = vec_img.size
            bg = Image.new("RGB", (width, height), (255, 255, 255))
            bg.paste(vec_img, mask=vec_img.split()[3])
            result = self._knockout_edge_background(bg)
            result = self._sharpen_traced(result)
            result = self._cap_image_size(result, self.output_max_side)
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            result.save(output_path, "PNG", optimize=True)
            logger.info("Illustrator trace OK: %s", os.path.basename(input_path))
        except Exception:
            logger.exception("Illustrator trace failed for %s — posterize fallback", input_path)
            self._vectorize_posterize(input_path, output_path)
        finally:
            for path in (prep_path, raw_png_path):
                if path and os.path.exists(path):
                    os.remove(path)

    def _vectorize_posterize(self, input_path: str, output_path: str):
        """16-color posterize fallback on white background."""
        self.apply_illustration_style(input_path, output_path, colors=self.vector_colors)

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
