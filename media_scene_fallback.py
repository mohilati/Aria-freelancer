from __future__ import annotations
from pathlib import Path
from typing import Any

def register_visual_scene(scene_assets: list[dict[str, Any]], *, index: int,
                          duration: float, image_result: Any = None,
                          video_result: Any = None, voice_path: str | None = None,
                          on_screen_text: str = "") -> bool:
    video_path = getattr(video_result, "output_path", None) if video_result else None
    image_path = getattr(image_result, "output_path", None) if image_result else None

    if video_result is not None and getattr(video_result, "ok", False) and video_path and Path(video_path).exists():
        scene_assets.append({"index": index, "duration": float(duration),
                             "video": str(video_path), "image": None, "path": str(video_path),
                             "voice": voice_path, "text": on_screen_text, "asset_type": "video"})
        return True

    if image_result is not None and getattr(image_result, "ok", False) and image_path and Path(image_path).exists():
        scene_assets.append({"index": index, "duration": float(duration),
                             "video": None, "image": str(image_path), "path": str(image_path),
                             "voice": voice_path, "text": on_screen_text, "asset_type": "image"})
        return True
    return False
