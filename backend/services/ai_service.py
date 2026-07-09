import logging
import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import replicate
import requests
from PIL import Image

from backend.utils.image_output import resize_and_save, save_bytes_as_output, save_image

from backend.core.output_sizes import resolve_output_dimensions

# Module-level rate limiter — serialises Replicate calls across all threads so
# concurrent turnaround workers don't trigger 429s when many images run together.
_replicate_rate_lock = threading.Lock()
_replicate_last_call: float = 0.0

logger = logging.getLogger(__name__)


class ReplicateBalanceError(RuntimeError):
    """Replicate credits exhausted — pipeline should stop gracefully."""


class ReplicateThrottleError(RuntimeError):
    """Replicate rate limit hit — pipeline should stop at last successful image."""


_BALANCE_MARKERS = (
    "insufficient credit",
    "insufficient balance",
    "payment required",
    "out of credit",
    "billing",
    "402",
    "spend limit",
    "quota",
)

_RATE_LIMIT_MARKERS = (
    "429",
    "throttl",
    "rate limit",
    "too many requests",
)


def _is_timeout_error(exc: Exception) -> bool:
    return isinstance(
        exc, (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout)
    )


def _raise_if_balance_error(exc: Exception) -> None:
    msg = str(exc).lower()
    if any(marker in msg for marker in _BALANCE_MARKERS):
        raise ReplicateBalanceError(
            "Replicate balance exhausted. Stopped at the last successful image."
        ) from exc


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in _RATE_LIMIT_MARKERS)


def _retry_wait_seconds(exc: Exception, fallback: float) -> float:
    msg = str(exc).lower()
    match = re.search(r"resets in ~(\d+)\s*s", msg)
    if match:
        return max(fallback, float(match.group(1)) + 1.0)
    match = re.search(r"resets in ~(\d+)\s*m", msg)
    if match:
        return max(fallback, float(match.group(1)) * 60.0 + 1.0)
    return fallback


