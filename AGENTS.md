# Image Transform Pipeline — agent guide

## Repo
- GitHub: `git@github.com:NazarFedus/Image_Transform_Pipeline_WEB.git`
- Branch: `main`

## What it does
Flask app: upload cartoon JPG/PNG → pipeline produces ZIP with:
- `vector/` — 16-color posterize + radial gradient (#E0FFFF → #40E0D0)
- `3d/` — FLUX Kontext Pro Pixar-style 3D render

Hive V3 scores both outputs (target < 10% on 3D is hard; raw Kontext ≈ 100%).

## Stack
- Python 3.13, Flask, gunicorn, Pillow, numpy, scipy, vtracer, resvg_py
- Replicate API: `flux-kontext-pro` for 3D
- Docker: `docker compose up -d --build` (port 8080)

## Key files
- `backend/core/pipeline.py` — orchestrator
- `backend/services/ai_service.py` — Replicate FLUX
- `backend/services/image_service.py` — vectorize, humanize, depth-guided (optional)
- `config.py` / `.env` — secrets (never commit `.env`)

## Env (copy from `.env.example`)
```
THREED_MODE=kontext          # real 3D (default)
REPLICATE_API_TOKEN=...
HIVEDETECT_API_KEY=...
UNIQUE_MODE=pillow
VECTOR_MODE=posterize
```

## Deploy (server)
```bash
git clone git@github.com:NazarFedus/Image_Transform_Pipeline_WEB.git
cd Image_Transform_Pipeline_WEB
cp .env.example .env   # fill keys
docker compose up -d --build
```

## Known constraints
- Raw Kontext 3D passes quality but fails Hive (~100%)
- `THREED_MODE=depth-guided` passes Hive but loses real 3D look
- Do not add heavy postprocess that ruins Kontext output without user approval
