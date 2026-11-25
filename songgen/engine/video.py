"""Gabungkan audio + gambar cover menjadi MP4 siap upload YouTube (butuh ffmpeg)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def make_video(audio: Path, cover: Path, out: Path, log=print) -> Path:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg tidak ditemukan. Mac: brew install ffmpeg | Windows: winget install ffmpeg | Linux: apt install ffmpeg")
    cmd = ["ffmpeg", "-y", "-loop", "1", "-framerate", "1", "-i", str(cover), "-i", str(audio),
           "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=yuv420p",
           "-c:v", "libx264", "-tune", "stillimage", "-preset", "veryfast", "-r", "1",
           "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", str(out)]
    log("Membuat video: " + " ".join(cmd))
    subprocess.run(cmd, check=True)
    return out
