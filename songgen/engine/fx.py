"""Efek: EQ per peran, master bus, efek lofi opsional (tape, vinyl), limiter."""
from __future__ import annotations

import numpy as np
from pedalboard import (Bitcrush, Compressor, Gain, HighpassFilter, Limiter, LowpassFilter,
                        Pedalboard, Reverb)
from scipy.signal import butter, sosfilt

from .. import SR


def _pb(board: Pedalboard, x: np.ndarray) -> np.ndarray:
    return board(x.T.astype(np.float32), SR, reset=True).T


def stem_fx(role: str, x: np.ndarray, lofi: float = 0.0) -> np.ndarray:
    """EQ/kompresi per peran (reverb ditangani bus bersama di mixer)."""
    lp = 18000 - 12000 * lofi
    if role == "chords":
        b = [HighpassFilter(90), LowpassFilter(lp)]
    elif role == "melody":
        b = [HighpassFilter(140), LowpassFilter(lp), Compressor(threshold_db=-20, ratio=2, attack_ms=15, release_ms=150)]
    elif role == "bass":
        b = [HighpassFilter(35), LowpassFilter(min(lp, 4000)), Compressor(threshold_db=-20, ratio=3, attack_ms=10, release_ms=120)]
    elif role == "drums":
        b = [HighpassFilter(35), LowpassFilter(lp), Compressor(threshold_db=-18, ratio=2.5, attack_ms=8, release_ms=90)]
        if lofi > 0.3:
            b.insert(1, Bitcrush(bit_depth=14 - 6 * lofi))
    elif role == "pad":
        b = [HighpassFilter(120), LowpassFilter(min(lp, 9000))]
    else:
        return x
    return _pb(Pedalboard(b), x)


def sidechain(x: np.ndarray, kick_times, depth: float = 0.35, release: float = 0.22) -> np.ndarray:
    """Pumping halus: volume turun sesaat setiap kick."""
    n = len(x)
    env = np.ones(n, dtype=np.float32)
    rel = int(release * SR)
    curve = 1 - depth * np.exp(-np.linspace(0, 5, rel)).astype(np.float32)
    for kt in kick_times:
        i = int(kt * SR)
        if i >= n:
            break
        j = min(n, i + rel)
        env[i:j] = np.minimum(env[i:j], curve[: j - i])
    return x * env[:, None]


def wow_flutter(x: np.ndarray, amount: float, rng: np.random.Generator) -> np.ndarray:
    """Modulasi pitch ala pita kaset (variable delay)."""
    n = len(x)
    tt = np.arange(n) / SR
    wow = np.sin(2 * np.pi * 0.55 * tt + rng.uniform(0, 6.28)) * 0.0022
    wow += np.sin(2 * np.pi * 0.23 * tt + rng.uniform(0, 6.28)) * 0.0014
    flutter = np.sin(2 * np.pi * 6.3 * tt) * 0.00012
    delay = (0.004 + (wow + flutter) * amount) * SR
    idx = np.arange(n) - delay
    idx = np.clip(idx, 0, n - 1)
    return np.stack([np.interp(idx, np.arange(n), x[:, c]) for c in range(2)], axis=1).astype(np.float32)


def saturate(x: np.ndarray, drive: float) -> np.ndarray:
    k = 1 + 3 * drive
    return (np.tanh(x * k) / np.tanh(k)).astype(np.float32)


