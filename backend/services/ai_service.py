import os

import replicate
import requests
from PIL import Image


class AIService:
    """
    Replicate API wrappers:
      - flux-redux-dev — subtle image variations (uniquify)
      - flux-kontext-dev — instruction-based edits (3D Pixar transform)
    """

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

    TURNAROUND_PROMPT = (
        "Character design turnaround reference sheet. Using the provided character as reference, "
        "create a professional turnaround with exactly 5 views arranged in a single horizontal row "
        "on a plain white background. Left to right order: "
        "(1) three-quarter left view — front-left diagonal angle, "
        "(2) left side profile — 90 degrees left, fully sideways, "
        "(3) back view — character facing directly away, full rear view, "
        "(4) right side profile — 90 degrees right, fully sideways, "
        "(5) three-quarter right view — front-right diagonal angle. "
        "All 5 views show the complete character from head to toe in a neutral A-pose with arms "
        "slightly apart at sides. Maintain identical proportions, exact same character design, "
        "colors, hair, clothing, and all details across all 5 views. "
        "Each view is independently drawn — absolutely no left-right mirroring. "
        "Clean flat illustrator style with clear outlines, even lighting, white background, "
        "all 5 views equally sized and evenly spaced. Wide panoramic 16:9 format. "
        "No text, no labels, no annotations, no drop shadows on background."
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
        "watermark, text, extra limbs, disfigured"
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
        self.unique_mode = config.get("UNIQUE_MODE", "pillow")
        self.threed_model = config.get("THREED_MODEL", "flux-kontext-pro")

        self._legacy_model = None
        self._flux_redux_model = None
        self._flux_kontext_model = None

        self.strength = config["IMG2IMG_STRENGTH"]
        self.strength_3d = config.get("IMG2IMG_3D_STRENGTH", 0.55)
        self.flux_redux_guidance = config.get("FLUX_REDUX_GUIDANCE", 2.5)
        self.flux_kontext_guidance = config.get("FLUX_KONTEXT_GUIDANCE", 2.5)
        self.flux_kontext_steps = int(config.get("FLUX_KONTEXT_STEPS", 28))

        self.kontext_3d_prompt = config.get("KONTEXT_3D_PROMPT", self.KONTEXT_3D_PROMPT)
        self.turnaround_prompt = config.get("TURNAROUND_PROMPT", self.TURNAROUND_PROMPT)
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

    def _resolve_model(self, model: str) -> str:
        if ":" in model:
            return model

        meta = replicate.models.get(model)
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

    def generate_turnaround(self, input_path: str, output_path: str) -> str:
        """Generate 5-view character turnaround reference sheet (16:9 wide image)."""
        self._run_flux_kontext(
            input_path, self.turnaround_prompt, output_path, aspect_ratio="16:9"
        )
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

    def _run_flux_redux(self, input_path: str, output_path: str):
        try:
            with open(input_path, "rb") as image_file:
                output = replicate.run(
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
        try:
            with open(input_path, "rb") as image_file:
                output = replicate.run(
                    self.flux_kontext_model,
                    input={
                        "prompt": prompt,
                        "input_image": image_file,
                        "aspect_ratio": aspect_ratio,
                        "guidance": self.flux_kontext_guidance,
                        "num_inference_steps": self.flux_kontext_steps,
                        "output_format": "png",
                    },
                )
        except OSError as exc:
            raise RuntimeError(f"Cannot reach Replicate API: {exc}") from exc
        self._save_output(output, output_path)

    def _run_legacy_img2img(
        self, input_path: str, prompt: str, prompt_strength: float, output_path: str
    ):
        try:
            with open(input_path, "rb") as image_file:
                output = replicate.run(
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

        if hasattr(replicate_output, "read"):
            with open(save_path, "wb") as f:
                f.write(replicate_output.read())
            return

        if hasattr(replicate_output, "url"):
            url = replicate_output.url
            if url:
                r = requests.get(url, timeout=120)
                r.raise_for_status()
                with open(save_path, "wb") as f:
                    f.write(r.content)
                return

        if isinstance(replicate_output, str) and replicate_output.startswith("http"):
            r = requests.get(replicate_output, timeout=120)
            r.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(r.content)
            return

        raise RuntimeError(f"Unexpected Replicate output type: {type(replicate_output)!r}")
