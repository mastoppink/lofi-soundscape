"""Peran pad: akor panjang lembut (strings / pad)."""
from __future__ import annotations

from ..song import Note
from ..theory import voice
from . import active, vel


def generate(arr, layer, rng):
    notes = []
    lo, hi = 53 + 12 * layer.octave, 79 + 12 * layer.octave
    prev = None
    for sec in arr.sections:
        if not active(layer, sec):
            continue
        b_start, b_end = sec.start_bar * arr.beats_per_bar, sec.end_bar * arr.beats_per_bar
        for c in [x for x in arr.chords if b_start <= x.start < b_end]:
            v = voice(c.root, c.quality, prev, lo, hi, rootless=False, max_notes=4)
            prev = v
            st, en = arr.time(c.start, False), arr.time(c.end, False)
            if sec is arr.sections[-1]:
                en += 3.0
            base = 30 + 40 * sec.intensity * (0.6 + 0.4 * layer.density)
            for n in v:
                notes.append(Note(st + rng.uniform(0, 0.04), en - st + 0.05, n, vel(rng, base, 6)))
    return notes
