"""Sampler multi-sampel: memilih rekaman per nada & kekuatan (velocity layer), round-robin,
geser pitch berkualitas tinggi (soxr), envelope release. Untuk instrumen rekaman asli."""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr

from .. import SR
from .song import Note

NOTE_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
           "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


@dataclass
class Zone:
    path: Path
    key: int          # nada asli rekaman
    vel_lo: int
    vel_hi: int
    rr: int = 1


@dataclass
class LibDef:
    name: str
    zones: list[Zone]
    release: float = 0.25        # detik fade setelah note-off
    gain_db: float = 0.0
    max_len: float = 12.0        # potong sampel yang sangat panjang
    vel_curve: float = 0.6       # 0 = velocity tidak mengubah volume dalam satu layer, 1 = linear


def _parse_name(stem: str, pattern: str, octave_offset: int):
    m = re.fullmatch(pattern, stem)
    if not m:
        return None
    g = m.groupdict()
    key = (int(g["oct"]) + octave_offset) * 12 + NOTE_PC[g["note"]]
    return key, int(g.get("vel") or 1), int(g.get("rr") or 1)


def load_lib(lib_dir: Path) -> LibDef:
    """Membaca instrument.json di folder library."""
    meta = json.loads((lib_dir / "instrument.json").read_text())
    parsed = []
    for p in sorted(lib_dir.glob(meta.get("glob", "*.wav"))):
        r = _parse_name(p.stem, meta["pattern"], meta.get("octave_offset", 1))
        if r:
            parsed.append((p, *r))
    if not parsed:
        raise RuntimeError(f"library {lib_dir} kosong / pola nama tidak cocok")
    vels = sorted({v for _, _, v, _ in parsed})
    # bagi rentang velocity 1..127 rata ke tiap layer
    bounds = {v: (1 + i * 127 // len(vels), (i + 1) * 127 // len(vels)) for i, v in enumerate(vels)}
    zones = [Zone(p, k, *bounds[v], rr) for p, k, v, rr in parsed]
    return LibDef(meta["name"], zones, meta.get("release", 0.25), meta.get("gain_db", 0.0),
                  meta.get("max_len", 12.0), meta.get("vel_curve", 0.6))


@lru_cache(maxsize=4096)
def _sample(path: str, max_len: float) -> np.ndarray:
    x, sr = sf.read(path, dtype="float32", always_2d=True, frames=int(max_len * 48000))
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    x = x[:, :2]
    if sr != SR:
        x = soxr.resample(x, sr, SR, quality="HQ").astype(np.float32)
    return x


@lru_cache(maxsize=8192)
def _shifted(path: str, max_len: float, semis: int) -> np.ndarray:
    x = _sample(path, max_len)
    if semis == 0:
        return x
    ratio = 2 ** (semis / 12)
    # memutar lebih cepat = resample ke rate lebih rendah
    return soxr.resample(x, SR, SR / ratio, quality="HQ").astype(np.float32)


class Sampler:
    def __init__(self, lib: LibDef, seed: int = 0):
        self.lib = lib
        self.rng = random.Random(seed)
        self.by_key = {}
        for z in lib.zones:
            self.by_key.setdefault(z.key, []).append(z)
        self.keys = sorted(self.by_key)

    def _pick(self, key: int, vel: int) -> Zone:
        # rekaman terdekat; utamakan geser pitch kecil (dan sedikit preferensi ke bawah -> warna lebih alami)
        k0 = min(self.keys, key=lambda k: (abs(k - key), k > key))
        zs = [z for z in self.by_key[k0] if z.vel_lo <= vel <= z.vel_hi]
        if not zs:
            zs = sorted(self.by_key[k0], key=lambda z: abs((z.vel_lo + z.vel_hi) / 2 - vel))[:2]
        return self.rng.choice(zs)

    def render(self, notes: list[Note], duration: float) -> np.ndarray:
        total = int(duration * SR)
        out = np.zeros((total, 2), np.float32)
        rel = int(self.lib.release * SR)
        g0 = 10 ** (self.lib.gain_db / 20)
        for n in notes:
            st = int(n.start * SR)
            if st >= total:
                continue
            z = self._pick(n.key, n.vel)
            x = _shifted(str(z.path), self.lib.max_len, n.key - z.key)
            hold = int(n.dur * SR)
            ln = min(len(x), hold + rel, total - st)
            if ln <= 0:
                continue
            seg = x[:ln].copy()
            if hold < ln:  # release setelah note-off
                r = ln - hold
                seg[hold:] *= np.linspace(1, 0, r, dtype=np.float32)[:, None] ** 2
            # posisi relatif velocity dalam layer -> volume halus antar layer
            span = max(1, z.vel_hi - z.vel_lo)
            pos = (n.vel - z.vel_lo) / span
            g = g0 * (1 - self.lib.vel_curve * 0.5 * (1 - pos)) * (n.vel / 100) ** 0.3
            # anti klik di awal
            f = min(32, ln)
            seg[:f] *= np.linspace(0, 1, f, dtype=np.float32)[:, None]
            out[st:st + ln] += seg * np.float32(g)
        return out


LIB_DIR_DEFAULT = Path(__file__).resolve().parents[2] / "instruments"


def available(lib_root: Path = LIB_DIR_DEFAULT) -> dict[str, Path]:
    return {p.parent.name: p.parent for p in lib_root.glob("*/instrument.json")}
