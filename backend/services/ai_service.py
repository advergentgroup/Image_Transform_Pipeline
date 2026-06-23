import replicate
import requests
import os


class AIService:
    """
    Wraps Replicate API for:
      - img2img uniquification (subtle, prompt_strength ~0.25)
      - img2img 3D Pixar style transform
    """

    UNIQUE_PROMPT = (
        "same character, same pose, same colors, cartoon illustration, "
        "high quality, clean lines, detailed"
    )

    PIXAR_PROMPT = (
        "3D Pixar style, same character, same outfit, same pose, "
        "volumetric lighting, subsurface scattering, cinematic render, "
        "high detail, soft shadows, Disney Pixar animation"
    )

    NEGATIVE_PROMPT = "blurry, low quality, distorted, deformed, watermark, text"

    def __init__(self, config: dict):
        token = config.get("REPLICATE_API_TOKEN", "")
        if not token:
            raise ValueError("REPLICATE_API_TOKEN is not set in .env")

        os.environ["REPLICATE_API_TOKEN"] = token
        self.model = self._resolve_model(config["IMG2IMG_MODEL"])
        self.strength = config["IMG2IMG_STRENGTH"]
        self.strength_3d = config.get("IMG2IMG_3D_STRENGTH", 0.55)

    def _resolve_model(self, model: str) -> str:
        """Replicate requires owner/name:version — slug alone returns 404."""
        if ":" in model:
            return model

        meta = replicate.models.get(model)
        version = meta.latest_version
        if not version:
            raise ValueError(f"No published version found for Replicate model '{model}'")

        return f"{meta.owner}/{meta.name}:{version.id}"

    def img2img_unique(self, input_path: str, output_dir: str) -> str:
        output_path = os.path.join(output_dir, "uniquified_" + os.path.basename(input_path))
        self._run_img2img(input_path, self.UNIQUE_PROMPT, self.strength, output_path)
        return output_path

    def img2img_3d(self, input_path: str, output_path: str) -> str:
        self._run_img2img(input_path, self.PIXAR_PROMPT, self.strength_3d, output_path)
        return output_path

    def _run_img2img(self, input_path: str, prompt: str, prompt_strength: float, output_path: str):
        with open(input_path, "rb") as image_file:
            output = replicate.run(
                self.model,
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
