from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def _probe_duration(path: Path) -> float | None:
    try:
        result = _run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path)
        ])
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return None


def _make_motion_clip(
    image_path: str | Path,
    output_path: str | Path,
    duration: float,
    index: int,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> None:
    frames = max(int(round(duration * fps)), 1)
    motions = [
        f"scale={width * 1.14}:{height * 1.14}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='min(zoom+0.0009,1.14)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:fps={fps}:s={width}x{height}",
        f"scale={width * 1.14}:{height * 1.14}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='max(1.14-on*0.0009,1.0)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:fps={fps}:s={width}x{height}",
        f"scale={width * 1.14}:{height * 1.14}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='min(zoom+0.0007,1.10)':"
        f"x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)':d=1:fps={fps}:s={width}x{height}",
        f"scale={width * 1.14}:{height * 1.14}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='min(zoom+0.0007,1.10)':"
        f"x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2-(ih/zoom/2)':d=1:fps={fps}:s={width}x{height}",
    ]
    _run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-t", f"{duration:.3f}", "-vf", motions[index % len(motions)],
        "-r", str(fps), "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output_path),
    ])


def _normalize_audio(input_path: str | Path, output_path: str | Path) -> None:
    _run([
        "ffmpeg", "-y", "-i", str(input_path), "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "2",
        "-c:a", "aac", "-b:a", "192k", str(output_path)
    ])


def _concat_clips(clips: list[Path], output_path: Path) -> None:
    concat_file = output_path.parent / ".aria_concat.txt"
    concat_file.write_text(
        "".join(
            f"file '{str(p.resolve()).replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n"
            for p in clips
        ),
        encoding="utf-8",
    )
    try:
        _run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart",
            str(output_path)
        ])
    finally:
        concat_file.unlink(missing_ok=True)


def _mix_audio(
    video_path: Path,
    narration_path: Path | None,
    music_path: Path | None,
    output_path: Path,
) -> None:
    if narration_path and music_path:
        filt = (
            "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[n];"
            "[2:a]volume=0.11,afade=t=in:st=0:d=1.5,"
            "afade=t=out:st=43:d=3[m];"
            "[n][m]amix=inputs=2:duration=longest:dropout_transition=2[a]"
        )
        args = [
            "ffmpeg", "-y", "-i", str(video_path), "-i", str(narration_path),
            "-i", str(music_path), "-filter_complex", filt,
            "-map", "0:v:0", "-map", "[a]"
        ]
    elif narration_path:
        args = [
            "ffmpeg", "-y", "-i", str(video_path), "-i", str(narration_path),
            "-filter_complex",
            "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[n]",
            "-map", "0:v:0", "-map", "[n]"
        ]
    elif music_path:
        args = [
            "ffmpeg", "-y", "-i", str(video_path), "-i", str(music_path),
            "-filter_complex",
            "[1:a]volume=0.11,afade=t=in:st=0:d=1.5,afade=t=out:st=43:d=3[m]",
            "-map", "0:v:0", "-map", "[m]"
        ]
    else:
        args = [
            "ffmpeg", "-y", "-i", str(video_path), "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-map", "0:v:0", "-map", "1:a:0"
        ]
    _run(args + [
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", str(output_path)
    ])


def _find_media_path(item: Any) -> str | None:
    if isinstance(item, (str, Path)):
        return str(item)
    if isinstance(item, dict):
        for key in (
            "video", "image", "path", "file", "file_path", "output_path",
            "video_path", "image_path", "audio_path"
        ):
            if item.get(key):
                return str(item[key])
    return None


def _resolve_output(output_path: str | Path | None) -> Path:
    if output_path:
        p = Path(output_path)
        # A known media filename means "write here"; otherwise treat it as a directory.
        if p.suffix.lower() == ".mp4":
            return p
        return p / "aria_final.mp4"
    return Path(os.getenv("ARIA_OUTPUT_DIR", "outputs")) / "aria_final.mp4"


def assemble_video(
    scene_assets: list[Any] | None = None,
    narration_path: str | Path | None = None,
    music_path: str | Path | None = None,
    output_path: str | Path | None = None,
    target_duration: float | int | None = None,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    aspect_ratio: str = "9:16",
    **kwargs: Any,
) -> str:
    del kwargs
    if not scene_assets:
        raise RuntimeError("No scene assets supplied to assemble_video().")

    output = _resolve_output(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    usable: list[tuple[Path, float | None]] = []
    for item in scene_assets:
        path = _find_media_path(item)
        if not path:
            continue
        p = Path(path)
        if not p.exists() or not p.is_file():
            continue
        duration = None
        if isinstance(item, dict) and item.get("duration") is not None:
            try:
                duration = max(float(item["duration"]), 0.1)
            except (TypeError, ValueError):
                duration = None
        usable.append((p, duration))

    if not usable:
        raise RuntimeError("No existing visual scene files were found.")

    temp_dir = output.parent / ".aria_assembly"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    clips: list[Path] = []
    try:
        requested_total = max(float(target_duration), 0.1) if target_duration else 48.0
        fallback_duration = requested_total / len(usable)

        for idx, (asset, scene_duration) in enumerate(usable):
            duration = scene_duration or fallback_duration
            clip = temp_dir / f"scene_{idx + 1:02d}.mp4"
            if asset.suffix.lower() in VIDEO_EXTENSIONS:
                _run([
                    "ffmpeg", "-y", "-i", str(asset), "-t", f"{duration:.3f}",
                    "-vf",
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                    "-r", str(fps), "-an", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(clip)
                ])
            else:
                _make_motion_clip(asset, clip, duration, idx, width, height, fps)
            clips.append(clip)

        visual = temp_dir / "visual_track.mp4"
        _concat_clips(clips, visual)

        narration = None
        if narration_path and Path(narration_path).exists():
            narration = temp_dir / "narration_normalized.m4a"
            _normalize_audio(narration_path, narration)

        music = Path(music_path) if music_path and Path(music_path).exists() else None
        mixed = temp_dir / "mixed.mp4"
        _mix_audio(visual, narration, music, mixed)

        _run([
            "ffmpeg", "-y", "-i", str(mixed),
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "20", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(output)
        ])

        final_duration = _probe_duration(output)
        if not output.exists() or output.stat().st_size < 1024:
            raise RuntimeError("FFmpeg did not produce a valid MP4 output.")
        if final_duration is None or final_duration <= 0:
            raise RuntimeError("Produced MP4 has no readable duration.")

        manifest = {
            "status": "success",
            "output": str(output),
            "output_exists": True,
            "output_size_bytes": output.stat().st_size,
            "duration_seconds": final_duration,
            "aspect_ratio": aspect_ratio,
            "resolution": f"{width}x{height}",
            "fps": fps,
            "scene_count": len(usable),
            "requested_duration": requested_total,
            "narration": bool(narration),
            "music": bool(music),
            "scenes": [
                {
                    "index": i + 1,
                    "source": str(asset),
                    "asset_type": "video" if asset.suffix.lower() in VIDEO_EXTENSIONS else "image",
                    "duration": duration,
                    "generated_clip": str(clips[i]),
                }
                for i, (asset, duration) in enumerate(usable)
            ],
        }
        (output.parent / "media-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(output)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
