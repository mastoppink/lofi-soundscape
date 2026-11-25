"""Layer ambience kontinu. Pakai rekaman asli di samples/<layer>/ bila ada,
kalau tidak ada, pakai suara sintetis sebagai cadangan."""
from __future__ import annotations

import math
from fractions import Fraction
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter, resample_poly, sosfilt

from . import SR

AUDIO_EXT = {".wav", ".flac", ".ogg", ".mp3", ".aif", ".aiff"}


def load_audio(path: Path) -> np.ndarray:
    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    x = x[:, :2]
    if sr != SR:
        f = Fraction(SR, sr).limit_denominator(1000)
        x = resample_poly(x, f.numerator, f.denominator, axis=0).astype(np.float32)
    # normalisasi ke RMS yang seragam supaya slider volume konsisten
    rms = float(np.sqrt(np.mean(x ** 2))) or 1.0
    return x * (0.1 / rms)


class SampleLayer:
    """Memutar file-file rekaman secara bergantian dengan crossfade panjang (tanpa sambungan)."""

    def __init__(self, files: list[Path], rng: np.random.Generator, xfade: float = 4.0):
        self.clips = [load_audio(f) for f in files]
        self.rng = rng
        self.xf = int(xfade * SR)
        self.buf = np.zeros((0, 2), dtype=np.float32)

    def _next_clip(self) -> np.ndarray:
        c = self.clips[self.rng.integers(len(self.clips))]
        # mulai dari titik acak supaya loop tidak terdengar berulang
        if len(c) > self.xf * 4:
            s = int(self.rng.integers(0, len(c) - self.xf * 3))
            c = np.concatenate([c[s:], c[:s]])
        return c

    def read(self, n: int) -> np.ndarray:
        while len(self.buf) < n + self.xf:
            c = self._next_clip()
            if len(self.buf) < self.xf:
                self.buf = c.copy()
                continue
            fade = np.linspace(0, 1, self.xf, dtype=np.float32)[:, None]
            fo, fi = np.sqrt(1 - fade), np.sqrt(fade)  # equal-power
            head = self.buf[:-self.xf]
            mix = self.buf[-self.xf:] * fo + c[: self.xf] * fi
            self.buf = np.concatenate([head, mix, c[self.xf:]])
        out, self.buf = self.buf[:n], self.buf[n:]
        return out


CAL = {"rain": 0.1 / 0.031, "wind": 0.1 / 0.146, "ocean": 0.1 / 0.17, "fire": 0.1 / 0.197}


class SynthLayer:
    """Cadangan sintetis: rain, wind, ocean, fire."""

    def __init__(self, kind: str, rng: np.random.Generator):
        self.kind, self.rng, self.t = kind, rng, 0.0
        spec = {
            "rain": [(2, [700, 9000], "band")],
            "wind": [(2, 500, "low")],
            "ocean": [(2, 1200, "low")],
            "fire": [(2, 400, "low")],
        }[kind]
        o, f, bt = spec[0]
        self.sos = butter(o, f, btype=bt, fs=SR, output="sos")
        self.z = np.zeros((self.sos.shape[0], 2, 2))
        self.pop_sos = butter(2, [1500, 6000], btype="band", fs=SR, output="sos")
        self.pz = np.zeros((self.pop_sos.shape[0], 2, 2))
        self.brown = np.zeros(1)

    def read(self, n: int) -> np.ndarray:
        r = self.rng
        tt = self.t + np.arange(n) / SR
        self.t += n / SR
        if self.kind in ("wind", "ocean", "fire"):
            src, self.brown = lfilter([0.1], [1, -0.995], r.standard_normal(n), zi=self.brown)
        else:
            src = r.standard_normal(n)
        y, self.z = sosfilt(self.sos, np.stack([src, np.roll(src, 113)], 1), axis=0, zi=self.z)
        if self.kind == "wind":
            y *= (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * tt) * np.sin(2 * np.pi * 0.023 * tt))[:, None] * 0.25
        elif self.kind == "ocean":
            sw = 0.5 + 0.5 * np.sin(2 * np.pi * tt / 9.0) ** 3
            y *= (0.15 + sw)[:, None] * 0.25
        elif self.kind == "rain":
            y *= 0.05
            drops = np.zeros((n, 2))
            k = r.poisson(n / SR * 60)
            drops[r.integers(0, n, k), r.integers(0, 2, k)] = r.standard_normal(k) * 0.25
            d, self.pz = sosfilt(self.pop_sos, drops, axis=0, zi=self.pz)
            y = y + d
        elif self.kind == "fire":
            y *= 0.2
            pops = np.zeros((n, 2))
            k = r.poisson(n / SR * 12)
            pops[r.integers(0, n, k), r.integers(0, 2, k)] = r.standard_normal(k) * r.exponential(0.3, k)
            p, self.pz = sosfilt(self.pop_sos, pops, axis=0, zi=self.pz)
            y = y + p
        # kalibrasi supaya RMS ~0.1 (sama dengan rekaman yang dinormalisasi)
        return (y * CAL[self.kind]).astype(np.float32)


class Ambience:
    def __init__(self, layers: dict[str, float], samples_dir: Path, seed: int, log=print):
        self.layers = []
        rng = np.random.default_rng(seed + 999)
        for name, vol in layers.items():
            if vol <= 0:
                continue
            d = samples_dir / name
            files = sorted(p for p in d.glob("*") if p.suffix.lower() in AUDIO_EXT) if d.exists() else []
            if files:
                log(f"  ambience '{name}': {len(files)} rekaman")
                self.layers.append((SampleLayer(files, rng), vol))
            elif name in ("rain", "wind", "ocean", "fire"):
                log(f"  ambience '{name}': tidak ada rekaman di {d}, pakai versi sintetis")
                self.layers.append((SynthLayer(name, rng), vol))
            else:
                log(f"  ambience '{name}': dilewati (taruh file audio di {d})")

    def read(self, n: int) -> np.ndarray:
        out = np.zeros((n, 2), dtype=np.float32)
        for layer, vol in self.layers:
            out += layer.read(n) * vol
        return out
