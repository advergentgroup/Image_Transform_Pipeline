"""Adobe Illustrator COM automation for Image Trace (Windows only)."""
from __future__ import annotations

import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

_JSX_TEMPLATE = Path(__file__).resolve().parent.parent / "scripts" / "illustrator_image_trace.jsx"

# Illustrator UserInteractionLevel — suppress modal dialogs during automation.
_UI_NEVER_DISPLAY_ALERTS = 2


@contextmanager
def _com_session():
    """Initialize COM in the current thread (required for Flask background threads)."""
    import pythoncom  # noqa: PLC0415

    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()


class IllustratorService:
    def __init__(self, config: dict):
        self.max_colors = max(4, min(int(config.get("VECTOR_TRACE_COLORS", 16)), 32))
        self.noise = max(1, min(int(config.get("VECTOR_TRACE_NOISE", 4)), 20))
        self.path_fidelity = max(40, min(int(config.get("ILLUSTRATOR_PATH_FIDELITY", "95")), 100))
        self.corner_fidelity = max(40, min(int(config.get("ILLUSTRATOR_CORNER_FIDELITY", "95")), 100))
        self.export_scale = max(100, min(int(config.get("ILLUSTRATOR_EXPORT_SCALE", "200")), 400))
        self.noise_fidelity = max(1, min(int(config.get("ILLUSTRATOR_NOISE_FIDELITY", "2")), 50))
        method = str(config.get("ILLUSTRATOR_TRACING_METHOD", "abutting")).lower()
        self.tracing_method = (
            "TracingMethodType.TRACINGMETHODOVERLAPPING"
            if method in ("overlapping", "overlap")
            else "TracingMethodType.TRACINGMETHODABUTTING"
        )
        self.visible = str(config.get("ILLUSTRATOR_VISIBLE", "0")).lower() in ("1", "true", "yes")

    @staticmethod
    def is_supported_platform() -> bool:
        return sys.platform == "win32"

    def is_available(self) -> bool:
        if not self.is_supported_platform():
            return False
        try:
            with _com_session():
                import win32com.client  # noqa: PLC0415

                app = win32com.client.Dispatch("Illustrator.Application")
                _ = app.Version
                return True
        except Exception as exc:
            logger.warning("Illustrator unavailable: %s", exc)
            return False

    def image_trace(self, input_path: str, output_path: str) -> None:
        if not self.is_supported_platform():
            raise RuntimeError("Illustrator automation requires Windows")

        try:
            import win32com.client  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError("pywin32 is required for Illustrator mode (pip install pywin32)") from exc

        input_path = os.path.abspath(input_path)
        output_path = os.path.abspath(output_path)
        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"Input image not found: {input_path}")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        work_dir = os.path.dirname(output_path) or "."
        jsx_path = os.path.join(work_dir, f".ai_trace_{os.getpid()}.jsx")
        err_path = os.path.join(work_dir, f".ai_trace_{os.getpid()}.err")

        for path in (output_path, err_path):
            if os.path.isfile(path):
                os.remove(path)

        jsx = self._build_jsx(input_path, output_path, err_path)
        try:
            with open(jsx_path, "w", encoding="utf-8") as handle:
                handle.write(jsx)

            with _com_session():
                import win32com.client  # noqa: PLC0415

                app = win32com.client.Dispatch("Illustrator.Application")
                try:
                    app.Visible = self.visible
                except AttributeError:
                    logger.debug("Illustrator.Visible is read-only in this session")
                app.UserInteractionLevel = _UI_NEVER_DISPLAY_ALERTS
                app.DoJavaScriptFile(jsx_path)

            if os.path.isfile(err_path):
                with open(err_path, encoding="utf-8") as handle:
                    message = handle.read().strip()
                raise RuntimeError(message or "Illustrator Image Trace failed")

            if not os.path.isfile(output_path):
                raise RuntimeError("Illustrator did not produce output PNG")
        finally:
            for path in (jsx_path, err_path):
                if path and os.path.isfile(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def _build_jsx(self, input_path: str, output_path: str, err_path: str) -> str:
        if not _JSX_TEMPLATE.is_file():
            raise FileNotFoundError(f"JSX template missing: {_JSX_TEMPLATE}")

        template = _JSX_TEMPLATE.read_text(encoding="utf-8")
        noise_fidelity = self.noise_fidelity
        replacements = {
            "__INPUT__": self._jsx_path(input_path),
            "__OUTPUT__": self._jsx_path(output_path),
            "__ERR__": self._jsx_path(err_path),
            "__COLORS__": str(self.max_colors),
            "__NOISE_FIDELITY__": str(noise_fidelity),
            "__PATH_FIDELITY__": str(self.path_fidelity),
            "__CORNER_FIDELITY__": str(self.corner_fidelity),
            "__EXPORT_SCALE__": str(self.export_scale),
            "__TRACING_METHOD__": self.tracing_method,
        }
        for key, value in replacements.items():
            template = template.replace(key, value)
        return template

    @staticmethod
    def _jsx_path(path: str) -> str:
        return os.path.abspath(path).replace("\\", "/")
