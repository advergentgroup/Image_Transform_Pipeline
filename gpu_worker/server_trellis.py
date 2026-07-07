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

import numpy as np
import torch
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from PIL import Image
from rembg import remove as rembg_remove

from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.utils import render_utils

TOKEN = os.getenv("GPU_WORKER_TOKEN", "").strip()
MODEL = os.getenv("TRELLIS_MODEL", "JeffreyXiang/TRELLIS-image-large")
RENDER_RES = int(os.getenv("TRELLIS_RENDER_RES", "512"))
# Level turnaround: pitch ~0 = eye-level side view. Small positive tilts the
# camera slightly down so the top is visible. Radius / FOV match TRELLIS demo.
PITCH = float(os.getenv("TRELLIS_PITCH", "0.1"))
RADIUS = float(os.getenv("TRELLIS_RADIUS", "2.0"))
FOV = float(os.getenv("TRELLIS_FOV", "40"))
# Gaussian renderer background as 0-1 floats. White (1,1,1) renders the product
# directly on white so no color-keying is needed (dark parts no longer vanish).
# Override via TRELLIS_BG="r,g,b" if a build expects 0-255 (use "255,255,255").
BG_COLOR = tuple(float(x) for x in os.getenv("TRELLIS_BG", "1,1,1").split(","))

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


def _on_white(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    white.paste(img, (0, 0), img)
    return white.convert("RGB")


def _frame_to_image(frame: np.ndarray) -> Image.Image:
    """Frames render directly on white (bg_color=1,1,1) — no color keying needed, so
    dark product parts (black tires, dark trim) survive instead of being keyed white."""
    return Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8), "RGB")


def _encode(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _render_turnaround(sample, views: int) -> list[Image.Image]:
    """Level orbit around yaw -> clean turnaround views (no vertical bobbing).

    Uses TRELLIS's own camera builder with the SAME signature its render_video uses:
    yaw_pitch_r_fov_to_extrinsics_intrinsics(yaws, pitchs, r, fov) — r/fov positional
    scalars. Constant pitch keeps every view at the same height (fixes the
    "looking from below" artifact of Zero123++'s fixed poses).
    """
    yaws = [2 * math.pi * i / views for i in range(views)]
    pitchs = [PITCH] * views
    extr, intr = render_utils.yaw_pitch_r_fov_to_extrinsics_intrinsics(
        yaws, pitchs, RADIUS, FOV
    )
    result = render_utils.render_frames(
        sample, extr, intr, {"resolution": RENDER_RES, "bg_color": BG_COLOR}
    )
    return [_frame_to_image(f) for f in result["color"]]


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
    cond = _on_white(rembg_remove(cond))

    pipe = _get_pipe()
    outputs = pipe.run(cond, seed=1, formats=["gaussian"])
    sample = outputs["gaussian"][0]

    views = max(1, min(int(views), 12))
    frames = _render_turnaround(sample, views)
    return {"views": [_encode(f) for f in frames]}
