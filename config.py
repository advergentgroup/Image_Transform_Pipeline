import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max upload

    # Folders
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "tmp/uploads")
    OUTPUT_FOLDER = os.getenv("OUTPUT_FOLDER", "tmp/outputs")

    # AI — uniquify: pillow (filters only) | flux-redux (recommended) | sd-img2img (legacy)
    REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
    UNIQUE_MODE = os.getenv("UNIQUE_MODE", "pillow")
    UNIQUIFY_FILTER_STRENGTH = float(os.getenv("UNIQUIFY_FILTER_STRENGTH", "1.0"))

    THREED_MODEL = os.getenv("THREED_MODEL", "flux-kontext-pro")
    # THREED_MODE — legacy (unused by default vector pipeline):
    #   depth-guided = algorithmic 3D (100% Hive-safe, < 5%, good quality) ← DEFAULT
    #   kontext      = real FLUX 3D AI render (great quality but ~99% Hive, needs postprocess)
    THREED_MODE = os.getenv("THREED_MODE", "depth-guided")
    DEPTH_GUIDED_STRENGTH = float(os.getenv("DEPTH_GUIDED_STRENGTH", "1.3"))
    DEPTH_GUIDED_GRID = int(os.getenv("DEPTH_GUIDED_GRID", "24"))
    DEPTH_GUIDED_COLORS = int(os.getenv("DEPTH_GUIDED_COLORS", "48"))
    CEL_SHADER_COLORS = int(os.getenv("CEL_SHADER_COLORS", "24"))
    THREED_WHITE_BACKGROUND = os.getenv("THREED_WHITE_BACKGROUND", "0")

    FLUX_REDUX_MODEL = os.getenv("FLUX_REDUX_MODEL", "black-forest-labs/flux-redux-dev")
    FLUX_DEV_MODEL = os.getenv("FLUX_DEV_MODEL", "black-forest-labs/flux-dev")
    FLUX_KONTEXT_MODEL = os.getenv(
        "FLUX_KONTEXT_MODEL", "black-forest-labs/flux-kontext-pro"
    )
    FLUX_TURNAROUND_MODEL = os.getenv(
        "FLUX_TURNAROUND_MODEL", "black-forest-labs/flux-kontext-pro"
    )
    # kontext = one 16:9 turnaround sheet (best for flat vector clipart)
    # qwen / gpu-worker try to rotate/reconstruct 3D — poor on flat illustrations
    TURNAROUND_MODE = os.getenv("TURNAROUND_MODE", "kontext").lower()
    QWEN_MULTIANGLE_MODEL = os.getenv("QWEN_MULTIANGLE_MODEL", "qwen/qwen-edit-multiangle")
    QWEN_ROTATE_DEGREES = os.getenv("QWEN_ROTATE_DEGREES", "-90,-45,0,45,90")
    # qwen-multi: views per call (2,3 -> 5 views in 2 calls) + chroma-key backdrop color
    QWEN_MULTI_SPLIT = os.getenv("QWEN_MULTI_SPLIT", "2,3")
    QWEN_CHROMA_COLOR = os.getenv("QWEN_CHROMA_COLOR", "0,177,64")
    # gpu-worker: rented-GPU FastAPI service (Zero123++/TRELLIS) for turnaround views
    GPU_WORKER_URL = os.getenv("GPU_WORKER_URL", "")
    GPU_WORKER_TOKEN = os.getenv("GPU_WORKER_TOKEN", "")
    GPU_WORKER_TIMEOUT = os.getenv("GPU_WORKER_TIMEOUT", "180")
    GPU_WORKER_VIEWS = os.getenv("GPU_WORKER_VIEWS", "5")
    QWEN_TURNAROUND_PROMPT = os.getenv(
        "QWEN_TURNAROUND_PROMPT",
        "Keep the exact same clean vector illustration style, flat colors, crisp outlines, "
        "minimal shading. Solid white background #FFFFFF. No floor, no shadows on background.",
    )
    TURNAROUND_SHEET_WIDTH = os.getenv("TURNAROUND_SHEET_WIDTH", "")
    TURNAROUND_SHEET_HEIGHT = os.getenv("TURNAROUND_SHEET_HEIGHT", "")
    # Reference 9:16 portrait + turnaround 16:9 landscape — preset key or custom REFERENCE_* / TURNAROUND_*
    OUTPUT_SIZE = os.getenv("OUTPUT_SIZE", "2880")
    REFERENCE_WIDTH = os.getenv("REFERENCE_WIDTH", "")
    REFERENCE_HEIGHT = os.getenv("REFERENCE_HEIGHT", "")
    FLUX_TURNAROUND_LORA_MODEL = os.getenv(
        "FLUX_TURNAROUND_LORA_MODEL", "black-forest-labs/flux-kontext-dev-lora"
    )
    TURNAROUND_LORA_URL = os.getenv(
        "TURNAROUND_LORA_URL",
        "https://huggingface.co/reverentelusarca/kontext-turnaround-sheet-lora-v1/"
        "resolve/main/kontext-turnaround-sheet-v1.safetensors",
    )
    TURNAROUND_LORA_STRENGTH = float(os.getenv("TURNAROUND_LORA_STRENGTH", "1.0"))
    FLUX_REDUX_GUIDANCE = float(os.getenv("FLUX_REDUX_GUIDANCE", "2.5"))
    FLUX_DEV_GUIDANCE = float(os.getenv("FLUX_DEV_GUIDANCE", "3.5"))
    FLUX_DEV_STEPS = int(os.getenv("FLUX_DEV_STEPS", "35"))
    # go_fast=1 uses fp8 on Replicate — faster but softer/blurrier; 0 = full quality
    FLUX_DEV_GO_FAST = os.getenv("FLUX_DEV_GO_FAST", "0")
    FLUX_DEV_MEGAPIXELS = os.getenv("FLUX_DEV_MEGAPIXELS", "1")
    FLUX_KONTEXT_GUIDANCE = float(os.getenv("FLUX_KONTEXT_GUIDANCE", "2.5"))
    FLUX_KONTEXT_STEPS = int(os.getenv("FLUX_KONTEXT_STEPS", "28"))
    # Replicate: with balance < $5 → ~6 predictions/min, burst 1
    REPLICATE_REQUEST_DELAY = float(os.getenv("REPLICATE_REQUEST_DELAY", "11"))
    REPLICATE_RATE_LIMIT_RETRIES = int(os.getenv("REPLICATE_RATE_LIMIT_RETRIES", "8"))
    REPLICATE_TIMEOUT_SECONDS = float(os.getenv("REPLICATE_TIMEOUT_SECONDS", "600"))

    VECTOR_MODE = os.getenv("VECTOR_MODE", "posterize")
    VECTOR_TRACE_COLORS = int(os.getenv("VECTOR_TRACE_COLORS", "16"))
    VECTOR_TRACE_NOISE = int(os.getenv("VECTOR_TRACE_NOISE", "4"))
    VECTOR_BG_TOLERANCE = int(os.getenv("VECTOR_BG_TOLERANCE", "40"))
    VECTOR_OUTPUT_MAX_SIDE = int(os.getenv("VECTOR_OUTPUT_MAX_SIDE", "2048"))
    # illustrator mode: show Illustrator window during trace (debug)
    ILLUSTRATOR_VISIBLE = os.getenv("ILLUSTRATOR_VISIBLE", "0")
    ILLUSTRATOR_PATH_FIDELITY = int(os.getenv("ILLUSTRATOR_PATH_FIDELITY", "95"))
    ILLUSTRATOR_CORNER_FIDELITY = int(os.getenv("ILLUSTRATOR_CORNER_FIDELITY", "95"))
    ILLUSTRATOR_EXPORT_SCALE = int(os.getenv("ILLUSTRATOR_EXPORT_SCALE", "200"))
    ILLUSTRATOR_NOISE_FIDELITY = int(os.getenv("ILLUSTRATOR_NOISE_FIDELITY", "2"))
    ILLUSTRATOR_TRACING_METHOD = os.getenv("ILLUSTRATOR_TRACING_METHOD", "abutting")

    # Legacy SD 1.5 img2img (poor quality for cartoons — avoid unless testing)
    IMG2IMG_MODEL = os.getenv(
        "IMG2IMG_MODEL",
        "stability-ai/stable-diffusion-img2img:15a3689ee13b0d2616e98820eca31d4c3abcd36672df6afce5cb6feb1d66087d",
    )
    IMG2IMG_STRENGTH = float(os.getenv("IMG2IMG_STRENGTH", "0.25"))
    IMG2IMG_3D_STRENGTH = float(os.getenv("IMG2IMG_3D_STRENGTH", "0.55"))

    # Hive AI-generated content detection (V3 Playground)
    # https://docs.thehive.ai/docs/ai-generated-and-deepfake-content-detection-playground
    HIVEDETECT_API_KEY = os.getenv("HIVEDETECT_API_KEY", "")
    HIVEDETECT_URL = os.getenv(
        "HIVEDETECT_URL",
        "https://api.thehive.ai/api/v3/hive/ai-generated-and-deepfake-content-detection",
    )
    HIVEDETECT_USE_MOCK = os.getenv("HIVEDETECT_USE_MOCK", "0")
    HIVEDETECT_TARGET_SCORE = float(os.getenv("HIVEDETECT_TARGET_SCORE", "10"))
    HIVEDETECT_MAX_RETRIES = int(os.getenv("HIVEDETECT_MAX_RETRIES", "3"))
    HIVEDETECT_HUMANIZE_INTENSITY = int(os.getenv("HIVEDETECT_HUMANIZE_INTENSITY", "6"))

    # Processing
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
    OUTPUT_IMAGE_FORMAT = os.getenv("OUTPUT_IMAGE_FORMAT", "jpeg").lower()
    OUTPUT_JPEG_QUALITY = int(os.getenv("OUTPUT_JPEG_QUALITY", "92"))
    MAX_FILES_PER_JOB = int(os.getenv("MAX_FILES_PER_JOB", "100"))
    MAX_STYLE_REFS = int(os.getenv("MAX_STYLE_REFS", "10"))
    # Product reference/turnaround background: none | edge (default) | illustrator
    PRODUCT_BG_MODE = os.getenv("PRODUCT_BG_MODE", "edge").lower()
    PRODUCT_BG_TOLERANCE = int(os.getenv("PRODUCT_BG_TOLERANCE", os.getenv("VECTOR_BG_TOLERANCE", "40")))

    # User-editable prompts (Settings tab) — stored in JSON, not .env
    SETTINGS_FILE = os.getenv("SETTINGS_FILE", "tmp/settings.json")
