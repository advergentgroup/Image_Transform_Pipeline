"""
ImageService — векторизація через vtracer + радіальний градієнт фон.
"""
import os

import cairosvg
import numpy as np
import vtracer
from PIL import Image


class ImageService:
    def __init__(self, config: dict):
        self.config = config

    def vectorize_with_gradient(self, input_path: str, output_path: str):
        """
        1. Векторизація через vtracer (6 кольорів, Image Trace ефект)
        2. Растеризація SVG → PNG через cairosvg
        3. Накладення радіального градієнтного фону (#E0FFFF → #40E0D0)
        """
        work_dir = os.path.dirname(output_path) or "."
        stem = os.path.splitext(os.path.basename(input_path))[0]
        svg_path = os.path.join(work_dir, f".{stem}_vec.svg")
        raw_png_path = os.path.join(work_dir, f".{stem}_vec_raw.png")

        try:
            vtracer.convert_image_to_svg_py(
                input_path,
                svg_path,
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

            cairosvg.svg2png(url=svg_path, write_to=raw_png_path, scale=2.0)

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
