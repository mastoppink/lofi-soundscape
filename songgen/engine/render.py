"""Pipeline lengkap: SongSpec -> arrangement -> not per layer -> audio -> file."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path

import soundfile as sf

from .. import SR
from . import genres
from .arrangement import Arrangement
from .mixer import compose, mix, render_stems
from .song import SongSpec

WORDS = {
    "sad": (["Blue", "Late", "Lonely", "Grey", "Faded", "Quiet", "Rainy", "Distant", "Empty", "Midnight"],
            ["Avenue", "Letters", "Hours", "Station", "Window", "Blues", "Memory", "Harbor", "Shadows", "Goodbye"]),
    "happy": (["Golden", "Sunny", "Bright", "Easy", "Sweet", "Lucky", "Morning", "Dancing", "Little", "Spring"],
              ["Stroll", "Steps", "Sunday", "Garden", "Talk", "Breeze", "Swing", "Corner", "Street", "Smile"]),
}


def title_for(spec: SongSpec) -> str:
    rng = random.Random(spec.seed * 31 + 7)
    a, b = WORDS["sad" if spec.valence < 0.5 else "happy"]
    return f"{rng.choice(a)} {rng.choice(b)}"


def arrange(spec: SongSpec) -> Arrangement:
    return genres.get(spec.genre).arrange(spec)


@dataclass
class Result:
    path: Path
    title: str
    arrangement: Arrangement
    seconds: float


def render_song(spec: SongSpec, out: Path, soundfont: Path, max_seconds: float | None = None,
                stems_dir: Path | None = None, log=print) -> Result:
    t0 = time.time()
    arr = arrange(spec)
    title = title_for(spec)
    log(f"'{title}' — {arr.describe().splitlines()[0]}")
    notes = compose(spec, arr, log)
    stems = render_stems(spec, arr, notes, soundfont, max_seconds, log)
    if not stems:
        raise SystemExit("Tidak ada layer yang bunyi (semua mati/mute).")
    audio = mix(spec, stems, spec.seed)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), audio, SR, subtype="PCM_24" if out.suffix.lower() in (".wav", ".flac") else None)
    if stems_dir:
        stems_dir.mkdir(parents=True, exist_ok=True)
        for k, x in stems.items():
            sf.write(str(stems_dir / f"{k}.wav"), x, SR, subtype="PCM_24")
    el = time.time() - t0
    log(f"Selesai: {out} ({len(audio) / SR:.0f} detik audio, {el:.0f} detik proses)")
    return Result(out, title, arr, len(audio) / SR)
