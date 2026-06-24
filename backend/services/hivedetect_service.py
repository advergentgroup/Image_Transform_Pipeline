import base64
import logging
import mimetypes
import os

import requests

logger = logging.getLogger(__name__)

_PLACEHOLDER_KEYS = frozenset({"", "your_key_here", "change-me", "changeme"})
_DEFAULT_URL = (
    "https://api.thehive.ai/api/v3/hive/ai-generated-and-deepfake-content-detection"
)


class HivedetectService:
    """
    Hive AI-Generated and Deepfake Content Detection (V3 Playground).
    Docs: https://docs.thehive.ai/docs/ai-generated-and-deepfake-content-detection-playground

    Returns % probability that image is AI-generated (0–100).
    Lower score = more human-like = better for our use case.
    """

    def __init__(self, config: dict):
        self.api_key = (config.get("HIVEDETECT_API_KEY") or "").strip()
        self.api_url = (config.get("HIVEDETECT_URL") or _DEFAULT_URL).strip()
        self.use_mock = str(config.get("HIVEDETECT_USE_MOCK", "0")).lower() in (
            "1",
            "true",
            "yes",
        )

    def _key_valid(self) -> bool:
        if self.use_mock:
            return False
        return bool(self.api_key) and self.api_key.lower() not in _PLACEHOLDER_KEYS

    def check(self, image_path: str) -> float:
        """
        Returns AI detection score 0.0–100.0.
        0% = looks human-made, 100% = clearly AI.
        -1.0 = check failed.
        """
        if not self._key_valid():
            return 0.0

        if not os.path.isfile(image_path):
            logger.warning("Hive check: file not found: %s", image_path)
            return -1.0

        mime, _ = mimetypes.guess_type(image_path)
        mime = mime or "image/png"
        filename = os.path.basename(image_path)

        score = self._check_json(image_path, mime)
        if score is not None:
            return score

        score = self._check_multipart(image_path, filename, mime)
        if score is not None:
            return score

        return -1.0

    def _check_json(self, image_path: str, mime: str) -> float | None:
        with open(image_path, "rb") as f:
            raw = f.read()

        if len(raw) > 20 * 1024 * 1024:
            logger.info("Hive: %s exceeds 20 MB base64 limit, trying multipart", image_path)
            return None

        data_uri = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
        payload = {
            "media_metadata": True,
            "input": [{"media_base64": data_uri}],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60,
            )
        except requests.RequestException as exc:
            logger.warning("Hive JSON request failed for %s: %s", image_path, exc)
            return None

        return self._handle_response(response, "json", image_path)

    def _check_multipart(self, image_path: str, filename: str, mime: str) -> float | None:
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            with open(image_path, "rb") as f:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    files={"media": (filename, f, mime)},
                    timeout=60,
                )
        except requests.RequestException as exc:
            logger.warning("Hive multipart request failed for %s: %s", image_path, exc)
            return None

        return self._handle_response(response, "multipart", image_path)

    def _handle_response(
        self,
        response: requests.Response,
        mode: str,
        image_path: str,
    ) -> float | None:
        if response.status_code in (401, 403):
            logger.warning(
                "Hive %s auth rejected (HTTP %s): %s",
                mode,
                response.status_code,
                self._response_detail(response),
            )
            return None

        if response.status_code >= 400:
            logger.warning(
                "Hive %s HTTP %s for %s: %s",
                mode,
                response.status_code,
                image_path,
                self._response_detail(response),
            )
            return None

        try:
            data = response.json()
        except ValueError:
            logger.error("Hive %s returned non-JSON for %s", mode, image_path)
            return None

        score = self._parse_ai_score(data)
        if score is None:
            logger.error("Hive %s unexpected response for %s", mode, image_path)
            return None

        filename = os.path.basename(image_path)
        logger.info("Hive %s score %.1f%% for %s", mode, score, filename)
        return round(max(0.0, min(100.0, score)), 1)

    @staticmethod
    def _response_detail(response: requests.Response) -> str:
        try:
            data = response.json()
            if isinstance(data, dict):
                for key in ("message", "error", "detail", "title"):
                    value = data.get(key)
                    if value:
                        return str(value)[:400]
                return str(data)[:400]
            return str(data)[:400]
        except Exception:
            return (response.text or "")[:400]

    def _parse_ai_score(self, data: dict) -> float | None:
        outputs = data.get("output") or []
        for item in outputs:
            if not isinstance(item, dict):
                continue
            score = self._score_from_classes(item.get("classes") or [])
            if score is not None:
                return score

        # Legacy / wrapped responses
        status_list = data.get("status") or []
        for status_item in status_list:
            if not isinstance(status_item, dict):
                continue
            response = status_item.get("response") or {}
            for item in response.get("output") or []:
                if isinstance(item, dict):
                    score = self._score_from_classes(item.get("classes") or [])
                    if score is not None:
                        return score

        return self._find_score_in_tree(data)

    def _find_score_in_tree(self, obj) -> float | None:
        if isinstance(obj, dict):
            classes = obj.get("classes")
            if isinstance(classes, list):
                score = self._score_from_classes(classes)
                if score is not None:
                    return score
            for value in obj.values():
                score = self._find_score_in_tree(value)
                if score is not None:
                    return score
        elif isinstance(obj, list):
            for item in obj:
                score = self._find_score_in_tree(item)
                if score is not None:
                    return score
        return None

    def _score_from_classes(self, classes: list) -> float | None:
        ai_score = None
        not_ai_score = None

        for item in classes:
            if not isinstance(item, dict):
                continue
            name = (item.get("class") or "").lower().replace("-", "_")
            raw = item.get("value")
            if raw is None:
                raw = item.get("score")
            if raw is None:
                continue
            value = float(raw)

            if name == "ai_generated":
                ai_score = value
            elif name == "not_ai_generated":
                not_ai_score = value

        if ai_score is not None:
            return ai_score * 100.0 if ai_score <= 1.0 else ai_score
        if not_ai_score is not None:
            pct = (1.0 - not_ai_score) * 100.0 if not_ai_score <= 1.0 else (100.0 - not_ai_score)
            return pct

        return None
