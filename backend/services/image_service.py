"""
ImageService — відповідає Розробник 2 (frontend dev).

Реалізує:
  - vectorize_with_gradient(): vtracer векторизація + радіальний градієнт фон
"""
import os
from PIL import Image, ImageDraw
import numpy as np


class ImageService:
    def __init__(self, config: dict):
        self.config = config

    def vectorize_with_gradient(self, input_path: str, output_path: str):
        """
        1. Векторизація через vtracer (6 кольорів, Image Trace ефект)
        2. Накладення радіального градієнтного фону (#E0FFFF → #40E0D0)
        3. Збереження PNG

        TODO (Розробник 2):
          - pip install vtracer
          - Викликати vtracer CLI або Python API
          - Підібрати параметри: colormode=color, nr_colors=6, filter_speckle=4
          - Конвертувати SVG результат назад у PNG через cairosvg або Pillow
        """
        # ── Placeholder — замінити на реальний vtracer виклик ──────────
        img = Image.open(input_path).convert("RGBA")
        width, height = img.size

        # Радіальний градієнт фон
        bg = self._make_radial_gradient(width, height,
                                         center_color=(224, 255, 255),   # #E0FFFF
                                         edge_color=(64, 224, 208))      # #40E0D0

        # Composite: gradient bg + character
        bg.paste(img, (0, 0), img)
        bg.convert("RGB").save(output_path, "PNG")

    def _make_radial_gradient(self, width: int, height: int,
                               center_color: tuple, edge_color: tuple) -> Image.Image:
        """Create radial gradient background image."""
        cx, cy = width // 2, height // 2
        max_dist = ((cx**2 + cy**2) ** 0.5)

        img_array = np.zeros((height, width, 3), dtype=np.uint8)
        y_indices, x_indices = np.mgrid[0:height, 0:width]

        dist = np.sqrt((x_indices - cx)**2 + (y_indices - cy)**2)
        t = np.clip(dist / max_dist, 0, 1)

        for c in range(3):
            img_array[:, :, c] = (
                center_color[c] * (1 - t) + edge_color[c] * t
            ).astype(np.uint8)

        return Image.fromarray(img_array, "RGB")
