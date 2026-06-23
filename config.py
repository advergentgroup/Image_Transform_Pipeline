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

    # AI
    REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
    IMG2IMG_MODEL = os.getenv(
        "IMG2IMG_MODEL",
        "stability-ai/stable-diffusion-img2img:15a3689ee13b0d2616e98820eca31d4c3abcd36672df6afce5cb6feb1d66087d",
    )
    IMG2IMG_STRENGTH = float(os.getenv("IMG2IMG_STRENGTH", "0.25"))
    IMG2IMG_3D_STRENGTH = float(os.getenv("IMG2IMG_3D_STRENGTH", "0.55"))

    # Hivedetect
    HIVEDETECT_API_KEY = os.getenv("HIVEDETECT_API_KEY", "")
    HIVEDETECT_URL = "https://hivedetect.ai/api/check"

    # Processing
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
    MAX_FILES_PER_JOB = 10  # MVP limit
