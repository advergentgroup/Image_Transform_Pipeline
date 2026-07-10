"""GPU turnaround worker — TRELLIS variant (higher-quality 3D than Zero123++).

Same HTTP contract as server.py (/health, /generate -> {"views": [...base64 png...]}),
so the app's TURNAROUND_MODE=gpu-worker talks to it unchanged. Use this on an
RTX 3090 (24GB) when Zero123++ smears thin geometry (e.g. bike spokes).

IMPORTANT: TRELLIS is NOT pip-installable as a simple package. Run this file from
inside the cloned microsoft/TRELLIS repo (so `import trellis` resolves), after its
own setup. See README.md "TRELLIS" section.

Run (inside the TRELLIS repo, its env activated):
    cp /path/to/gpu_worker/server_trellis.py .
    export GPU_WORKER_TOKEN=some-secret
    export TRELLIS_MODEL=JeffreyXiang/TRELLIS-image-large
    uvicorn server_trellis:app --host 0.0.0.0 --port 8000
"""

import base64
import io
import math
import os
from collections import deque

import numpy as np
import torch
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from PIL import Image, ImageEnhance, ImageFilter

from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.utils import render_utils

TOKEN = os.getenv("GPU_WORKER_TOKEN", "").strip()
MODEL = os.getenv("TRELLIS_MODEL", "JeffreyXiang/TRELLIS-image-large")
RENDER_RES = int(os.getenv("TRELLIS_RENDER_RES", "512"))
PITCH = float(os.getenv("TRELLIS_PITCH", "0.1"))
RADIUS = float(os.getenv("TRELLIS_RADIUS", "2.0"))
FOV = float(os.getenv("TRELLIS_FOV", "40"))
BG_COLOR = tuple(float(x) for x in os.getenv("TRELLIS_BG", "1,1,1").split(","))

# Sampling quality: 24 steps is the sweet-spot for RTX 4090 (doubles quality vs 12,
# adds ~35s). Increase via env vars on slower GPUs if timeout allows.
SS_STEPS = int(os.getenv("TRELLIS_SS_STEPS", "24"))
SLAT_STEPS = int(os.getenv("TRELLIS_SLAT_STEPS", "24"))
SS_CFG = float(os.getenv("TRELLIS_SS_CFG", "7.5"))
SLAT_CFG = float(os.getenv("TRELLIS_SLAT_CFG", "3.0"))

# White-bg flood-fill tolerance: pixels within this distance from #FFFFFF are bg.
BG_TOLERANCE = int(os.getenv("TRELLIS_BG_TOLERANCE", "20"))

os.environ.setdefault("ATTN_BACKEND", "flash-attn")
os.environ.setdefault("SPCONV_ALGO", "native")

app = FastAPI(title="turnaround-gpu-worker-trellis")
_pipe = None


def _get_pipe():
    global _pipe
    if _pipe is None:
        pipe = TrellisImageTo3DPipeline.from_pretrained(MODEL)
        pipe.cuda()
        _pipe = pipe
    return _pipe


def _remove_white_bg(img: Image.Image, tolerance: int = BG_TOLERANCE) -> Image.Image:
    """BFS flood-fill from all image edges to remove pure-white background.

    Only pixels *connected* to the image border are removed.  White product
    details in the interior (guitar strings, paper sheet, white surfaces) are
    untouched — they cannot be reached by the fill because the product outline
    breaks the connectivity.  Far safer than rembg/u2net for white products.
    """
    rgb = np.array(img.convert("RGB"))
    h, w = rgb.shape[:2]
    alpha = np.full((h, w), 255, dtype=np.uint8)
    visited = np.zeros((h, w), dtype=bool)
    thresh = 255 - tolerance

    q: deque = deque()

    def _seed(y: int, x: int) -> None:
        if not visited[y, x]:
            r, g, b = rgb[y, x]
            if r >= thresh and g >= thresh and b >= thresh:
                visited[y, x] = True
                q.append((y, x))

    for x in range(w):
        _seed(0, x)
        _seed(h - 1, x)
    for y in range(1, h - 1):
        _seed(y, 0)
        _seed(y, w - 1)

    while q:
        y, x = q.popleft()
        alpha[y, x] = 0
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                _seed(ny, nx)

    rgba = np.dstack([rgb, alpha])
    return Image.fromarray(rgba, "RGBA")


def _on_white(img: Image.Image) -> Image.Image:
    """Composite RGBA image onto solid white, return RGB."""
    img = img.convert("RGBA")
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    white.paste(img, (0, 0), img)
    return white.convert("RGB")


def _stylize_frame(img: Image.Image) -> Image.Image:
    """Post-process a rendered TRELLIS frame to match illustration style.

    TRELLIS gaussian-splat renders are slightly desaturated and soft compared
    to flux-kontext reference images.  These PIL-only adjustments (zero GPU
    cost) bring contrast, color, and sharpness closer to the reference style.
    """
    img = ImageEnhance.Contrast(img).enhance(1.25)
    img = ImageEnhance.Color(img).enhance(1.25)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=100, threshold=3))
    return img


def _frame_to_image(frame: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8), "RGB")


def _encode(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _render_turnaround(sample, views: int) -> list[Image.Image]:
    """Level orbit around yaw -> clean turnaround views."""
    yaws = [2 * math.pi * i / views for i in range(views)]
    pitchs = [PITCH] * views
    extr, intr = render_utils.yaw_pitch_r_fov_to_extrinsics_intrinsics(
        yaws, pitchs, RADIUS, FOV
    )
    result = render_utils.render_frames(
        sample, extr, intr, {"resolution": RENDER_RES, "bg_color": BG_COLOR}
    )
    return [_stylize_frame(_frame_to_image(f)) for f in result["color"]]


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL, "cuda": torch.cuda.is_available()}


@app.post("/generate")
async def generate(
    image: UploadFile = File(...),
    views: int = Form(5),
    authorization: str = Header(default=""),
):
    if TOKEN and authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="bad token")

    raw = await image.read()
    cond = Image.open(io.BytesIO(raw)).convert("RGB")

    # Flood-fill removes the white background while keeping white product parts.
    # Compositing back on white gives TRELLIS a clean, white-bg RGB image.
    cond = _on_white(_remove_white_bg(cond))

    pipe = _get_pipe()
    outputs = pipe.run(
        cond,
        seed=1,
        formats=["gaussian"],
        sparse_structure_sampler_params={"steps": SS_STEPS, "cfg_strength": SS_CFG},
        slat_sampler_params={"steps": SLAT_STEPS, "cfg_strength": SLAT_CFG},
    )
    sample = outputs["gaussian"][0]

    views = max(1, min(int(views), 12))
    frames = _render_turnaround(sample, views)
    return {"views": [_encode(f) for f in frames]}
