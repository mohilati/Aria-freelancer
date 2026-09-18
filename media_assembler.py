"""
Premium vertical media assembler.

Key changes:
- 1080x1920, 30fps.
- Image fallback is motion-treated, but only used after video generation fails.
- Persian narration is handled separately by persian_tts.py.
- Original procedural suspense bed is always available as a fallback.
- Voice is mixed above music so Persian speech stays intelligible.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

def _run(args: List[str]) -> None:
    subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def _duration(path: str) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        check=True, text=True, stdout=subprocess.PIPE,
    )
    return float(p.stdout.strip())

def image_to_clip(image: str, output: str, seconds: float = 6.0) -> str:
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"zoompan=z='min(zoom+0.0007,1.06)':d={int(seconds*30)}:s=1080x1920:fps=30,"
        "format=yuv420p"
    )
    _run([
        "ffmpeg", "-y", "-loop", "1", "-i", image,
        "-t", str(seconds), "-vf", vf,
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        output,
    ])
    return output

def concat_video(clips: List[str], output: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        list_path = f.name
        for clip in clips:
            f.write(f"file '{Path(clip).resolve()}'\n")
    try:
        _run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            output,
        ])
    finally:
        Path(list_path).unlink(missing_ok=True)
    return output

def concat_audio(tracks: List[str], output: str) -> str:
    if not tracks:
        raise ValueError("No narration tracks")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        list_path = f.name
        for track in tracks:
            f.write(f"file '{Path(track).resolve()}'\n")
    try:
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
              "-c:a", "libmp3lame", "-b:a", "160k", output])
    finally:
        Path(list_path).unlink(missing_ok=True)
    return output

def make_suspense_bed(output: str, seconds: float) -> str:
    # Original, synthetic sound design: no copyrighted recording.
    filter_complex = (
        "[0:a]volume=0.045,lowpass=f=420,afade=t=in:st=0:d=1.5,"
        f"afade=t=out:st={max(seconds-2.0,0):.2f}:d=2[n1];"
        "[1:a]volume=0.018,highpass=f=80,lowpass=f=2600,afade=t=in:st=0:d=2,"
        f"afade=t=out:st={max(seconds-2.0,0):.2f}:d=2[n2];"
        "[n1][n2]amix=inputs=2:duration=longest,loudnorm=I=-24:TP=-2:LRA=7[out]"
    )
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=58:sample_rate=48000",
        "-f", "lavfi", "-i", "anoisesrc=color=brown:sample_rate=48000",
        "-t", str(seconds),
        "-filter_complex", filter_complex,
        "-map", "[out]", "-c:a", "aac", "-b:a", "128k", output,
    ])
    return output

def mux(video: str, narration: str, music: str, output: str) -> str:
    _run([
        "ffmpeg", "-y",
        "-i", video, "-i", narration, "-i", music,
        "-filter_complex",
        "[1:a]volume=1.0[narr];[2:a]volume=0.16[mus];"
        "[narr][mus]amix=inputs=2:duration=longest:dropout_transition=2,"
        "loudnorm=I=-16:TP=-1.5:LRA=8[a]",
        "-map", "0:v:0", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", output,
    ])
    return output
