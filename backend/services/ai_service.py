import replicate
import requests
import base64
import os


class AIService:
    """
    Wraps Replicate API for:
      - img2img uniquification (subtle, strength ~0.2)
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

    def __init__(self, config: dict):
        os.environ["REPLICATE_API_TOKEN"] = config["REPLICATE_API_TOKEN"]
        self.model = config["IMG2IMG_MODEL"]
        self.strength = config["IMG2IMG_STRENGTH"]
        self.output_folder = config["OUTPUT_FOLDER"]

    def _encode_image(self, path: str) -> str:
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()

    def img2img_unique(self, input_path: str, output_dir: str) -> str:
        """Subtle uniquification — keeps original style, just makes it unique."""
        output_path = os.path.join(output_dir, "uniquified_" + os.path.basename(input_path))

        output = replicate.run(
            self.model,
            input={
                "image": self._encode_image(input_path),
                "prompt": self.UNIQUE_PROMPT,
                "strength": self.strength,       # 0.2–0.3 = stays very close to original
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
            }
        )

        # Replicate returns URL or file-like — save to disk
        self._save_output(output, output_path)
        return output_path

    def img2img_3d(self, input_path: str, output_path: str) -> str:
        """Transform to 3D Pixar style."""
        output = replicate.run(
            self.model,
            input={
                "image": self._encode_image(input_path),
                "prompt": self.PIXAR_PROMPT,
                "strength": 0.55,               # higher = more 3D transformation
                "num_inference_steps": 40,
                "guidance_scale": 9.0,
            }
        )

        self._save_output(output, output_path)
        return output_path

    def _save_output(self, replicate_output, save_path: str):
        """Save Replicate output (URL or FileOutput) to disk."""
        if hasattr(replicate_output, "read"):
            with open(save_path, "wb") as f:
                f.write(replicate_output.read())
        elif isinstance(replicate_output, str) and replicate_output.startswith("http"):
            r = requests.get(replicate_output, timeout=30)
            with open(save_path, "wb") as f:
                f.write(r.content)
        elif isinstance(replicate_output, list) and replicate_output:
            self._save_output(replicate_output[0], save_path)