class AIService:
    """
    Replicate API wrappers:
      - flux-dev — text-to-image product reference
      - flux-kontext-pro — style-guided product reference
      - flux-kontext-dev-lora + turnaround LoRA — optional (characters only)
      - qwen-edit-multiangle — product turnaround (~$0.025/view)
      - flux-kontext-dev — single-call fallback (~$0.025)
      - flux-redux-dev — legacy uniquify
    """

    TURNAROUND_LORA_URL = (
        "https://huggingface.co/reverentelusarca/kontext-turnaround-sheet-lora-v1/"
        "resolve/main/kontext-turnaround-sheet-v1.safetensors"
    )

    PRODUCT_REFERENCE_PROMPT = (
        "classic red city bicycle, side view, isolated on pure white background, centered "
        "composition, clean vector illustration, smooth outlines, flat colors, minimal shading, "
        "high detail, clipart style, no people, no text"
    )

    PRODUCT_CATALOG_PROMPTS = (
        "classic red city bicycle, side view, isolated on pure white background, centered composition, clean vector illustration, smooth outlines, flat colors, minimal shading, high detail, clipart style, no people, no text",
        "luxury motor yacht, front view, isolated on pure white background, centered composition, clean vector illustration, crisp outlines, flat colors, minimal shading, no shadow",
        "wooden rocking chair with beige cushion, front view, isolated on pure white background, centered composition, clean vector illustration, simple shading",
        "ornate vintage wooden cabinet with decorative mirror, front view, isolated on pure white background, centered composition, elegant vector illustration",
        "red lifeguard tower, front view, isolated on pure white background, centered composition, clean vector illustration",
        "modern office chair, front view, isolated on pure white background, centered composition, flat vector illustration",
        "wooden dining table, front view, isolated on pure white background, centered composition, vector clipart style",
        "upholstered sofa, front view, isolated on pure white background, centered composition, clean vector illustration",
        "wooden bookshelf filled with books, front view, isolated on pure white background, centered composition, vector illustration",
        "bedside table with drawer, front view, isolated on pure white background, centered composition, vector illustration",
        "floor lamp, front view, isolated on pure white background, centered composition, vector illustration",
        "table lamp, front view, isolated on pure white background, centered composition, clean vector illustration",
        "grandfather clock, front view, isolated on pure white background, centered composition, vector illustration",
        "wall clock, front view, isolated on pure white background, centered composition, vector illustration",
        "mailbox, front view, isolated on pure white background, centered composition, vector illustration",
        "fire hydrant, front view, isolated on pure white background, centered composition, vector illustration",
        "park bench, front view, isolated on pure white background, centered composition, clean vector illustration",
        "picnic table, front view, isolated on pure white background, centered composition, vector illustration",
        "garden swing, front view, isolated on pure white background, centered composition, vector illustration",
        "birdhouse, front view, isolated on pure white background, centered composition, vector illustration",
        "wooden ladder, front view, isolated on pure white background, centered composition, vector illustration",
        "wheelbarrow, side view, isolated on pure white background, centered composition, vector illustration",
        "watering can, side view, isolated on pure white background, centered composition, vector illustration",
        "flower pot with green plant, front view, isolated on pure white background, centered composition, vector illustration",
        "cactus in ceramic pot, front view, isolated on pure white background, centered composition, vector illustration",
        "ceramic vase, front view, isolated on pure white background, centered composition, vector illustration",
        "teapot, side view, isolated on pure white background, centered composition, vector illustration",
        "coffee mug, side view, isolated on pure white background, centered composition, vector illustration",
        "wine bottle, front view, isolated on pure white background, centered composition, vector illustration",
        "glass bottle, front view, isolated on pure white background, centered composition, vector illustration",
        "wooden barrel, front view, isolated on pure white background, centered composition, vector illustration",
        "treasure chest, front view, isolated on pure white background, centered composition, vector illustration",
        "suitcase, front view, isolated on pure white background, centered composition, vector illustration",
        "backpack, front view, isolated on pure white background, centered composition, vector illustration",
        "acoustic guitar, front view, isolated on pure white background, centered composition, vector illustration",
        "grand piano, front view, isolated on pure white background, centered composition, vector illustration",
        "violin, front view, isolated on pure white background, centered composition, vector illustration",
        "drum set, front view, isolated on pure white background, centered composition, vector illustration",
        "trumpet, side view, isolated on pure white background, centered composition, vector illustration",
        "saxophone, front view, isolated on pure white background, centered composition, vector illustration",
        "telescope, side view, isolated on pure white background, centered composition, vector illustration",
        "microscope, front view, isolated on pure white background, centered composition, vector illustration",
        "camera, front view, isolated on pure white background, centered composition, vector illustration",
        "vintage radio, front view, isolated on pure white background, centered composition, vector illustration",
        "television, front view, isolated on pure white background, centered composition, vector illustration",
        "desktop computer, front view, isolated on pure white background, centered composition, vector illustration",
        "laptop computer, open front view, isolated on pure white background, centered composition, vector illustration",
        "keyboard, top view, isolated on pure white background, centered composition, vector illustration",
        "computer mouse, top view, isolated on pure white background, centered composition, vector illustration",
        "printer, front view, isolated on pure white background, centered composition, vector illustration",
    )

    CATALOG_STYLE_GUIDED_PROMPT = (
        "Use the provided image ONLY as a RENDER STYLE reference "
        "(vector illustration style, outlines, flat colors, shading level).\n\n"
        "IGNORE the background from the sample — result background is always flat pure white "
        "#FFFFFF edge to edge.\n\n"
        "Do NOT copy the object from the style sample. Generate exactly the object described below."
    )

    STYLE_GUIDED_PROMPT = (
        "Використай надане зображення лише як зразок СТИЛЮ рендеру "
        "(стилізована 3D-ілюстрація, освітлення, рівень деталізації, чіткість контурів).\n\n"
        "ІГНОРУЙ фон і тіні зі зразка — не копіюй підлогу, контактні тіні, сірі плями чи площини. "
        "Фон результату завжди суцільний чисто білий #FFFFFF від краю до краю.\n\n"
        "НЕ копіюй персонажів, людей, humanoid фігур, райдерів чи силуетів зі зразка стилю — "
        "навіть якщо вони є на style ref. Перенось лише стиль рендеру (3D, освітлення, деталізація), "
        "не суб'єктів і не сцен.\n\n"
        "Не копіюй і не повторюй об'єкт, форму, колір чи категорію з референсу.\n\n"
        "Згенеруй повністю інший об'єкт згідно з інструкціями нижче."
    )

    TURNAROUND_PROMPT = (
        "Based on the provided product reference image, create one 16:9 turnaround sheet.\n\n"
        "Exactly 5 views of the SAME object in one horizontal row, left to right:\n"
        "1. Front 3/4 Left\n"
        "2. Left Side\n"
        "3. Back\n"
        "4. Right Side\n"
        "5. Front 3/4 Right\n\n"
        "Keep the exact same clean vector illustration style from the reference: crisp outlines, "
        "flat colors, minimal shading, clipart style. NOT photorealistic, NOT 3D render. "
        "Same object shape, proportions, colors and details in every view — do not add, remove "
        "or deform parts. Do not incorrectly mirror asymmetric details.\n\n"
        "Equal scale and consistent style in all views. Background: flat pure white #FFFFFF.\n"
        "No text, labels, dimension lines, grid, floor, cast shadows, contact shadows, or environment."
    )

    KONTEXT_VIEW_PROMPTS = (
        # View 1 — Front-Left 3/4
        "TURNAROUND VIEW 1 of 5: FRONT-LEFT THREE-QUARTER VIEW.\n"
        "The camera is positioned to the LEFT of the front — the product is turned "
        "approximately 45 degrees so you see the LEFT face and part of the front face simultaneously. "
        "This is the classic product 'hero' angle from the left side.\n"
        "Keep the EXACT same object, colors, proportions and clean vector illustration style. "
        "Pure flat white background #FFFFFF. No floor, no shadows, no contact shadows.",

        # View 2 — Left Side
        "TURNAROUND VIEW 2 of 5: PURE LEFT SIDE PROFILE.\n"
        "The camera is directly to the LEFT, rotated exactly 90 degrees from the front. "
        "You see ONLY the left side face of the product — no front, no back visible at all. "
        "Full left side silhouette, pure side-on view.\n"
        "Keep the EXACT same object, colors, proportions and clean vector illustration style. "
        "Pure flat white background #FFFFFF. No floor, no shadows, no contact shadows.",

        # View 3 — Back
        "TURNAROUND VIEW 3 of 5: FULL BACK / REAR VIEW.\n"
        "The product is fully rotated 180 degrees — the camera looks at the BACK of the product. "
        "The front face is completely hidden; you see only the rear side. "
        "This is the opposite of the reference image — the back face, rear details, back panel.\n"
        "Keep the EXACT same object, colors, proportions and clean vector illustration style. "
        "Pure flat white background #FFFFFF. No floor, no shadows, no contact shadows.",

        # View 4 — Right Side
        "TURNAROUND VIEW 4 of 5: PURE RIGHT SIDE PROFILE.\n"
        "The camera is directly to the RIGHT, rotated exactly 90 degrees from the front. "
        "You see ONLY the right side face of the product — no front, no back visible at all. "
        "Full right side silhouette, pure side-on view. "
        "Note: this is the MIRROR OPPOSITE of view 2 (left side).\n"
        "Keep the EXACT same object, colors, proportions and clean vector illustration style. "
        "Pure flat white background #FFFFFF. No floor, no shadows, no contact shadows.",

        # View 5 — Front-Right 3/4
        "TURNAROUND VIEW 5 of 5: FRONT-RIGHT THREE-QUARTER VIEW.\n"
        "The camera is positioned to the RIGHT of the front — the product is turned "
        "approximately 45 degrees so you see the RIGHT face and part of the front face simultaneously. "
        "This is the mirror of view 1 but from the RIGHT side. "
        "Note: this view should look like view 1 mirrored, not identical to it.\n"
        "Keep the EXACT same object, colors, proportions and clean vector illustration style. "
        "Pure flat white background #FFFFFF. No floor, no shadows, no contact shadows.",
    )

    KONTEXT_3D_PROMPT = (
        "Transform the uploaded 2D character/image into a high-quality 3D render while "
        "preserving the original design exactly. Keep the same character identity, pose, "
        "proportions, silhouette, facial expression, colors, clothing/accessories, composition, "
        "camera angle, and background. Do not add, remove, or redesign any elements. Convert only "
        "the visual depth, lighting, materials, and surface volume from flat 2D into polished 3D. "
        "Create a clean professional 3D cartoon-style render with soft rounded forms, smooth surfaces, "
        "subtle realistic shading, gentle ambient occlusion, soft studio lighting, and a slightly "
        "glossy toy-like finish. Maintain the original color palette and all details exactly as in "
        "the reference image. The result should look like the same image recreated as a 3D character "
        "render, centered, clean, high-resolution, crisp edges, professional character art, white or "
        "original background preserved."
    )

    LEGACY_UNIQUE_PROMPT = (
        "same character, same pose, same colors, cartoon illustration, "
        "high quality, clean lines, detailed"
    )

    LEGACY_PIXAR_PROMPT = (
        "3D Pixar style, same character, same outfit, same pose, "
        "volumetric lighting, subsurface scattering, cinematic render, "
        "high detail, soft shadows, Disney Pixar animation"
    )

    NEGATIVE_PROMPT = (
        "blurry, low quality, distorted, deformed, ugly face, bad anatomy, "
        "watermark, text, extra limbs, disfigured, colored background, gradient background, "
        "gray background, floor, ground, shadow on background, environment, scenery"
    )

    _CATALOG_STYLE_SUFFIX = (
        "\n\nStyle: flat 2D vector clipart illustration only. NOT 3D render. NOT photorealistic. "
        "Vertical 9:16 portrait frame. No drop shadow, no contact shadow, no floor plane."
    )

    _WHITE_BG_SUFFIX = (
        "\n\nОБОВ'ЯЗКОВО: увесь фон — суцільний плоский чисто білий #FFFFFF від краю до краю. "
        "Без градієнта, без сірого, без кольорового фону, без підлоги. "
        "Без drop shadow, без contact shadow, без cast shadow, без контактних тіней, "
        "без сірих плям під об'єктом, без ореолів, без тіньових площин. "
        "Isolated product on pure flat white #FFFFFF background, no floor, no shadows anywhere. "
        "Colors must be vivid and accurate — do NOT wash out, desaturate, or darken any colors. "
        "Crisp sharp edges on the product. No blur, no anti-aliasing haze outside the product."
    )

    _ASPECT_RATIOS = {
        "1:1": 1.0,
        "16:9": 16 / 9,
        "21:9": 21 / 9,
        "3:2": 3 / 2,
        "2:3": 2 / 3,
        "4:5": 4 / 5,
        "5:4": 5 / 4,
        "3:4": 3 / 4,
        "4:3": 4 / 3,
        "9:16": 9 / 16,
        "9:21": 9 / 21,
    }

    def __init__(self, config: dict):
        token = config.get("REPLICATE_API_TOKEN", "")
        if not token:
            raise ValueError("REPLICATE_API_TOKEN is not set in .env")

        os.environ["REPLICATE_API_TOKEN"] = token
        self.config = config
        timeout_sec = float(config.get("REPLICATE_TIMEOUT_SECONDS", "600"))
        self._replicate_client = replicate.Client(
            api_token=token,
            timeout=httpx.Timeout(timeout_sec, connect=60.0),
        )
        self.unique_mode = config.get("UNIQUE_MODE", "pillow")
        self.threed_model = config.get("THREED_MODEL", "flux-kontext-pro")

        self._legacy_model = None
        self._flux_redux_model = None
        self._flux_kontext_model = None
        self._flux_turnaround_model = None
        self._flux_turnaround_lora_model = None
        self._flux_dev_model = None
        self._qwen_multiangle_model = None

        self.strength = config["IMG2IMG_STRENGTH"]
        self.strength_3d = config.get("IMG2IMG_3D_STRENGTH", 0.55)
        self.flux_redux_guidance = config.get("FLUX_REDUX_GUIDANCE", 2.5)
        self.flux_dev_guidance = float(config.get("FLUX_DEV_GUIDANCE", "3.5"))
        self.flux_dev_steps = int(config.get("FLUX_DEV_STEPS", "35"))
        self.flux_dev_go_fast = str(config.get("FLUX_DEV_GO_FAST", "0")).strip().lower() in (
            "1",
            "true",
            "yes",
        )
        dims = resolve_output_dimensions(config)
        self.reference_size = (dims["REFERENCE_WIDTH"], dims["REFERENCE_HEIGHT"])
        self.turnaround_size = (dims["TURNAROUND_SHEET_WIDTH"], dims["TURNAROUND_SHEET_HEIGHT"])
        self.flux_dev_megapixels = dims["FLUX_DEV_MEGAPIXELS"]
        self.flux_kontext_guidance = config.get("FLUX_KONTEXT_GUIDANCE", 2.5)
        self.flux_kontext_steps = int(config.get("FLUX_KONTEXT_STEPS", 28))
        self.flux_turnaround_model = config.get(
            "FLUX_TURNAROUND_MODEL", "black-forest-labs/flux-kontext-dev"
        )
        self.turnaround_mode = str(config.get("TURNAROUND_MODE", "qwen")).lower()
        self.qwen_multiangle_model_name = config.get(
            "QWEN_MULTIANGLE_MODEL", "qwen/qwen-edit-multiangle"
        )
        angle_str = str(config.get("QWEN_ROTATE_DEGREES", "-90,-45,0,45,90"))
        self.qwen_rotate_degrees = tuple(
            max(-90, min(90, int(x.strip()))) for x in angle_str.split(",") if x.strip()
        )
        split_str = str(config.get("QWEN_MULTI_SPLIT", "2,3"))
        self.qwen_multi_split = tuple(
            int(x.strip()) for x in split_str.split(",") if x.strip()
        )
        chroma_str = str(config.get("QWEN_CHROMA_COLOR", "0,177,64"))
        chroma = [int(x.strip()) for x in chroma_str.split(",") if x.strip()]
        self.qwen_chroma_rgb = tuple((chroma + [0, 177, 64])[:3])
        self.gpu_worker_url = str(config.get("GPU_WORKER_URL", "")).strip()
        self.gpu_worker_token = str(config.get("GPU_WORKER_TOKEN", "")).strip()
        self.gpu_worker_timeout = float(config.get("GPU_WORKER_TIMEOUT", "180"))
        self.gpu_worker_views = int(config.get("GPU_WORKER_VIEWS", "5"))
        self.qwen_turnaround_prompt = config.get(
            "QWEN_TURNAROUND_PROMPT",
            "Keep the exact same stylized 3D product, materials and colors. "
            "Solid white background #FFFFFF. No floor, no shadows on background.",
        )
        self.turnaround_lora_url = config.get("TURNAROUND_LORA_URL", self.TURNAROUND_LORA_URL)
        self.turnaround_lora_strength = float(config.get("TURNAROUND_LORA_STRENGTH", "1.0"))
        self.request_delay = float(config.get("REPLICATE_REQUEST_DELAY", "11"))
        self.rate_limit_retries = int(config.get("REPLICATE_RATE_LIMIT_RETRIES", "8"))

        self.product_reference_prompt = config.get(
            "PRODUCT_REFERENCE_PROMPT", self.PRODUCT_REFERENCE_PROMPT
        )
        self.style_guided_prompt = config.get("STYLE_GUIDED_PROMPT", self.STYLE_GUIDED_PROMPT)
        self.turnaround_prompt = config.get("TURNAROUND_PROMPT", self.TURNAROUND_PROMPT)
        raw_view_prompts = config.get("KONTEXT_VIEW_PROMPTS")
        self.kontext_view_prompts: tuple[str, ...] = (
            tuple(raw_view_prompts) if raw_view_prompts else self.KONTEXT_VIEW_PROMPTS
        )
        self.kontext_3d_prompt = config.get("KONTEXT_3D_PROMPT", self.KONTEXT_3D_PROMPT)
        self.legacy_unique_prompt = config.get("LEGACY_UNIQUE_PROMPT", self.LEGACY_UNIQUE_PROMPT)
        self.legacy_pixar_prompt = config.get("LEGACY_PIXAR_PROMPT", self.LEGACY_PIXAR_PROMPT)
        self.negative_prompt = config.get("NEGATIVE_PROMPT", self.NEGATIVE_PROMPT)

    @property
    def legacy_model(self) -> str:
        if self._legacy_model is None:
            self._legacy_model = self._resolve_model(self.config["IMG2IMG_MODEL"])
        return self._legacy_model

    @property
    def flux_redux_model(self) -> str:
        if self._flux_redux_model is None:
            self._flux_redux_model = self._resolve_model(
                self.config.get("FLUX_REDUX_MODEL", "black-forest-labs/flux-redux-dev")
            )
        return self._flux_redux_model

    @property
    def flux_kontext_model(self) -> str:
        if self._flux_kontext_model is None:
            self._flux_kontext_model = self._resolve_model(
                self.config.get(
                    "FLUX_KONTEXT_MODEL", "black-forest-labs/flux-kontext-pro"
                )
            )
        return self._flux_kontext_model

    @property
    def flux_turnaround_kontext_model(self) -> str:
        if self._flux_turnaround_model is None:
            self._flux_turnaround_model = self._resolve_model(self.flux_turnaround_model)
        return self._flux_turnaround_model

    @property
    def flux_turnaround_lora_model(self) -> str:
        if self._flux_turnaround_lora_model is None:
            lora_model = self.config.get(
                "FLUX_TURNAROUND_LORA_MODEL", "black-forest-labs/flux-kontext-dev-lora"
            )
            self._flux_turnaround_lora_model = self._resolve_model(lora_model)
        return self._flux_turnaround_lora_model

    @property
    def flux_dev_model(self) -> str:
        if self._flux_dev_model is None:
            self._flux_dev_model = self._resolve_model(
                self.config.get("FLUX_DEV_MODEL", "black-forest-labs/flux-dev")
            )
        return self._flux_dev_model

    @property
    def qwen_multiangle_model(self) -> str:
        if self._qwen_multiangle_model is None:
            self._qwen_multiangle_model = self._resolve_model(self.qwen_multiangle_model_name)
        return self._qwen_multiangle_model

    @staticmethod
    def shuffle_catalog_prompt_indices(count: int) -> list[int]:
        """Return `count` unique random 1-based catalog indices without repeats."""
        total = len(AIService.PRODUCT_CATALOG_PROMPTS)
        pick = min(max(count, 0), total)
        return random.sample(range(1, total + 1), pick)

    def product_reference_prompt_for_catalog_slot(self, slot: int) -> str | None:
        """Return the catalog prompt for a 1-based catalog slot."""
        if 1 <= slot <= len(self.PRODUCT_CATALOG_PROMPTS):
            return self.PRODUCT_CATALOG_PROMPTS[slot - 1]
        return None

    def product_reference_prompt_for_index(self, index: int) -> str | None:
        """Return the catalog prompt for 1-based image index (sequential fallback)."""
        return self.product_reference_prompt_for_catalog_slot(index)

    def generate_product_reference(
        self,
        output_path: str,
        prompt: str | None = None,
        style_ref_path: str | None = None,
        *,
        catalog_mode: bool = False,
    ) -> str:
        """Catalog reference (9:16 portrait). With style_ref → flux-kontext; else flux-dev."""
        text_prompt = (prompt or self.product_reference_prompt)
        if catalog_mode:
            text_prompt += self._CATALOG_STYLE_SUFFIX
        text_prompt += self._WHITE_BG_SUFFIX
        if style_ref_path and os.path.isfile(style_ref_path):
            style_prefix = (
                self.CATALOG_STYLE_GUIDED_PROMPT if catalog_mode else self.style_guided_prompt
            )
            combined = f"{style_prefix}\n\n{text_prompt}"
            self._run_flux_kontext(
                style_ref_path,
                combined,
                output_path,
                aspect_ratio="9:16",
            )
        else:
            self._run_flux_dev(text_prompt, output_path, aspect_ratio="9:16")
        self._finalize_output(output_path, self.reference_size)
        return output_path

    def _finalize_output(self, path: str, size: tuple[int, int]) -> None:
        resize_and_save(path, size, self.config)

    def generate_turnaround(
        self, reference_path: str, output_path: str, prompt: str | None = None
    ) -> str:
        """Turnaround sheet (16:9). Default: Qwen multi-angle (~$0.03/view)."""
        if self.turnaround_mode == "trellis":
            self._run_trellis_turnaround(reference_path, output_path)
        elif self.turnaround_mode == "qwen":
            self._run_qwen_turnaround(reference_path, output_path, prompt=prompt)
        elif self.turnaround_mode in ("qwen-multi", "qwen_multi"):
            self._run_qwen_multi_turnaround(reference_path, output_path)
        elif self.turnaround_mode in ("gpu-worker", "gpu_worker"):
            if not self.gpu_worker_url:
                raise ValueError(
                    "TURNAROUND_MODE=gpu-worker requires GPU_WORKER_URL in .env"
                )
            self._run_gpu_worker_turnaround(reference_path, output_path)
        else:
            text_prompt = (prompt or self.turnaround_prompt) + self._WHITE_BG_SUFFIX
            if self.turnaround_mode == "lora":
                self._run_flux_kontext_lora(
                    reference_path, text_prompt, output_path, aspect_ratio="16:9"
                )
            elif self.turnaround_mode == "kontext":
                self._run_kontext_5views_turnaround(reference_path, output_path)
            elif self.turnaround_mode in ("local", "zero123", "syncdreamer"):
                raise ValueError(
                    f"TURNAROUND_MODE={self.turnaround_mode!r} was removed. "
                    "Use TURNAROUND_MODE=qwen in .env (default), then restart py app.py."
                )
            else:
                raise ValueError(
                    f"Unknown TURNAROUND_MODE: {self.turnaround_mode!r}. "
                    "Use qwen, kontext, or lora."
                )
        self._finalize_output(output_path, self.turnaround_size)
        return output_path

    # Per-view camera config: (rotate_degrees, vertical_tilt, move_forward)
    # rotate_degrees: -90=left … 0=front … +90=right
    # vertical_tilt: Replicate int in {-1,0,1} (-1=top-down, 0=eye-level, +1=low-angle)
    # move_forward: Replicate int 0–10 (0=normal, higher=closer)
    _QWEN_VIEW_PARAMS = (
        (-90, -1, 0),   # left side, slightly elevated
        (-45, -1, 0),   # front-left, slightly elevated
        (  0,  0, 0),   # front, eye-level
        ( 45,  0, 1),   # front-right, slightly low, slightly closer
        ( 90,  1, 2),   # right side, low angle, closer
    )

    _QWEN_VIEW_LABELS = (
        "VIEW 1 of 5 — LEFT SIDE: rotate the product so the camera sees only the left profile. Camera slightly above eye-level. Single product, white background.",
        "VIEW 2 of 5 — FRONT-LEFT: camera 45 degrees to the left and slightly above. Show the front face and left side together. Single product, white background.",
        "VIEW 3 of 5 — FRONT: camera directly in front, eye-level. Show the front face. Single product, white background.",
        "VIEW 4 of 5 — FRONT-RIGHT: camera 45 degrees to the right and slightly below eye-level. Show the front face and right side together. Single product, white background.",
        "VIEW 5 of 5 — RIGHT SIDE: rotate the product so the camera sees only the right profile. Camera slightly below eye-level, slightly closer. Single product, white background.",
    )

    def _run_qwen_turnaround(
        self, reference_path: str, output_path: str, prompt: str | None = None
    ) -> None:
        """Five camera rotations via Qwen Edit Multiangle, stitched to 16:9.

        Views run concurrently via a thread pool; the module-level rate limiter
        serialises HTTP submissions so multiple turnaround threads don't collide.
        Each view gets a per-angle label in the prompt and a unique seed to prevent
        the model from generating duplicate frames.
        """
        from backend.services.image_service import ImageService

        base_prompt = prompt or self.qwen_turnaround_prompt
        work_dir = os.path.dirname(output_path) or "."
        tmp_paths: list[str] = []
        opened: list[Image.Image] = []

        def _generate_view(i: int) -> tuple[int, str]:
            vpath = os.path.join(
                work_dir,
                f".qwen_view_{i}_{os.getpid()}_{threading.get_ident()}.png",
            )
            rotate, tilt, forward = self._QWEN_VIEW_PARAMS[i]
            label = self._QWEN_VIEW_LABELS[i] if i < len(self._QWEN_VIEW_LABELS) else ""
            view_prompt = f"{base_prompt}\n\n{label}" if label else base_prompt
            with open(reference_path, "rb") as fh:
                out = self._run_replicate(
                    self.qwen_multiangle_model,
                    {
                        "image": fh,
                        "rotate_degrees": int(rotate),
                        "vertical_tilt": int(tilt),
                        "move_forward": int(forward),
                        "use_wide_angle": False,
                        "go_fast": True,
                        "aspect_ratio": "1:1",
                        "output_format": "png",
                        "prompt": view_prompt,
                    },
                )
            self._save_output(out, vpath)
            return i, vpath

        try:
            results: dict[int, str] = {}
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = {
                    pool.submit(_generate_view, i): i
                    for i in range(len(self._QWEN_VIEW_PARAMS))
                }
                for fut in as_completed(futures):
                    idx, vpath = fut.result()
                    results[idx] = vpath
                    tmp_paths.append(vpath)

            for i in sorted(results):
                opened.append(Image.open(results[i]))

            ImageService(self.config).compose_turnaround_sheet(opened, output_path)
        finally:
            for img in opened:
                img.close()
            for p in tmp_paths:
                if os.path.isfile(p):
                    os.remove(p)

    def _run_trellis_turnaround(self, reference_path: str, output_path: str) -> None:
        """True 360° turnaround via firtoz/trellis on Replicate.

        TRELLIS reconstructs a 3D Gaussian Splat from the product photo and
        renders a 360° color video.  We extract 5 evenly-spaced frames from
        that video (0%, 20%, 40%, 60%, 80% of duration) and stitch them into
        the 16:9 turnaround sheet.
        """
        import urllib.request
        import av as pyav
        from backend.services.image_service import ImageService

        with open(reference_path, "rb") as fh:
            result = self._run_replicate(
                self._resolve_model("firtoz/trellis"),
                {
                    "images": [fh],
                    "generate_color": True,
                    "generate_model": False,
                    "generate_normal": False,
                    "randomize_seed": True,
                    "ss_sampling_steps": 12,
                    "slat_sampling_steps": 12,
                },
            )

        if isinstance(result, dict):
            color_video_url = result.get("color_video")
        else:
            color_video_url = getattr(result, "color_video", None)
        if not color_video_url:
            raise RuntimeError(f"TRELLIS returned no color_video. result={result!r}")

        work_dir = os.path.dirname(output_path) or "."
        video_path = os.path.join(work_dir, f".trellis_{os.getpid()}.mp4")
        try:
            urllib.request.urlretrieve(color_video_url, video_path)

            container = pyav.open(video_path)
            stream = container.streams.video[0]
            frames_list = list(container.decode(stream))
            container.close()

            total_frames = len(frames_list)
            if total_frames == 0:
                raise RuntimeError("TRELLIS color_video has no frames")

            n_views = 5
            indices = [int(i * total_frames / n_views) for i in range(n_views)]

            views: list[Image.Image] = []
            for idx in indices:
                frame = frames_list[min(idx, total_frames - 1)]
                views.append(frame.to_image())
            ImageService(self.config).compose_turnaround_sheet(views, output_path)
        finally:
            if os.path.isfile(video_path):
                os.remove(video_path)

    def _run_kontext_5views_turnaround(self, reference_path: str, output_path: str) -> None:
        """Five unique views via 5 individual flux-kontext calls, then stitched to 16:9.

        Each call receives the reference image and a dedicated single-angle prompt so the
        model actually rotates the object instead of repeating the front view.  Calls run
        concurrently through a thread pool so inference time overlaps; the module-level
        rate limiter serialises the HTTP submissions to stay within Replicate's rate limit.
        """
        from backend.services.image_service import ImageService

        work_dir = os.path.dirname(output_path) or "."
        tmp_paths: list[str] = []
        opened: list[Image.Image] = []

        def _generate_one(i: int, prompt: str) -> tuple[int, str]:
            vpath = os.path.join(
                work_dir,
                f".kv_{i}_{os.getpid()}_{threading.get_ident()}.png",
            )
            with open(reference_path, "rb") as fh:
                out = self._run_replicate(
                    self.flux_kontext_model,
                    {
                        "prompt": prompt,
                        "input_image": fh,
                        "aspect_ratio": "1:1",
                        "guidance": self.flux_kontext_guidance,
                        "num_inference_steps": self.flux_kontext_steps,
                        "output_format": "png",
                    },
                )
            self._save_output(out, vpath)
            return i, vpath

        try:
            prompts = list(self.kontext_view_prompts[:5])
            while len(prompts) < 5:
                prompts.append(prompts[-1])

            # Thread pool: inference runs in parallel; _replicate_rate_lock inside
            # _run_replicate ensures sequential HTTP submissions to honour rate limits.
            results: dict[int, str] = {}
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = {pool.submit(_generate_one, i, p): i for i, p in enumerate(prompts)}
                for fut in as_completed(futures):
                    idx, vpath = fut.result()
                    results[idx] = vpath
                    tmp_paths.append(vpath)

            for i in sorted(results):
                opened.append(Image.open(results[i]))

            ImageService(self.config).compose_turnaround_sheet(opened, output_path)
        finally:
            for img in opened:
                img.close()
            for p in tmp_paths:
                if os.path.isfile(p):
                    os.remove(p)

    def _chroma_desc(self) -> tuple[str, str]:
        """Human color NAME + hex for the chroma key — Qwen honors names, not rgb()."""
        r, g, b = self.qwen_chroma_rgb
        hex_code = f"#{r:02X}{g:02X}{b:02X}"
        if g >= r and g >= b:
            name = "GREEN"
        elif r >= g and r >= b:
            name = "MAGENTA"
        else:
            name = "BLUE"
        return name, hex_code

    def _multiview_prompt(self, count: int) -> str:
        """Prompt for one image containing `count` copies of the product on chroma green."""
        name, hex_code = self._chroma_desc()
        return (
            f"Show the SAME product as {count} separate copies side by side in one "
            "horizontal row, evenly spaced with a clear empty gap between each copy, "
            "every copy fully visible and never cropped, each at a slightly different "
            "three-quarter / side viewing angle. Identical object, identical scale, "
            "lighting and materials in every copy.\n\n"
            f"Background: solid uniform chroma-key {name} ({hex_code}) filling the whole "
            "frame, flat studio backdrop. No text, no labels, no dimension lines, no "
            "measurements."
        )

    def _run_qwen_multi_turnaround(self, reference_path: str, output_path: str) -> None:
        """Cheaper turnaround: few Qwen calls, each rendering several views on a chroma
        backdrop, then keyed to white and stitched. E.g. split 2,3 -> 5 views in 2 calls."""
        from backend.services.image_service import ImageService

        svc = ImageService(self.config)
        work_dir = os.path.dirname(output_path) or "."
        tmp_paths: list[str] = []
        views: list[Image.Image] = []

        try:
            for i, count in enumerate(self.qwen_multi_split):
                tmp = os.path.join(work_dir, f".qmv_{i}_{os.getpid()}.png")
                with open(reference_path, "rb") as image_file:
                    output = self._run_replicate(
                        self.qwen_multiangle_model,
                        {
                            "image": image_file,
                            "rotate_degrees": 0,
                            "vertical_tilt": 0,
                            "move_forward": 0,
                            "use_wide_angle": True,
                            "go_fast": True,
                            "aspect_ratio": "16:9",
                            "output_format": "png",
                            "prompt": self._multiview_prompt(count),
                        },
                    )
                self._save_output(output, tmp)
                tmp_paths.append(tmp)

                keyed = svc.chroma_key_to_white(Image.open(tmp), self.qwen_chroma_rgb)
                subjects = svc.extract_subjects(keyed, count)
                if len(subjects) < count:
                    # Backdrop wasn't the expected chroma color (Qwen ignored it) —
                    # fall back to an even strip split so we still get `count` views.
                    subjects = svc.split_image_strip(keyed, count)
                views.extend(subjects)

                if i + 1 < len(self.qwen_multi_split):
                    self.wait_between_requests()

            if not views:
                raise RuntimeError("qwen-multi produced no views")
            svc.compose_turnaround_sheet(views, output_path)
        finally:
            for img in views:
                img.close()
            for path in tmp_paths:
                if os.path.isfile(path):
                    os.remove(path)

    def _run_gpu_worker_turnaround(self, reference_path: str, output_path: str) -> None:
        """Turnaround via a rented-GPU worker (Zero123++/TRELLIS FastAPI service).

        Sends the reference to GPU_WORKER_URL, receives N novel views (base64 PNGs on
        white), and stitches them into the standard 16:9 sheet. Costs only GPU rental
        time (~$0.14/h) instead of per-view API fees.
        """
        import base64
        import io

        from backend.services.image_service import ImageService

        url = self.gpu_worker_url.rstrip("/") + "/generate"
        headers = {}
        if self.gpu_worker_token:
            headers["Authorization"] = f"Bearer {self.gpu_worker_token}"

        with open(reference_path, "rb") as image_file:
            ref_ext = os.path.splitext(reference_path)[1].lower() or ".jpg"
            ref_mime = "image/jpeg" if ref_ext in (".jpg", ".jpeg") else "image/png"
            response = requests.post(
                url,
                headers=headers,
                files={"image": (f"reference{ref_ext}", image_file, ref_mime)},
                data={"views": str(self.gpu_worker_views)},
                timeout=self.gpu_worker_timeout,
            )
        response.raise_for_status()

        payload = response.json()
        encoded_views = payload.get("views") or []
        if not encoded_views:
            raise RuntimeError("GPU worker returned no views")

        images: list[Image.Image] = []
        try:
            for encoded in encoded_views:
                data = base64.b64decode(encoded)
                images.append(Image.open(io.BytesIO(data)).convert("RGB"))
            ImageService(self.config).compose_turnaround_sheet(images, output_path)
        finally:
            for img in images:
                img.close()

    def _resolve_model(self, model: str) -> str:
        if ":" in model:
            return model

        meta = self._replicate_client.models.get(model)
        version = meta.latest_version
        if not version:
            raise ValueError(f"No published version found for Replicate model '{model}'")

        return f"{meta.owner}/{meta.name}:{version.id}"

    def uniquify(self, input_path: str, output_dir: str) -> str:
        """AI uniquification layer — only when UNIQUE_MODE requests it."""
        stem = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, f"uniquified_{stem}.png")

        if self.unique_mode == "flux-redux":
            self._run_flux_redux(input_path, output_path)
        elif self.unique_mode == "sd-img2img":
            self._run_legacy_img2img(
                input_path, self.legacy_unique_prompt, self.strength, output_path
            )
        else:
            raise ValueError(f"uniquify() called with non-AI mode: {self.unique_mode}")

        return output_path

    def transform_3d(self, input_path: str, output_path: str) -> str:
        if self.threed_model.startswith("flux-kontext"):
            self._run_flux_kontext(input_path, self.kontext_3d_prompt, output_path)
        elif self.threed_model == "sd-img2img":
            self._run_legacy_img2img(
                input_path, self.legacy_pixar_prompt, self.strength_3d, output_path
            )
        else:
            raise ValueError(f"Unknown THREED_MODEL: {self.threed_model}")

        return output_path

    def repaint_to_break_fingerprint(self, input_path: str, output_path: str, strength: float | None = None) -> str:
        """Pass FLUX output through SD 1.5 img2img.
        Keeps 3D structure from FLUX, replaces diffusion fingerprint with SD 1.5."""
        s = strength if strength is not None else float(self.config.get("REPAINT_STRENGTH", "0.35"))
        try:
            self._run_legacy_img2img(
                input_path,
                self.legacy_pixar_prompt,
                s,
                output_path,
            )
        except OSError as exc:
            raise RuntimeError(f"Cannot reach Replicate API: {exc}") from exc
        return output_path

    def wait_between_requests(self):
        """Pace requests for Replicate low-credit tier (6/min, burst 1)."""
        if self.request_delay > 0:
            time.sleep(self.request_delay)

    def _run_replicate(self, model: str, input_dict: dict):
        global _replicate_last_call
        # Serialise API submissions across all threads to respect rate limits.
        if self.request_delay > 0:
            with _replicate_rate_lock:
                now = time.monotonic()
                gap = self.request_delay - (now - _replicate_last_call)
                if gap > 0:
                    time.sleep(gap)
                _replicate_last_call = time.monotonic()

        last_exc = None
        for attempt in range(self.rate_limit_retries + 1):
            try:
                return self._replicate_client.run(model, input=input_dict)
            except OSError as exc:
                raise RuntimeError(f"Cannot reach Replicate API: {exc}") from exc
            except Exception as exc:
                last_exc = exc
                _raise_if_balance_error(exc)
                if _is_timeout_error(exc) and attempt < self.rate_limit_retries:
                    wait = max(self.request_delay, 15.0)
                    logger.warning(
                        "Replicate timeout, retry in %.0fs (%s/%s)",
                        wait,
                        attempt + 1,
                        self.rate_limit_retries,
                    )
                    time.sleep(wait)
                    continue
                if _is_rate_limit_error(exc) and attempt < self.rate_limit_retries:
                    wait = _retry_wait_seconds(exc, self.request_delay)
                    logger.warning(
                        "Replicate rate limit, retry in %.0fs (%s/%s)",
                        wait,
                        attempt + 1,
                        self.rate_limit_retries,
                    )
                    time.sleep(wait)
                    continue
                if _is_rate_limit_error(exc):
                    raise ReplicateThrottleError(
                        "Replicate rate limit (429). Stopped at the last successful image. "
                        "With balance under $5 the limit is ~6 requests/min — increase delay "
                        "or top up Replicate credit."
                    ) from exc
                if _is_timeout_error(exc):
                    raise RuntimeError(
                        "Replicate request timed out. Try again or increase REPLICATE_TIMEOUT_SECONDS."
                    ) from exc
                raise
        if last_exc:
            raise last_exc

    def _run_flux_dev(self, prompt: str, output_path: str, aspect_ratio: str = "1:1"):
        output = self._run_replicate(
            self.flux_dev_model,
            {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "guidance": self.flux_dev_guidance,
                "num_inference_steps": self.flux_dev_steps,
                "output_format": "png",
                "go_fast": self.flux_dev_go_fast,
                "megapixels": self.flux_dev_megapixels,
            },
        )
        self._save_output(output, output_path)

    def _run_flux_redux(self, input_path: str, output_path: str):
        try:
            with open(input_path, "rb") as image_file:
                output = self._replicate_client.run(
                    self.flux_redux_model,
                    input={
                        "redux_image": image_file,
                        "aspect_ratio": self._closest_aspect_ratio(input_path),
                        "guidance": self.flux_redux_guidance,
                        "num_inference_steps": 28,
                        "output_format": "png",
                    },
                )
        except OSError as exc:
            raise RuntimeError(f"Cannot reach Replicate API: {exc}") from exc
        self._save_output(output, output_path)

    def _run_flux_kontext(
        self, input_path: str, prompt: str, output_path: str, aspect_ratio: str = "match_input_image"
    ):
        with open(input_path, "rb") as image_file:
            output = self._run_replicate(
                self.flux_kontext_model,
                {
                    "prompt": prompt,
                    "input_image": image_file,
                    "aspect_ratio": aspect_ratio,
                    "guidance": self.flux_kontext_guidance,
                    "num_inference_steps": self.flux_kontext_steps,
                    "output_format": "png",
                },
            )
        self._save_output(output, output_path)

    def _run_flux_kontext_turnaround(self, input_path: str, prompt: str, output_path: str):
        with open(input_path, "rb") as image_file:
            output = self._run_replicate(
                self.flux_turnaround_kontext_model,
                {
                    "prompt": prompt,
                    "input_image": image_file,
                    "aspect_ratio": "16:9",
                    "guidance": self.flux_kontext_guidance,
                    "num_inference_steps": self.flux_kontext_steps,
                    "output_format": "png",
                },
            )
        self._save_output(output, output_path)

    def _run_flux_kontext_lora(
        self, input_path: str, prompt: str, output_path: str, aspect_ratio: str = "16:9"
    ):
        with open(input_path, "rb") as image_file:
            output = self._run_replicate(
                self.flux_turnaround_lora_model,
                {
                    "prompt": prompt,
                    "input_image": image_file,
                    "lora_weights": self.turnaround_lora_url,
                    "lora_strength": self.turnaround_lora_strength,
                    "aspect_ratio": aspect_ratio,
                    "guidance": self.flux_kontext_guidance,
                    "num_inference_steps": self.flux_kontext_steps,
                    "output_format": "png",
                },
            )
        self._save_output(output, output_path)

    def _run_legacy_img2img(
        self, input_path: str, prompt: str, prompt_strength: float, output_path: str
    ):
        try:
            with open(input_path, "rb") as image_file:
                output = self._replicate_client.run(
                    self.legacy_model,
                    input={
                        "image": image_file,
                        "prompt": prompt,
                        "negative_prompt": self.negative_prompt,
                        "prompt_strength": prompt_strength,
                        "num_inference_steps": 30,
                        "guidance_scale": 7.5,
                    },
                )
        except OSError as exc:
            raise RuntimeError(f"Cannot reach Replicate API: {exc}") from exc
        self._save_output(output, output_path)

    def _closest_aspect_ratio(self, image_path: str) -> str:
        with Image.open(image_path) as img:
            ratio = img.width / img.height

        return min(self._ASPECT_RATIOS, key=lambda k: abs(self._ASPECT_RATIOS[k] - ratio))

    def _save_output(self, replicate_output, save_path: str):
        if replicate_output is None:
            raise RuntimeError("Replicate returned no output")

        if isinstance(replicate_output, list):
            if not replicate_output:
                raise RuntimeError("Replicate returned an empty output list")
            replicate_output = replicate_output[0]

        ext = os.path.splitext(save_path)[1].lower()

        if hasattr(replicate_output, "read"):
            data = replicate_output.read()
            if ext in (".jpg", ".jpeg"):
                save_bytes_as_output(data, save_path, self.config)
            else:
                with open(save_path, "wb") as f:
                    f.write(data)
            return

        if hasattr(replicate_output, "url"):
            url = replicate_output.url
            if url:
                r = requests.get(url, timeout=120)
                r.raise_for_status()
                if ext in (".jpg", ".jpeg"):
                    save_bytes_as_output(r.content, save_path, self.config)
                else:
                    with open(save_path, "wb") as f:
                        f.write(r.content)
                return

        if isinstance(replicate_output, str) and replicate_output.startswith("http"):
            r = requests.get(replicate_output, timeout=120)
            r.raise_for_status()
            if ext in (".jpg", ".jpeg"):
                save_bytes_as_output(r.content, save_path, self.config)
            else:
                with open(save_path, "wb") as f:
                    f.write(r.content)
            return

        raise RuntimeError(f"Unexpected Replicate output type: {type(replicate_output)!r}")
