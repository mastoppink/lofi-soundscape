"""Generator per peran. Setiap generator: generate(arr, layer, rng) -> list[Note]."""
from __future__ import annotations

import random

from ..arrangement import Arrangement, Section
from ..song import Layer, Note

# bagian lagu tempat setiap peran bunyi bila layer.sections = None
DEFAULT_SECTIONS = {
    "chords": None, "bass": None, "drums": None, "pad": None,
    "melody": ["head", "solo", "ending", "verse", "chorus", "theme", "climax"],
}

# rentang nada nyaman per instrumen GM (rendah, tinggi)
RANGES = {
    65: (56, 82), 66: (49, 77), 64: (61, 87), 56: (55, 82), 59: (55, 80), 57: (46, 72),
    71: (52, 86), 73: (62, 91), 11: (62, 89), 0: (67, 88), 4: (60, 86), 26: (52, 80), 24: (52, 80),
    40: (57, 91), 41: (52, 84), 42: (40, 72), 60: (45, 74), 68: (60, 86), 74: (62, 91),
}


def active(layer: Layer, sec: Section) -> bool:
    allowed = layer.sections if layer.sections is not None else DEFAULT_SECTIONS.get(layer.role)
    return allowed is None or sec.kind in allowed


def hum(rng: random.Random, t: float, amt: float = 0.008) -> float:
    return max(0.0, t + rng.gauss(0, amt))


def vel(rng: random.Random, base: float, spread: float = 8) -> int:
    return int(max(1, min(127, rng.gauss(base, spread / 2))))


def generate(arr: Arrangement, layer: Layer, rng: random.Random) -> list[Note]:
    from . import bass, chords, drums, melody, pad
    mod = {"chords": chords, "bass": bass, "drums": drums, "melody": melody, "pad": pad}[layer.role]
    notes = mod.generate(arr, layer, rng)
    return [n for n in notes if n.dur > 0.01]
