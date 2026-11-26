"""Bunyi brush drum disintesis (sapuan & tepukan), karena tidak ada sampel brush berlisensi bebas.
Sapuan = noise ber-filter dengan envelope melengkung; tepukan = semburan noise pendek + 'body' snare."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

from .. import SR


def _noise(rng, n):
    return rng.standard_normal(n)


def sweep(rng, length=0.55, bright=1.0):
    n = int(length * SR)
    x = _noise(rng, n)
    lo, hi = 700 * bright, min(9000, 5200 * bright)
    x = sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
    t = np.linspace(0, 1, n)
    env = np.sin(np.pi * np.clip(t * 1.15, 0, 1)) ** 1.6          # naik lalu turun (gerak melingkar)
    env *= 1 + 0.25 * np.sin(2 * np.pi * rng.uniform(5, 9) * t + rng.uniform(0, 6))   # tekstur bulu sikat
    l = x * env
    r = np.roll(x, int(rng.integers(20, 80))) * env
    return np.stack([l, r], 1) * 0.25


def tap(rng, strength=1.0):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    x = sosfilt(butter(2, [900, 7500], btype="band", fs=SR, output="sos"), _noise(rng, n))
    x *= np.exp(-t / (0.045 + 0.03 * strength))
    body = np.sin(2 * np.pi * rng.uniform(180, 210) * t) * np.exp(-t / 0.06) * 0.35
    snare = sosfilt(butter(2, [2500, 6000], btype="band", fs=SR, output="sos"), _noise(rng, n)) * np.exp(-t / 0.12) * 0.25
    y = (x + body + snare) * (0.3 + 0.5 * strength)
    return np.stack([y, np.roll(y, 12)], 1) * 0.5


def make(dest: Path, seed: int = 7) -> dict:
    """Tulis file brush ke dest; kembalikan entri peta drum (nada -> [file, vel_lo, vel_hi])."""
    rng = np.random.default_rng(seed)
    m = {"40": [], "39": []}
    for i, (lo, hi, br) in enumerate([(1, 45, 0.8), (46, 80, 1.0), (81, 127, 1.2)]):
        for rr in range(3):
            f = f"brush_sweep_v{i + 1}_rr{rr + 1}.wav"
            sf.write(str(dest / f), sweep(rng, rng.uniform(0.45, 0.65), br).astype(np.float32), SR)
            m["40"].append([f, lo, hi])
            f = f"brush_tap_v{i + 1}_rr{rr + 1}.wav"
            sf.write(str(dest / f), tap(rng, 0.4 + 0.3 * i).astype(np.float32), SR)
            m["39"].append([f, lo, hi])
    return m
