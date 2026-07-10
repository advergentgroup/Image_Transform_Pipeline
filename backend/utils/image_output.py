import io
import os

from PIL import Image, ImageFilter

_IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def output_extension(config: dict | None = None) -> str:
    fmt = str((config or {}).get("OUTPUT_IMAGE_FORMAT", "jpeg")).lower().strip()
    if fmt in ("jpg", "jpeg"):
        return ".jpg"
    if fmt == "png":
        return ".png"
    return ".jpg"


def output_filename(index: int, config: dict | None = None) -> str:
    return f"{index}{output_extension(config)}"


def jpeg_quality(config: dict | None = None) -> int:
    raw = (config or {}).get("OUTPUT_JPEG_QUALITY", 92)
    try:
        return max(1, min(100, int(raw)))
    except (TypeError, ValueError):
        return 92


def is_output_image(name: str) -> bool:
    lower = name.lower()
    return lower.endswith(_IMAGE_EXTS) and not name.startswith(".")


def image_index(name: str) -> int | None:
    stem, ext = os.path.splitext(name)
    if ext.lower() not in _IMAGE_EXTS:
        return None
    if stem.isdigit():
        return int(stem)
    return None


def find_index_path(directory: str, index: int, config: dict | None = None) -> str | None:
    candidates = [output_extension(config), ".jpg", ".jpeg", ".png"]
    seen: set[str] = set()
    for ext in candidates:
        if ext in seen:
            continue
        seen.add(ext)
        path = os.path.join(directory, f"{index}{ext}")
        if os.path.isfile(path):
            return path
    return None


def save_image(img: Image.Image, output_path: str, config: dict | None = None) -> None:
    ext = os.path.splitext(output_path)[1].lower()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if ext in (".jpg", ".jpeg"):
        img.convert("RGB").save(
            output_path,
            "JPEG",
            quality=jpeg_quality(config),
            optimize=True,
        )
    else:
        img.save(output_path, "PNG", optimize=True)


def save_bytes_as_output(data: bytes, output_path: str, config: dict | None = None) -> None:
    with Image.open(io.BytesIO(data)) as img:
        save_image(img, output_path, config)


def resize_and_save(path: str, size: tuple[int, int], config: dict | None = None) -> None:
    target_ext = output_extension(config)
    path_ext = os.path.splitext(path)[1].lower()
    with Image.open(path) as img:
        needs_resize = img.size != size
        needs_format = path_ext != target_ext and not (
            path_ext in (".jpg", ".jpeg") and target_ext == ".jpg"
        )
        if not needs_resize and not needs_format:
            return
        out = img.convert("RGB")
        if needs_resize:
            out = out.resize(size, Image.Resampling.LANCZOS)
            out = out.filter(ImageFilter.UnsharpMask(radius=1.4, percent=110, threshold=2))
        save_image(out, path, config)
