"""Standard 9:16 reference + 16:9 turnaround output dimensions."""

# Replicate flux-dev only accepts megapixels "1" or "0.25" — exact sizes come from resize.
FLUX_DEV_MEGAPIXELS = "1"

# Portrait reference (W×H) and matching landscape turnaround sheet (W×H).
OUTPUT_SIZE_PRESETS: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {
    "1024": ((1024, 1820), (1820, 1024)),
    "1080": ((1080, 1920), (1920, 1080)),
    "1152": ((1152, 2048), (2048, 1152)),
    "1296": ((1296, 2304), (2304, 1296)),
    "1440": ((1440, 2560), (2560, 1440)),
    "1620": ((1620, 2880), (2880, 1620)),
    "2160": ((2160, 3840), (3840, 2160)),
    "2880": ((2880, 5120), (5120, 2880)),
    "4320": ((4320, 7680), (7680, 4320)),
}

MAX_OUTPUT_SIZE = max(OUTPUT_SIZE_PRESETS.keys(), key=int)
DEFAULT_OUTPUT_SIZE = "2880"


def _int_or_default(val, default: int) -> int:
    if val is None or val == "":
        return default
    return int(val)


def _flux_megapixels(config: dict) -> str:
    val = str(config.get("FLUX_DEV_MEGAPIXELS", FLUX_DEV_MEGAPIXELS)).strip()
    return val if val in ("1", "0.25") else FLUX_DEV_MEGAPIXELS


def resolve_output_dimensions(config: dict) -> dict:
    """Merge OUTPUT_SIZE preset into reference/turnaround width/height fields."""
    preset_key = str(config.get("OUTPUT_SIZE", DEFAULT_OUTPUT_SIZE)).strip()
    preset = OUTPUT_SIZE_PRESETS.get(preset_key)
    if preset is None:
        preset_key = DEFAULT_OUTPUT_SIZE
        preset = OUTPUT_SIZE_PRESETS[preset_key]

    (ref_w, ref_h), (turn_w, turn_h) = preset

    return {
        "OUTPUT_SIZE": preset_key,
        "REFERENCE_WIDTH": _int_or_default(config.get("REFERENCE_WIDTH"), ref_w),
        "REFERENCE_HEIGHT": _int_or_default(config.get("REFERENCE_HEIGHT"), ref_h),
        "TURNAROUND_SHEET_WIDTH": _int_or_default(config.get("TURNAROUND_SHEET_WIDTH"), turn_w),
        "TURNAROUND_SHEET_HEIGHT": _int_or_default(config.get("TURNAROUND_SHEET_HEIGHT"), turn_h),
        "FLUX_DEV_MEGAPIXELS": _flux_megapixels(config),
    }
