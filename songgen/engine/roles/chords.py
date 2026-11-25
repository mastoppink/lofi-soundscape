"""Peran akor: comping piano/gitar jazz, ballad, stabs, sustain."""
from __future__ import annotations

from ..song import Note
from ..theory import voice
from . import active, hum, vel

# pola comping dalam 1 bar: (posisi ketukan, panjang ketukan). Tingkat kepadatan naik.
COMP = [
    [[(0, 1.5)], [(1.5, 1.2)], [(0, 3.5)]],                               # jarang
    [[(0, 1.2), (1.5, 0.8)], [(1.5, 1.0), (3.5, 0.4)], [(0, 0.7), (2.5, 1.2)],
     [(1, 0.6), (2.5, 1.0)], [(0.5, 1.0), (2.5, 0.8)]],                    # sedang (Charleston dkk.)
    [[(0, 0.5), (1.5, 0.5), (2.5, 0.4), (3.5, 0.4)], [(0.5, 0.4), (1.5, 0.4), (3, 0.8)],
     [(0, 1.0), (1.5, 0.4), (2.5, 0.4), (3.5, 0.4)]],                     # ramai
]


def generate(arr, layer, rng):
    notes = []
    style = layer.style if layer.style != "auto" else "comping"
    lo, hi = 48 + 12 * layer.octave, 67 + 12 * layer.octave
    prev = None
    bpb = arr.beats_per_bar
    for sec in arr.sections:
        if not active(layer, sec):
            continue
        last_sec = sec is arr.sections[-1]
        for bar in range(sec.start_bar, sec.end_bar):
            b0 = bar * bpb
            final = last_sec and bar >= sec.end_bar - 2
            if final:
                # akor penutup: digulung pelan dan ditahan
                if bar == sec.end_bar - 2:
                    c = arr.chord_at(b0)
                    v = voice(c.root, c.quality, prev, lo, hi, max_notes=5)
                    for i, n in enumerate(v):
                        notes.append(Note(arr.time(b0) + i * 0.045, 8 * arr.beat_sec, n, vel(rng, 58)))
                continue
            if style in ("ballad", "sustain"):
                hits = []
                pos = 0.0
                for c in [x for x in arr.chords if b0 <= x.start < b0 + bpb]:
                    hits.append((c.start - b0, c.beats))
                if style == "ballad" and rng.random() < layer.density * 0.6:
                    hits.append((rng.choice([1.5, 2.5, 3.5]), 0.9))  # isian kecil
                roll = 0.03 if style == "ballad" else 0.0
            elif style == "stabs":
                hits = [(1, 0.35), (3, 0.35)] if rng.random() > layer.density * 0.5 else [(1, 0.35), (2.5, 0.3), (3, 0.35)]
                roll = 0.006
            else:  # comping
                d = layer.density * 0.6 + sec.intensity * 0.4
                tier = 0 if d < 0.38 else 1 if d < 0.72 else 2
                if rng.random() < 0.25:
                    tier = max(0, min(2, tier + rng.choice([-1, 1])))
                hits = rng.choice(COMP[tier])
                roll = 0.012
            for pos, length in hits:
                beat = b0 + pos
                # antisipasi: hit di off-beat terakhir memakai akor bar berikutnya
                c = arr.chord_at(beat + (0.5 if pos % 1 == 0.5 and pos >= 3.5 else 0))
                v = voice(c.root, c.quality, prev, lo, hi)
                prev = v
                st = arr.time(beat)
                base = 40 + 35 * sec.intensity + (8 if pos % 1 == 0.5 else 0)
                dur = length * arr.beat_sec * (0.98 if style in ("ballad", "sustain") else 0.85)
                for i, n in enumerate(v):
                    notes.append(Note(hum(rng, st + i * roll * rng.uniform(0.3, 1.2), 0.006), dur, n, vel(rng, base, 10)))
    return notes
