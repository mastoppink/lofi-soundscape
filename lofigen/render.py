"""Render playlist panjang per potongan, langsung ditulis ke file (hemat memori)."""
from __future__ import annotations

import random
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from . import SR
from .ambience import Ambience
from .composer import compose
from .fx import StreamLimiter, Vinyl, master, sidechain, stem_fx
from .sfrender import Instrument


def fmt_ts(sec: float) -> str:
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class Band:
    def __init__(self, soundfont: Path, inst: dict):
        data = Path(soundfont).read_bytes()
        self.inst = {}
        for name, spec in inst.items():
            self.inst[name] = Instrument(data, spec.get("bank", 0), spec["preset"],
                                         drums=spec.get("drums", False), gain_db=spec.get("gain_db", 0))
        self.levels = {k: v.get("level", 1.0) for k, v in inst.items()}

    def play(self, song, lofi: float, rng: np.random.Generator) -> np.ndarray:
        n = int(song.duration * SR)
        mix = np.zeros((n, 2), dtype=np.float32)
        for name, notes in song.tracks.items():
            if name not in self.inst or not notes:
                continue
            x = self.inst[name].render(notes, song.duration)
            x = stem_fx(name, x, lofi)[:n]
            if name in ("keys", "bass", "melody"):
                x = sidechain(x, song.kick_times, depth=0.25 if name != "bass" else 0.4)
            mix[: len(x)] += x * self.levels[name]
        mix = master(mix, lofi, rng)
        rms = float(np.sqrt(np.mean(mix ** 2))) or 1.0
        return mix * (10 ** (-18 / 20) / rms)  # -18 dBFS RMS


def render(preset: dict, out: Path, duration: float, seed: int, soundfont: Path,
           samples_dir: Path, log=print) -> Path:
    t0 = time.time()
    rng_master = random.Random(seed)
    nprng = np.random.default_rng(seed)
    lofi = preset.get("lofi", 0.5)
    music_vol = preset.get("music_volume", 1.0)
    log(f"Memuat soundfont {soundfont.name} ...")
    band = Band(soundfont, preset["instruments"])
    amb = Ambience(preset.get("ambience", {}), samples_dir, seed, log)
    vinyl = Vinyl(seed)
    crackle = preset.get("vinyl", 0.6) * lofi * 1.6
    limiter = StreamLimiter(gain_db=preset.get("master_gain_db", 4.0), ceiling_db=-1.0)
    total = int(duration * SR)
    fade_in, fade_out = int(3 * SR), int(min(12, duration / 4) * SR)
    ov = int(3.0 * SR)  # crossfade antar lagu
    written = 0
    tracklist = []

    subtype = "PCM_24" if out.suffix.lower() in (".wav", ".flac", ".aiff") else None
    with sf.SoundFile(str(out), "w", SR, 2, subtype=subtype) as f:

        def emit(x: np.ndarray):
            nonlocal written
            x = x[: max(0, total - written)]
            if not len(x):
                return
            x = x * music_vol + amb.read(len(x)) + vinyl(len(x), crackle)
            idx = written + np.arange(len(x))
            env = np.minimum(1.0, np.minimum(idx / fade_in, (total - idx) / fade_out)).clip(0, 1)
            f.write(limiter(x * env[:, None]))
            written += len(x)

        pending = np.zeros((ov, 2), dtype=np.float32)
        while written + ov < total:
            s_seed = rng_master.randrange(1 << 30)
            song = compose(s_seed, preset.get("music", {}))
            start = written
            tracklist.append((start / SR, song))
            log(f"  [{fmt_ts(start / SR)}] {song.title}  ({song.key_name} {song.mode}, {song.bpm:.0f} BPM, seed {s_seed})")
            x = band.play(song, lofi, nprng)
            x[:ov] += pending
            emit(x[:-ov])
            pending = x[-ov:].copy()
            # jeda/gap sunyi antar lagu (ambience tetap jalan)
            gap = int(rng_master.uniform(0.5, 2.5) * SR)
            pending = np.concatenate([pending, np.zeros((gap, 2), np.float32)])
            emit(pending[:-ov])
            pending = pending[-ov:]
        emit(pending)
        while written < total:  # sisa diisi ambience saja
            emit(np.zeros((min(SR * 10, total - written), 2), np.float32))
        f.write(limiter(np.zeros((0, 2), np.float32), final=True))

    tl = out.with_suffix(".tracklist.txt")
    tl.write_text("\n".join(f"{fmt_ts(ts)} {s.title}" for ts, s in tracklist) + "\n")
    el = time.time() - t0
    log(f"Selesai: {out} ({fmt_ts(duration)}) dalam {el:.0f} detik ({duration / el:.1f}x realtime)")
    log(f"Tracklist: {tl}")
    return out