class Vinyl:
    """Generator crackle + hiss vinyl yang kontinu (bisa dipanggil per potongan)."""

    def __init__(self, seed: int):
        self.rng = np.random.default_rng(seed)
        self.sos_hiss = butter(2, [800, 9000], btype="band", fs=SR, output="sos")
        self.sos_pop = butter(2, 2500, btype="high", fs=SR, output="sos")
        self.zh = np.zeros((self.sos_hiss.shape[0], 2))
        self.zp = np.zeros((self.sos_pop.shape[0], 2))
        self.phase = 0.0

    def __call__(self, n: int, amount: float) -> np.ndarray:
        r = self.rng
        hiss, self.zh = sosfilt(self.sos_hiss, r.standard_normal(n) * 0.006, zi=self.zh)
        dust = np.zeros(n)
        k = r.poisson(n / SR * 9)
        pos = r.integers(0, n, k)
        dust[pos] = r.standard_normal(k) * r.exponential(0.12, k)
        big = r.poisson(n / SR * 0.35)
        dust[r.integers(0, n, big)] += r.choice([-1, 1], big) * r.uniform(0.2, 0.5, big)
        dust, self.zp = sosfilt(self.sos_pop, dust, zi=self.zp)
        mono = (hiss + dust) * amount
        # sedikit perbedaan kiri-kanan
        return np.stack([mono, np.roll(mono, 7)], axis=1).astype(np.float32)


def master(x: np.ndarray, lofi: float, rng: np.random.Generator, warmth: float = 0.0) -> np.ndarray:
    if lofi > 0:
        x = wow_flutter(x, 0.3 + lofi, rng)
    if lofi > 0 or warmth > 0:
        x = saturate(x, 0.1 * warmth + 0.4 * lofi)
    b = Pedalboard([HighpassFilter(28), LowpassFilter(min(19000 - 10000 * lofi, 19000 - 11000 * warmth)),
                    Compressor(threshold_db=-16, ratio=1.8, attack_ms=30, release_ms=250)])
    return _pb(b, x)


def limiter(x: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    return _pb(Pedalboard([Gain(3), Limiter(threshold_db=ceiling_db, release_ms=150)]), x)


class StreamLimiter:
    """Peak limiter sederhana dengan lookahead per blok; state tersimpan antar potongan."""

    def __init__(self, gain_db: float = 0.0, ceiling_db: float = -1.0, release: float = 0.25, block: int = 256):
        self.gain = 10 ** (gain_db / 20)
        self.ceil = 10 ** (ceiling_db / 20)
        self.block = block
        self.rel = np.exp(-block / (release * SR))
        self.g = 1.0
        self.buf = np.zeros((0, 2), np.float32)

    def __call__(self, x: np.ndarray, final: bool = False) -> np.ndarray:
        x = np.concatenate([self.buf, x * self.gain])
        B = self.block
        nb = len(x) // B if not final else -(-len(x) // B)
        keep = 1 if not final else 0  # simpan 1 blok untuk lookahead
        nb_out = max(0, nb - keep)
        if nb_out == 0:
            self.buf = x
            return np.zeros((0, 2), np.float32)
        pad = np.zeros((nb * B - len(x), 2), np.float32) if nb * B > len(x) else None
        xp = x if pad is None else np.concatenate([x, pad])
        peaks = np.abs(xp[: nb * B]).reshape(nb, B, 2).max(axis=(1, 2))
        look = np.maximum(peaks[:nb_out], peaks[1: nb_out + 1] if nb > nb_out else peaks[:nb_out])
        target = np.minimum(1.0, self.ceil / np.maximum(look, 1e-9))
        gains = np.empty(nb_out + 1)
        gains[0] = self.g
        g = self.g
        for i, tg in enumerate(target):
            g = tg if tg < g else tg + (g - tg) * self.rel
            gains[i + 1] = g
        self.g = g
        env = np.interp(np.arange(nb_out * B) / B, np.arange(nb_out + 1), gains)
        # gain sudah turun di awal blok yang mengandung puncak (lookahead 1 blok)
        env = np.minimum(env, np.repeat(target, B))
        out = xp[: nb_out * B] * env[:, None]
        self.buf = x[nb_out * B:]
        if final:
            out = out[: len(x)]
            self.buf = np.zeros((0, 2), np.float32)
        return np.clip(out, -self.ceil, self.ceil).astype(np.float32)
