from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _probe_duration(path: str | Path) -> float:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    return float(result.stdout.strip())


def _escape_filter_path(path: str | Path) -> str:
    # ffmpeg filtergraph escaping for Windows/Linux paths.
    value = str(Path(path).resolve()).replace("\\", "/")
    return value.replace("\\", r"\\").replace(":", r"\:")


def _make_motion_clip(
    image_path: str | Path,
    output_path: str | Path,
    duration: float,
    index: int,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> None:
    image = _escape_filter_path(image_path)

    # Alternate gentle push/pull and horizontal drift. The motion is deliberately
    # deterministic so the same scene produces the same result on every run.
    motions = [
        (
            f"scale={width * 1.14}:{height * 1.14}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            f"zoompan=z='min(zoom+0.0009,1.14)':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=1:fps={fps}:s={width}x{height}"
        ),
        (
            f"scale={width * 1.14}:{height * 1.14}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            f"zoompan=z='max(1.14-on*0.0009,1.0)':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=1:fps={fps}:s={width}x{height}"
        ),
        (
            f"scale={width * 1.14}:{height * 1.14}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            f"zoompan=z='min(zoom+0.0007,1.10)':"
            f"x='(iw-iw/zoom)*on/{max(int(duration * fps), 1)}':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=1:fps={fps}:s={width}x{height}"
        ),
        (
            f"scale={width * 1.14}:{height * 1.14}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            f"zoompan=z='min(zoom+0.0007,1.10)':"
            f"x='(iw-iw/zoom)*(1-on/{max(int(duration * fps), 1)})':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=1:fps={fps}:s={width}x{height}"
        ),
    ]

    vf = motions[index % len(motions)]

    # image2 + zoompan is more portable than relying on newer ffmpeg
    # loop/filter combinations. -t makes the final duration deterministic.
    _run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-t",
            f"{duration:.3f}",
            "-vf",
            vf,
            "-r",
            str(fps),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )


def _normalize_audio(
    input_path: str | Path,
    output_path: str | Path,
    target_lufs: float = -16.0,
) -> None:
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-af",
            f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ]
    )


def _make_silent_audio(
    output_path: str | Path,
    duration: float,
) -> None:
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t",
            f"{duration:.3f}",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ]
    )


def _concat_clips(clips: list[Path], output_path: Path) -> None:
    concat_file = output_path.parent / ".aria_concat.txt"
    concat_file.write_text(
        "".join(f"file '{str(p.resolve()).replace(chr(39), \"'\\\\''\")}'\n" for p in clips),
        encoding="utf-8",
    )
    try:
        _run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                str(output_path),
            ]
        )
    finally:
        concat_file.unlink(missing_ok=True)


def _mix_audio(
    video_path: Path,
    narration_path: Path | None,
    music_path: Path | None,
    output_path: Path,
) -> None:
    if narration_path and music_path:
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-i",
                str(narration_path),
                "-i",
                str(music_path),
                "-filter_complex",
                (
                    "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,"
                    "aresample=48000[n];"
                    "[2:a]volume=0.11,"
                    "afade=t=in:st=0:d=1.5,"
                    "afade=t=out:st=43:d=3[m];"
                    "[n][m]amix=inputs=2:duration=longest:dropout_transition=2[a]"
                ),
                "-map",
                "0:v:0",
                "-map",
                "[a]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )
    elif narration_path:
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-i",
                str(narration_path),
                "-filter_complex",
                "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[n]",
                "-map",
                "0:v:0",
                "-map",
                "[n]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )
    elif music_path:
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-i",
                str(music_path),
                "-filter_complex",
                "[1:a]volume=0.11,afade=t=in:st=0:d=1.5,afade=t=out:st=43:d=3[m]",
                "-map",
                "0:v:0",
                "-map",
                "[m]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )
    else:
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )


def _find_media_path(item: Any) -> str | None:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in (
            "path",
            "file",
            "file_path",
            "output_path",
            "video_path",
            "image_path",
            "audio_path",
        ):
            value = item.get(key)
            if value:
                return str(value)
    return None


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
    """
    Assemble approved scene assets into the final vertical MP4.

    Compatibility note:
    `aspect_ratio` is intentionally accepted here because agent.py passes it.
    Unknown keyword arguments are also tolerated so a provider/router update
    cannot break the assembler just because it adds metadata.
    """
    del kwargs

    if not scene_assets:
        raise RuntimeError("No scene assets supplied to assemble_video().")

    output = Path(output_path or os.getenv("ARIA_OUTPUT_DIR", "outputs")) / "aria_final.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)

    # Keep 9:16 as the canonical clinic-ad output. Width/height can still be
    # overridden by callers when they explicitly need another target.
    if aspect_ratio == "9:16" and (width, height) == (1080, 1920):
        width, height = 1080, 1920

    usable: list[Path] = []
    for item in scene_assets:
        path = _find_media_path(item)
        if not path:
            continue
        p = Path(path)
        if p.exists():
            usable.append(p)

    if not usable:
        raise RuntimeError("No existing visual scene files were found.")

    temp_dir = output.parent / ".aria_assembly"
    temp_dir.mkdir(parents=True, exist_ok=True)

    clips: list[Path] = []
    try:
        requested_total = float(target_duration) if target_duration else 48.0
        per_scene = requested_total / len(usable)

        for idx, asset in enumerate(usable):
            clip = temp_dir / f"scene_{idx + 1:02d}.mp4"
            suffix = asset.suffix.lower()

            if suffix in {".mp4", ".mov", ".webm", ".mkv"}:
                # Normalize video assets to the same canvas/fps.
                _run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(asset),
                        "-t",
                        f"{per_scene:.3f}",
                        "-vf",
                        (
                            f"scale={width}:{height}:"
                            "force_original_aspect_ratio=decrease,"
                            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
                        ),
                        "-r",
                        str(fps),
                        "-an",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "20",
                        "-pix_fmt",
                        "yuv420p",
                        "-movflags",
                        "+faststart",
                        str(clip),
                    ]
                )
            else:
                _make_motion_clip(
                    asset,
                    clip,
                    per_scene,
                    idx,
                    width=width,
                    height=height,
                    fps=fps,
                )
            clips.append(clip)

        silent_video = temp_dir / "visual_track.mp4"
        _concat_clips(clips, silent_video)

        final_narration: Path | None = None
        if narration_path and Path(narration_path).exists():
            final_narration = temp_dir / "narration_normalized.m4a"
            _normalize_audio(narration_path, final_narration)

        final_music: Path | None = None
        if music_path and Path(music_path).exists():
            final_music = Path(music_path)

        # If narration exists, the final output follows narration duration;
        # otherwise keep the requested visual duration.
        mixed = temp_dir / "mixed.mp4"
        _mix_audio(silent_video, final_narration, final_music, mixed)

        # Final hard normalization to the requested delivery format.
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(mixed),
                "-vf",
                (
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                    "format=yuv420p"
                ),
                "-r",
                str(fps),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(output),
            ]
        )

        metadata = {
            "aspect_ratio": aspect_ratio,
            "resolution": f"{width}x{height}",
            "fps": fps,
            "scene_count": len(usable),
            "requested_duration": requested_total,
            "narration": bool(final_narration),
            "music": bool(final_music),
        }
        output.with_suffix(".json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return str(output)

    finally:
        # Keep the final deliverable and metadata; remove only temporary clips.
        for p in temp_dir.glob("*"):
            if p.is_file():
                p.unlink(missing_ok=True)
        temp_dir.rmdir()
