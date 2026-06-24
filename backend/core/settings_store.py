"""User-editable prompts (Settings tab). API keys stay in .env."""
import json
import os

from backend.services.ai_service import AIService

PROMPT_KEYS = (
    "KONTEXT_3D_PROMPT",
    "LEGACY_UNIQUE_PROMPT",
    "LEGACY_PIXAR_PROMPT",
    "NEGATIVE_PROMPT",
)

DEFAULT_PROMPTS = {
    "KONTEXT_3D_PROMPT": AIService.KONTEXT_3D_PROMPT,
    "LEGACY_UNIQUE_PROMPT": AIService.LEGACY_UNIQUE_PROMPT,
    "LEGACY_PIXAR_PROMPT": AIService.LEGACY_PIXAR_PROMPT,
    "NEGATIVE_PROMPT": AIService.NEGATIVE_PROMPT,
}


def load_prompts(settings_file: str) -> dict:
    merged = dict(DEFAULT_PROMPTS)
    if not os.path.isfile(settings_file):
        return merged
    try:
        with open(settings_file, encoding="utf-8") as f:
            data = json.load(f)
        for key in PROMPT_KEYS:
            if key in data and isinstance(data[key], str) and data[key].strip():
                merged[key] = data[key].strip()
    except (json.JSONDecodeError, OSError):
        pass
    return merged


def save_prompts(settings_file: str, prompts: dict) -> dict:
    current = load_prompts(settings_file)
    for key in PROMPT_KEYS:
        if key in prompts and isinstance(prompts[key], str):
            val = prompts[key].strip()
            current[key] = val if val else DEFAULT_PROMPTS[key]
    os.makedirs(os.path.dirname(settings_file) or ".", exist_ok=True)
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)
    return current
