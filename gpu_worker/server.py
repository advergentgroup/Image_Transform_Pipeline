"""GPU turnaround worker — run this on a rented GPU (SimplePod RTX 3060/3090).

Takes one product reference image and returns N novel views (base64 PNGs on white)
using Zero123++. The main Flask app calls this via TURNAROUND_MODE=gpu-worker.

Run:
    export GPU_WORKER_TOKEN=some-secret          # optional but recommended
    export ZERO123_STEPS=75                       # quality/speed tradeoff
    uvicorn server:app --host 0.0.0.0 --port 8000

Cost model: you pay only for GPU rental time (~$0.05-0.14/h), not per view.
"""

import base64
import io
import os

import torch
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from PIL import Image

try:
    from diffusers import DiffusionPipeline, EulerAncestralDiscreteScheduler
except ImportError as exc:  # pragma: no cover - runtime dependency on GPU box
    raise SystemExit(
        "Install worker deps first:  pip install -r requirements.txt"
    ) from exc

from rembg import remove as rembg_remove

TOKEN = os.getenv("GPU_WORKER_TOKEN", "").strip()
STEPS = int(os.getenv("ZERO123_STEPS", "75"))
MODEL = os.getenv("ZERO123_MODEL", "sudo-ai/zero123plus-v1.2")

app = FastAPI(title="turnaround-gpu-worker")
_pipe = None


def _get_pipe():
    """Lazy-load Zero123++ once, keep it warm in VRAM."""
    global _pipe
    if _pipe is None:
        pipe = DiffusionPipeline.from_pretrained(
            MODEL,
            custom_pipeline="sudo-ai/zero123plus-pipeline",
            torch_dtype=torch.float16,
        )
        pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(
            pipe.scheduler.config, timestep_spacing="trailing"
        )
        pipe.to("cuda")
        _pipe = pipe
    return _pipe


def _on_white(rgba: Image.Image) -> Image.Image:
    """Composite an RGBA cutout onto a flat white background."""
    rgba = rgba.convert("RGBA")
    white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    white.paste(rgba, (0, 0), rgba)
    return white.convert("RGB")


def _split_grid(grid: Image.Image, cols: int = 2, rows: int = 3) -> list[Image.Image]:
    """Zero123++ returns a 2x3 grid of 320px tiles — split into 6 views (row-major)."""
    w, h = grid.size
    tw, th = w // cols, h // rows
    tiles = []
    for r in range(rows):
        for c in range(cols):
            tiles.append(grid.crop((c * tw, r * th, c * tw + tw, r * th + th)))
    return tiles


def _encode(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


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
    # Zero123++ works best on a clean isolated object.
    cond = _on_white(rembg_remove(cond))

    pipe = _get_pipe()
    grid = pipe(cond, num_inference_steps=STEPS).images[0]

    tiles = _split_grid(grid)
    views = max(1, min(int(views), len(tiles)))
    out = [_encode(_on_white(rembg_remove(t))) for t in tiles[:views]]
    return {"views": out}
