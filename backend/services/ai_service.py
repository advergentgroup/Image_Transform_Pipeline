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
        "Render this exact illustration as a 3D Pixar Disney CGI still. "
        "Keep the identical character, face, pose, body proportions, outfit, and colors from the input. "
        "Do not redesign or replace anything — only add 3D volume, soft studio lighting, "
        "subsurface scattering, and smooth CGI materials. Same composition and background."
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
        self.threed_model = config.get("THREED_MODEL", "flux-kontext-dev")

        self._legacy_model = None
        self._flux_redux_model = None
        self._flux_kontext_model = None

        self.strength = config["IMG2IMG_STRENGTH"]
        self.strength_3d = config.get("IMG2IMG_3D_STRENGTH", 0.55)
        self.flux_redux_guidance = config.get("FLUX_REDUX_GUIDANCE", 2.5)
        self.flux_kontext_guidance = config.get("FLUX_KONTEXT_GUIDANCE", 2.2)

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
                self.config.get("FLUX_KONTEXT_MODEL", "black-forest-labs/flux-kontext-dev")
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
                input_path, self.LEGACY_UNIQUE_PROMPT, self.strength, output_path
            )
        else:
            raise ValueError(f"uniquify() called with non-AI mode: {self.unique_mode}")

        return output_path

    def transform_3d(self, input_path: str, output_path: str) -> str:
        if self.threed_model == "flux-kontext-dev":
            self._run_flux_kontext(input_path, self.KONTEXT_3D_PROMPT, output_path)
        elif self.threed_model == "sd-img2img":
            self._run_legacy_img2img(
                input_path, self.LEGACY_PIXAR_PROMPT, self.strength_3d, output_path
            )
        else:
            raise ValueError(f"Unknown THREED_MODEL: {self.threed_model}")

        return output_path

    def _run_flux_redux(self, input_path: str, output_path: str):
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
        self._save_output(output, output_path)

    def _run_flux_kontext(self, input_path: str, prompt: str, output_path: str):
        with open(input_path, "rb") as image_file:
            output = replicate.run(
                self.flux_kontext_model,
                input={
                    "prompt": prompt,
                    "input_image": image_file,
                    "aspect_ratio": "match_input_image",
                    "guidance": self.flux_kontext_guidance,
                    "num_inference_steps": 30,
                    "output_format": "png",
                },
            )
        self._save_output(output, output_path)

    def _run_legacy_img2img(
        self, input_path: str, prompt: str, prompt_strength: float, output_path: str
    ):
        with open(input_path, "rb") as image_file:
            output = replicate.run(
                self.legacy_model,
                input={
                    "image": image_file,
                    "prompt": prompt,
                    "negative_prompt": self.NEGATIVE_PROMPT,
                    "prompt_strength": prompt_strength,
                    "num_inference_steps": 30,
                    "guidance_scale": 7.5,
                },
            )
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
