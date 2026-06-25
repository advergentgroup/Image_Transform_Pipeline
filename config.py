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
    # kontext = real FLUX 3D (default) | pseudo3d = flat Hive-safe fallback only
    THREED_MODE = os.getenv("THREED_MODE", "kontext")
    THREED_MODEL = os.getenv("THREED_MODEL", "flux-kontext-pro")

    FLUX_REDUX_MODEL = os.getenv("FLUX_REDUX_MODEL", "black-forest-labs/flux-redux-dev")
    FLUX_KONTEXT_MODEL = os.getenv(
        "FLUX_KONTEXT_MODEL", "black-forest-labs/flux-kontext-pro"
    )
    FLUX_REDUX_GUIDANCE = float(os.getenv("FLUX_REDUX_GUIDANCE", "2.5"))
    FLUX_KONTEXT_GUIDANCE = float(os.getenv("FLUX_KONTEXT_GUIDANCE", "2.5"))
    FLUX_KONTEXT_STEPS = int(os.getenv("FLUX_KONTEXT_STEPS", "28"))

    VECTOR_MODE = os.getenv("VECTOR_MODE", "posterize")
    VECTOR_TRACE_COLORS = int(os.getenv("VECTOR_TRACE_COLORS", "16"))
    VECTOR_TRACE_NOISE = int(os.getenv("VECTOR_TRACE_NOISE", "4"))

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
    HIVEDETECT_MAX_RETRIES = int(os.getenv("HIVEDETECT_MAX_RETRIES", "0"))

    # Processing
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
    MAX_FILES_PER_JOB = 10  # MVP limit

    # User-editable prompts (Settings tab) — stored in JSON, not .env
    SETTINGS_FILE = os.getenv("SETTINGS_FILE", "tmp/settings.json")
