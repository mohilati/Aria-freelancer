"""
Aria Freelancer v6 media assembler.

Turns approved stills into a polished vertical commercial when true video
generation is unavailable. Motion is intentional and synchronized to scene
durations; narration is mixed above a lightly ducked music bed.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List


def _run(cmd: List[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _duration(path: str) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return float(p.stdout.strip())


def _motion_filter(index: int, width: int = 1080, height: int = 1920) -> str:
    # Alternate gentle push-in / pull-out / lateral drift.
    zoom = "min(zoom+0.0007,1.12)" if index % 2 == 0 else "max(zoom-0.00045,1.03)"
    x = "(iw-iw/zoom)/2" if index % 3 == 0 else "((iw-iw/zoom)*0.35)"
    y = "(ih-ih/zoom)/2"
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s={width}x{height}:fps=30"
    )


def _make_scene_clip(image: str, out: str, duration: float, index: int) -> None:
    frames = max(1, round(duration * 30))
    vf = _motion_filter(index)
    _run([
        "ffmpeg", "-y", "-loop", "1", "-i", image,
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-r", "30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-an", out
    ])


def assemble_video(
    scene_assets: List[Dict[str, Any]],
    output_path: str,
    narration_path: str | None = None,
    music_path: str | None = None,
    fps: int = 30,
) -> str:
    if not scene_assets:
        raise RuntimeError("No approved scene assets available for assembly.")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / "_v6_clips"
    work.mkdir(exist_ok=True)

    clips: List[str] = []
    for i, scene in enumerate(scene_assets):
        asset = scene.get("video") or scene.get("image")
        if not asset or not Path(asset).exists():
            continue
        duration = float(scene.get("duration_seconds") or 7.0)
        clip = str(work / f"scene_{i+1:02d}.mp4")
        _make_scene_clip(asset, clip, duration, i)
        clips.append(clip)

    if not clips:
        raise RuntimeError("No usable visual assets available for assembly.")

    concat = work / "concat.txt"
    concat.write_text(
        "".join(f"file '{Path(x).resolve()}'\n" for x in clips),
        encoding="utf-8",
    )

    visual = work / "visual.mp4"
    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c", "copy", str(visual)
    ])

    inputs = ["-i", str(visual)]
    filters = ["[0:v]format=yuv420p[v]"]
    maps = ["-map", "[v]"]

    if narration_path and Path(narration_path).exists():
        inputs += ["-i", narration_path]
        filters = ["[0:v]format=yuv420p[v]", "[1:a]loudnorm=I=-16:TP=-1.5:LRA=7[n]"]
        maps += ["-map", "[n]"]

    if music_path and Path(music_path).exists():
        music_input_index = 2 if narration_path and Path(narration_path).exists() else 1
        inputs += ["-i", music_path]
        if narration_path and Path(narration_path).exists():
            filters.append(
                f"[{music_input_index}:a]volume=0.11,"
                f"afade=t=in:st=0:d=1.2,"
                f"afade=t=out:st=44:d=4[m]"
            )
            filters.append("[n][m]amix=inputs=2:duration=first:dropout_transition=2[a]")
            maps += ["-map", "[a]"]
        else:
            filters.append(f"[{music_input_index}:a]volume=0.18[m]")
            maps += ["-map", "[m]"]

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", ";".join(filters),
        *maps,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-r", str(fps), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        str(out),
    ]
    _run(cmd)
    return str(out)
