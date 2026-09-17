from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _run(args):
    subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _probe_duration(path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _make_image_clip(image_path: str, duration: float, output: Path):
    # Ken Burns-style vertical still-image clip.
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan=z='min(zoom+0.0007,1.08)':"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        "d=1:s=1080x1920:fps=30,"
        "format=yuv420p"
    )
    frames = max(1, int(round(duration * 30)))
    vf = vf.replace("d=1:", f"d={frames}:")
    _run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-t", str(duration),
        "-vf", vf,
        "-an",
        "-r", "30",
        str(output),
    ])


def _normalize_video(video_path: str, duration: float, output: Path):
    _run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-t", str(duration),
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,fps=30,format=yuv420p",
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        str(output),
    ])


def _make_voice_track(voices, output: Path):
    valid = [p for p in voices if p and Path(p).exists()]
    if not valid:
        return None

    concat_file = output.with_suffix(".txt")
    concat_file.write_text(
        "".join(f"file '{Path(p).resolve()}'\n" for p in valid),
        encoding="utf-8",
    )
    _run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        str(output),
    ])
    concat_file.unlink(missing_ok=True)
    return output


def assemble_video(scene_assets, music_path, output_path, aspect_ratio="9:16"):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    work = output_path.parent / "_render"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    clips = []
    voices = []

    for scene in scene_assets:
        index = scene["index"]
        duration = float(scene["duration"])
        clip = work / f"scene-{index:02d}.mp4"

        if scene.get("video") and Path(scene["video"]).exists():
            _normalize_video(scene["video"], duration, clip)
        elif scene.get("image") and Path(scene["image"]).exists():
            _make_image_clip(scene["image"], duration, clip)
        else:
            raise RuntimeError(f"Scene {index} has no usable visual asset.")

        clips.append(clip)
        if scene.get("voice") and Path(scene["voice"]).exists():
            voices.append(scene["voice"])

    concat_list = work / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.resolve()}'\n" for p in clips),
        encoding="utf-8",
    )
    base_video = work / "base.mp4"
    _run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(base_video),
    ])

    voice_track = _make_voice_track(voices, work / "voice.mp3")

    inputs = ["-i", str(base_video)]
    filter_parts = []
    audio_labels = []

    if music_path and Path(music_path).exists():
        inputs += ["-stream_loop", "-1", "-i", music_path]
        filter_parts.append("[1:a]volume=0.18[music]")
        audio_labels.append("[music]")

    if voice_track and voice_track.exists():
        music_index = 2 if music_path and Path(music_path).exists() else 1
        inputs += ["-i", str(voice_track)]
        filter_parts.append(f"[{music_index}:a]volume=1.0[voice]")
        audio_labels.append("[voice]")

    if audio_labels:
        amix = "".join(audio_labels)
        filter_parts.append(
            f"{amix}amix=inputs={len(audio_labels)}:duration=first:dropout_transition=2[aout]"
        )

    if audio_labels:
        _run([
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", ";".join(filter_parts),
            "-map", "0:v:0",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path),
        ])
    else:
        shutil.copy2(base_video, output_path)

    shutil.rmtree(work, ignore_errors=True)
    return output_path
