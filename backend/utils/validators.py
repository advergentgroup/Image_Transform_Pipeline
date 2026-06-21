from werkzeug.datastructures import FileStorage


def validate_files(files: list[FileStorage], config: dict) -> str | None:
    """
    Validates uploaded files.
    Returns error message string or None if valid.
    """
    if not files or all(f.filename == "" for f in files):
        return "No files uploaded"

    max_files = config.get("MAX_FILES_PER_JOB", 10)
    if len(files) > max_files:
        return f"Maximum {max_files} files per upload"

    allowed = config.get("ALLOWED_EXTENSIONS", {"jpg", "jpeg", "png"})
    for f in files:
        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in allowed:
            return f"File '{f.filename}' is not allowed. Use JPG or PNG."

    return None
