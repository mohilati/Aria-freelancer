from __future__ import annotations

from pathlib import Path
from typing import Any


def _result_value(result: Any, *keys: str) -> Any:
    """Read a value from object-like or dict-like provider results."""
    if result is None:
        return None
    if isinstance(result, dict):
        for key in keys:
            value = result.get(key)
            if value:
                return value
        return None
    for key in keys:
        value = getattr(result, key, None)
        if value:
            return value
    return None


def _existing_path(value: Any) -> str | None:
    if not value:
        return None
    try:
        path = Path(str(value))
    except (TypeError, ValueError):
        return None
    return str(path) if path.exists() and path.is_file() else None


def register_visual_scene(
    scene_assets: list[dict[str, Any]],
    *,
    index: int,
    duration: float,
    image_result: Any = None,
    video_result: Any = None,
    voice_path: str | None = None,
    on_screen_text: str = "",
) -> bool:
    """Register the best available visual asset for a scene.

    Provider results may be objects or dictionaries. Video wins when valid;
    otherwise a valid image is registered so the assembler can turn it into
    a real MP4 clip with motion.
    """
    video_ok = bool(_result_value(video_result, "ok", "success"))
    image_ok = bool(_result_value(image_result, "ok", "success"))

    video_path = _existing_path(
        _result_value(video_result, "output_path", "video_path", "path", "file_path", "file")
    )
    image_path = _existing_path(
        _result_value(image_result, "output_path", "image_path", "path", "file_path", "file")
    )

    if video_ok and video_path:
        scene_assets.append({
            "index": int(index),
            "duration": float(duration),
            "video": video_path,
            "image": None,
            "path": video_path,
            "voice": voice_path,
            "text": on_screen_text,
            "asset_type": "video",
        })
        return True

    if image_ok and image_path:
        scene_assets.append({
            "index": int(index),
            "duration": float(duration),
            "video": None,
            "image": image_path,
            "path": image_path,
            "voice": voice_path,
            "text": on_screen_text,
            "asset_type": "image",
        })
        return True

    return False
