# GPU turnaround worker (Zero123++)

Runs on a rented GPU and turns one product reference into N novel views for the
turnaround sheet. The main app talks to it via `TURNAROUND_MODE=gpu-worker`.

**Why:** at ~1000 items/day the per-view API cost ($0.06/item on Qwen ≈ $1800/mo)
is replaced by GPU rental only (RTX 3060 ≈ $0.05/h, RTX 3090 ≈ $0.14/h → tens of $/mo).

## 1. Rent the GPU (SimplePod)
- Type: **Docker GPU** (cheapest, instant).
- Card: **RTX 3060 12GB** (Zero123++ fits) or **RTX 3090 24GB** (headroom / TRELLIS later).
- Template: **PyTorch** (CUDA + torch preinstalled).
- Add **Network Storage** and point the HF cache there so weights persist:
  `export HF_HOME=/workspace/hf-cache`

## 2. Install + run the worker
```bash
git clone <this repo> && cd Image_Transform_Pipeline/gpu_worker
export HF_HOME=/workspace/hf-cache          # persist model weights on network storage
pip install -r requirements.txt
export GPU_WORKER_TOKEN=choose-a-secret      # must match GPU_WORKER_TOKEN in app .env
export ZERO123_STEPS=75                       # lower = faster
uvicorn server:app --host 0.0.0.0 --port 8000
```

Test it:
```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/generate \
  -H "Authorization: Bearer choose-a-secret" \
  -F "image=@reference.png" -F "views=5" | head -c 200
```

## 3. Expose a stable URL
SimplePod Docker forwards a **random port** (no fixed public IP). Two options:
- Use the forwarded `host:port` SimplePod shows, and put it in the app `.env` as
  `GPU_WORKER_URL` (update whenever it changes on restart).
- Or a stable tunnel:
  ```bash
  cloudflared tunnel --url http://localhost:8000
  ```
  and use the printed `https://...trycloudflare.com` URL.

## 4. Point the app at the worker
In the main app `.env`:
```
TURNAROUND_MODE=gpu-worker
GPU_WORKER_URL=https://<your-host-or-tunnel>
GPU_WORKER_TOKEN=choose-a-secret
GPU_WORKER_VIEWS=5
GPU_WORKER_TIMEOUT=180
```
Restart `py app.py` and run a job — the turnaround now comes from the GPU worker.

## Notes / tradeoffs
- **Thin geometry** (bike spokes) is the known weak spot of Zero123++. Validate on a
  real product before committing to 1000/day. If quality is poor, switch the card to
  RTX 3090 and use the **TRELLIS** worker below.
- Zero123++ returns 6 fixed views; `GPU_WORKER_VIEWS` picks how many go into the sheet.
- Keep `TURNAROUND_MODE=qwen-multi` as a fallback for items where 3D quality fails.

---

# TRELLIS variant (`server_trellis.py`)

Higher-quality 3D than Zero123++ — better for thin/detailed products. Needs **RTX 3090
(24GB)**. Unlike Zero123++, TRELLIS is **not** a simple pip install; run the worker from
inside the cloned TRELLIS repo.

## Instance requirements (IMPORTANT — learned the hard way)
TRELLIS compiles CUDA extensions (flash-attn, spconv, nvdiffrast, diffoctreerast,
mipgaussian) at install time. It only works on a properly matched box:
- **GPU:** RTX 3090 24GB (or better).
- **Disk:** **≥ 60 GB** (weights ~6 GB + build artifacts + torch). A 16 GB overlay
  with ~3 GB free will fail immediately.
- **Image:** **CUDA 12.1 *devel*** (nvcc required to compile), e.g. Vast template
  `pytorch/pytorch:2.4.0-cuda12.1-cudnn9-devel`. torch 2.4 + cu121 has prebuilt
  wheels for the extensions. A bleeding-edge torch 2.12/cu130 box will NOT build
  flash-attn/spconv — do not attempt TRELLIS there.

## Setup on the GPU box
```bash
# 1. Clone + install TRELLIS (follow its README for CUDA-matched wheels)
git clone --recurse-submodules https://github.com/microsoft/TRELLIS.git
cd TRELLIS
. ./setup.sh --new-env --basic --flash-attn --diffoctreerast --spconv --mipgaussian --nvdiffrast
pip install fastapi "uvicorn[standard]" python-multipart rembg onnxruntime-gpu

# 2. Drop the worker in and run (from the TRELLIS repo root)
cp /path/to/Image_Transform_Pipeline/gpu_worker/server_trellis.py .
export HF_HOME=/workspace/hf-cache          # persist weights on network storage
export GPU_WORKER_TOKEN=choose-a-secret
export TRELLIS_MODEL=JeffreyXiang/TRELLIS-image-large
uvicorn server_trellis:app --host 0.0.0.0 --port 8000
```

Steps 3 (expose URL) and 4 (point the app at it) are identical to the Zero123++ worker
above — same `/generate` contract, so `TURNAROUND_MODE=gpu-worker` needs no changes.

## Notes
- Slower than Zero123++ (~20-40s/item) but far better geometry.
- `_render_turnaround()` in `server_trellis.py` targets TRELLIS's `render_utils`. If your
  installed version's API differs, adjust that one function (it already falls back to
  `render_video` frame sampling).
