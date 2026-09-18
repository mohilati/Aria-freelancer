"""
Aria Freelancer media assembler.

Compatible with the current agent.py API:
    assemble_video(
        scene_assets=[...],
        music_path=...,
        output_path=...,
        aspect_ratio="9:16",
    )

It accepts generated video clips and image fallbacks, concatenates narration,
adds an original procedural suspense bed when external music is unavailable,
and writes a real MP4 with audio.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Union


PathLike = Union[str, Path]


def _run(args: List[str]) -> None:
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "FFmpeg failed:\n"
            + result.stderr[-4000:]
        )


def _probe_duration(path: PathLike) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _has_audio(path: PathLike) -> bool:
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=index",
            "-of", "csv=p=0",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return bool(result.stdout.strip())


def image_to_clip(
    image: PathLike,
    output: PathLike,
    seconds: float = 6.0,
) -> Path:
    """Turn an image into a subtle-motion vertical video clip."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    frames = max(30, int(round(seconds * 30)))

    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"zoompan=z='min(zoom+0.00055,1.055)':"
        f"d={frames}:"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "s=1080x1920:fps=30,"
        "format=yuv420p"
    )

    _run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image),
        "-t", f"{seconds:.3f}",
        "-vf", vf,
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(output),
    ])

    return output


def normalize_video(
    source: PathLike,
    output: PathLike,
) -> Path:
    """Normalize an arbitrary generated video to 1080x1920/30fps."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "fps=30,"
        "format=yuv420p"
    )

    _run([
        "ffmpeg", "-y",
        "-i", str(source),
        "-vf", vf,
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(output),
    ])

    return output


def concat_video(clips: List[PathLike], output: PathLike) -> Path:
    if not clips:
        raise ValueError("No video clips to concatenate.")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as handle:
        list_path = Path(handle.name)
        for clip in clips:
            # ffmpeg concat demuxer requires escaped single quotes.
            safe = str(Path(clip).resolve()).replace("'", r"'\''")
            handle.write(f"file '{safe}'\n")

    try:
        _run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_path),
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,fps=30,format=yuv420p",
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            str(output),
        ])
    finally:
        list_path.unlink(missing_ok=True)

    return output


def concat_audio(tracks: List[PathLike], output: PathLike) -> Path:
    if not tracks:
        raise ValueError("No narration tracks were generated.")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as handle:
        list_path = Path(handle.name)
        for track in tracks:
            safe = str(Path(track).resolve()).replace("'", r"'\''")
            handle.write(f"file '{safe}'\n")

    try:
        _run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_path),
            "-c:a", "aac",
            "-b:a", "160k",
            str(output),
        ])
    finally:
        list_path.unlink(missing_ok=True)

    return output


def make_suspense_bed(output: PathLike, seconds: float) -> Path:
    """Create original procedural suspense sound design with FFmpeg."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    seconds = max(1.0, float(seconds))
    fade_out_start = max(0.0, seconds - 2.0)

    filter_complex = (
        "[0:a]"
        "volume=0.045,"
        "lowpass=f=420,"
        "afade=t=in:st=0:d=1.5,"
        f"afade=t=out:st={fade_out_start:.2f}:d=2"
        "[drone];"
        "[1:a]"
        "volume=0.012,"
        "highpass=f=80,"
        "lowpass=f=2600,"
        "afade=t=in:st=0:d=2,"
        f"afade=t=out:st={fade_out_start:.2f}:d=2"
        "[noise];"
        "[drone][noise]"
        "amix=inputs=2:duration=longest:dropout_transition=2,"
        "loudnorm=I=-24:TP=-2:LRA=7"
        "[out]"
    )

    _run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "sine=frequency=58:sample_rate=48000",
        "-f", "lavfi",
        "-i", "anoisesrc=color=brown:sample_rate=48000",
        "-t", f"{seconds:.3f}",
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "aac",
        "-b:a", "128k",
        str(output),
    ])

    return output


def mux(
    video: PathLike,
    narration: PathLike,
    music: PathLike,
    output: PathLike,
) -> Path:
    """Mix narration above music and mux with the video."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    _run([
        "ffmpeg", "-y",
        "-i", str(video),
        "-i", str(narration),
        "-i", str(music),
        "-filter_complex",
        "[1:a]volume=1.0[narr];"
        "[2:a]volume=0.16[mus];"
        "[narr][mus]"
        "amix=inputs=2:duration=first:dropout_transition=2,"
        "loudnorm=I=-16:TP=-1.5:LRA=8[a]",
        "-map", "0:v:0",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(output),
    ])

    return output


def assemble_video(
    scene_assets: List[dict],
    music_path: Optional[PathLike],
    output_path: PathLike,
    aspect_ratio: str = "9:16",
) -> Path:
    """
    Assemble the scene_assets produced by the current agent.py.

    Each scene asset may contain:
      - video: generated video path
      - image: image fallback path
      - voice: narration path
      - duration: desired duration
    """
    if aspect_ratio != "9:16":
        raise ValueError("Current assembler supports 9:16 vertical output only.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not scene_assets:
        raise ValueError("No scene assets supplied.")

    work = output_path.parent / "_assembly"
    work.mkdir(parents=True, exist_ok=True)

    clips: List[Path] = []
    narration_tracks: List[Path] = []

    for index, asset in enumerate(scene_assets, start=1):
        duration = float(asset.get("duration") or 6.0)
        video = asset.get("video")
        image = asset.get("image")
        voice = asset.get("voice")

        if video and Path(video).exists():
            clip = work / f"scene-{index:02d}.mp4"
            normalize_video(video, clip)
            clips.append(clip)
        elif image and Path(image).exists():
            clip = work / f"scene-{index:02d}.mp4"
            image_to_clip(image, clip, seconds=duration)
            clips.append(clip)
        else:
            print(f"[Assembler] Scene {index}: no visual asset; skipped.")

        if voice and Path(voice).exists():
            narration_tracks.append(Path(voice))

    if not clips:
        raise RuntimeError("No usable visual scenes were available.")

    video_only = work / "video-only.mp4"
    concat_video(clips, video_only)

    if narration_tracks:
        narration = work / "narration.m4a"
        concat_audio(narration_tracks, narration)
    else:
        # Keep the API strict: an approved media job must have narration.
        raise RuntimeError(
            "No narration tracks were generated. "
            "Refusing to produce a silent clinic advertisement."
        )

    total_duration = _probe_duration(video_only)

    if music_path and Path(music_path).exists():
        music = Path(music_path)
    else:
        music = work / "fallback-suspense.m4a"
        make_suspense_bed(music, total_duration)
        print("[Assembler] External music unavailable -> original suspense fallback.")

    mux(
        video=video_only,
        narration=narration,
        music=music,
        output=output_path,
    )

    if not output_path.exists() or output_path.stat().st_size < 10_000:
        raise RuntimeError("Final MP4 was not created correctly.")

    if not _has_audio(output_path):
        raise RuntimeError("Final MP4 has no audio stream.")

    final_duration = _probe_duration(output_path)
    if final_duration < 10:
        raise RuntimeError(f"Final MP4 is unexpectedly short: {final_duration:.2f}s")

    print(
        f"[Assembler] Final MP4: {output_path} "
        f"({final_duration:.1f}s, {output_path.stat().st_size} bytes)"
    )

    return output_path
