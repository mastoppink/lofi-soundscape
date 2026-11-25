"""Render tiap layer lewat SoundFont, lalu mix: volume, pan, bus reverb bersama, master."""
from __future__ import annotations

import random
import zlib
from functools import lru_cache
from pathlib import Path

import numpy as np
from pedalboard import HighpassFilter, Pedalboard, Reverb

from .. import SR
from .arrangement import Arrangement
from .fx import StreamLimiter, Vinyl, master, stem_fx
from .roles import generate
from .sampler import Sampler, available, load_lib
from .sfrender import Instrument as SfInstrument
from .song import Layer, Note, SongSpec


@lru_cache(maxsize=2)
def _sf_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


def layer_seed(spec: SongSpec, layer: Layer) -> int:
    if layer.seed is not None:
        return layer.seed
    return (spec.seed * 1_000_003 + zlib.crc32(layer.id.encode())) & 0x7FFFFFFF


# 'feel' per peran (detik): bass sedikit di depan ketukan, piano & melodi sedikit di belakang (laid back)
ROLE_FEEL = {"bass": -0.006, "drums": 0.0, "chords": 0.008, "melody": 0.014, "pad": 0.02}


def compose(spec: SongSpec, arr: Arrangement) -> dict[str, list[Note]]:
    """Not untuk semua layer aktif. Setiap layer pakai seed sendiri -> bisa diacak ulang terpisah."""
    out = {}
    for layer in spec.layers:
        if layer.enabled:
            notes = generate(arr, layer, random.Random(layer_seed(spec, layer)))
            off = ROLE_FEEL.get(layer.role, 0.0) * (1.0 if arr.tempo < 140 else 0.5)
            for n in notes:
                n.start = max(0.0, n.start + off)
            out[layer.id] = notes
    return out


def audible(spec: SongSpec) -> list[Layer]:
    on = [l for l in spec.layers if l.enabled and not l.mute]
    solos = [l for l in on if l.solo]
    return solos or on


def render_stems(spec: SongSpec, arr: Arrangement, notes: dict, soundfont: Path, max_seconds: float | None = None,
                 log=print) -> dict[str, np.ndarray]:
    dur = arr.duration if max_seconds is None else min(arr.duration, max_seconds)
    data = _sf_bytes(str(soundfont))
    stems = {}
    for layer in audible(spec):
        ins = layer.instrument
        log(f"  render layer '{layer.id}' ({ins.name or ins.preset}, {layer.style}, {len(notes[layer.id])} not)")
        libs = available()
        if ins.lib and ins.lib in libs:
            x = Sampler(load_lib(libs[ins.lib]), layer_seed(spec, layer)).render(notes[layer.id], dur)
        else:
            if ins.lib:
                log(f"    (library '{ins.lib}' belum diunduh, pakai soundfont; jalankan: python -m songgen setup)")
            x = SfInstrument(data, ins.bank, ins.preset, drums=ins.drums).render(notes[layer.id], dur)
        stems[layer.id] = stem_fx(layer.role, x, spec.lofi)
    return stems


# target loudness (RMS saat bunyi) per peran, sebelum volume layer; menyamakan instrumen yang beda level
ROLE_TARGET_DB = {"melody": -24.0, "chords": -29.0, "bass": -27.0, "drums": -30.0, "pad": -33.0}


def active_rms(x: np.ndarray, win: int = 4410) -> float:
    n = len(x) // win * win
    if n == 0:
        return 0.0
    r = np.sqrt((x[:n].reshape(-1, win, x.shape[1]) ** 2).mean(axis=(1, 2)))
    a = r[r > max(1e-4, r.max() * 0.05)]
    return float(np.sqrt((a ** 2).mean())) if len(a) else 0.0


def level(role: str, x: np.ndarray) -> np.ndarray:
    r = active_rms(x)
    if r <= 0:
        return x
    g_db = max(-18.0, min(24.0, ROLE_TARGET_DB.get(role, -28.0) - 20 * np.log10(r)))
    return x * np.float32(10 ** (g_db / 20))


def mix(spec: SongSpec, stems: dict[str, np.ndarray], seed: int = 0) -> np.ndarray:
    n = max(len(x) for x in stems.values())
    dry = np.zeros((n, 2), np.float32)
    send = np.zeros((n, 2), np.float32)
    for layer in audible(spec):
        if layer.id not in stems:
            continue
        x = level(layer.role, stems[layer.id]) * layer.volume
        p = max(-1.0, min(1.0, layer.pan))
        x = x * np.array([min(1.0, 1 - p), min(1.0, 1 + p)], np.float32)   # balance
        dry[: len(x)] += x
        send[: len(x)] += x * layer.reverb
    room = Pedalboard([HighpassFilter(180),
                       Reverb(room_size=0.35 + 0.55 * spec.room, damping=0.45, wet_level=1.0, dry_level=0.0, width=1.0)])
    wet = room(send.T, SR, reset=True).T
    out = dry + wet * 0.7
    rng = np.random.default_rng(seed)
    out = master(out, spec.lofi, rng)
    if spec.lofi > 0:
        out += Vinyl(seed)(len(out), spec.lofi * 0.8)
    # normalisasi kasar ke ~ -16 dBFS RMS lalu limiter (puncak -1 dB)
    rms = float(np.sqrt(np.mean(out ** 2))) or 1.0
    out = out * (10 ** (-16 / 20) / rms)
    lim = StreamLimiter(gain_db=0.0, ceiling_db=-1.0)
    out = np.concatenate([lim(out), lim(np.zeros((0, 2), np.float32), final=True)])
    # fade out pendek di akhir
    f = min(len(out), int(1.5 * SR))
    out[-f:] *= np.linspace(1, 0, f)[:, None]
    return out
