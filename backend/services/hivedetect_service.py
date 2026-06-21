import requests
import base64


class HivedetectService:
    """
    Checks image against Hivedetect AI detector.
    Returns % probability that image is AI-generated.
    Lower score = more human-like = better for our use case.
    """

    API_URL = "https://hivedetect.ai/api/check"

    def __init__(self, config: dict):
        self.api_key = config.get("HIVEDETECT_API_KEY", "")

    def check(self, image_path: str) -> float:
        """
        Returns AI detection score 0.0–100.0.
        0% = looks human-made, 100% = clearly AI.
        Target: < 10%
        """
        if not self.api_key:
            # No key configured — return mock score for local dev
            return 0.0

        try:
            with open(image_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()

            response = requests.post(
                self.API_URL,
                json={"image": encoded},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            # Adjust key based on actual Hivedetect API response shape
            return float(data.get("ai_score", data.get("score", 0.0)))

        except Exception:
            return -1.0   # -1 = check failed, show warning in UI
