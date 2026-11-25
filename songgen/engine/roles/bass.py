"""Peran bass: walking bass, two-feel, pedal."""
from __future__ import annotations

from ..song import Note
from ..theory import CHORD_SCALES, CHORDS, nearest
from . import active, hum, vel

LO, HI = 28, 52


def _near(pc, prev, lo, hi):
    return nearest(pc, prev if prev else 38, lo, hi)


def _walk_step(arr, c, prev, target, rng, lo, hi):
    """Nada di tengah: chord tone / nada skala, bergerak menuju target."""
    pcs = {(c.root + i) % 12 for i in CHORDS[c.quality][:4]} | {(c.root + i) % 12 for i in CHORD_SCALES[c.quality]}
    cands = [n for n in range(max(lo, prev - 7), min(hi, prev + 7) + 1) if n % 12 in pcs and n != prev]
    if not cands:
        return prev
    direction = 1 if target > prev else -1
    good = [n for n in cands if (n - prev) * direction > 0 and abs(n - prev) <= 4] or cands
    # hindari menabrak target terlalu awal
    good = [n for n in good if n != target] or good
    return rng.choice(good)


def generate(arr, layer, rng):
    notes = []
    style = layer.style if layer.style != "auto" else "walking"
    lo, hi = LO + 12 * layer.octave, HI + 12 * layer.octave
    prev = None
    bpb = arr.beats_per_bar
    for sec in arr.sections:
        if not active(layer, sec):
            continue
        sty = style
        if sec.kind == "intro" and style == "walking":
            sty = "two"
        last_sec = sec is arr.sections[-1]
        for bar in range(sec.start_bar, sec.end_bar):
            b0 = bar * bpb
            if last_sec and bar >= sec.end_bar - 2:
                if bar == sec.end_bar - 2:
                    c = arr.chord_at(b0)
                    n = _near(c.root, prev, lo, hi)
                    notes.append(Note(arr.time(b0), 7 * arr.beat_sec, n, vel(rng, 95)))
                continue
            if sty == "pedal":
                c = arr.chord_at(b0)
                n = _near(arr.key_pc if c.root != (arr.key_pc + 7) % 12 else c.root, prev, lo, hi)
                notes.append(Note(hum(rng, arr.time(b0)), bpb * arr.beat_sec * 0.95, n, vel(rng, 85)))
                prev = n
                continue
            beats = range(bpb) if sty == "walking" else range(0, bpb, 2)
            step = 1 if sty == "walking" else 2
            for b in beats:
                beat = b0 + b
                c = arr.chord_at(beat)
                nxt = arr.chord_at(beat + step)
                if abs(c.start - beat) < 1e-6:                      # awal akor -> root
                    n = _near(c.root, prev, lo, hi)
                elif nxt.start <= beat + step + 1e-6 and nxt is not c:  # sebelum akor baru -> approach
                    tgt = _near(nxt.root, prev, lo, hi)
                    r = rng.random()
                    if r < 0.55:
                        n = tgt + rng.choice([-1, 1])               # kromatik
                    elif r < 0.8:
                        n = _near((nxt.root + 7) % 12, prev, lo, hi)  # dominan dari target
                    else:
                        n = _walk_step(arr, c, prev, tgt, rng, lo, hi)
                    n = max(lo, min(hi, n))
                else:
                    if sty == "two":
                        n = _near((c.root + 7) % 12, prev, lo, hi)
                    else:
                        tgt = _near(nxt.root, prev, lo, hi)
                        n = _walk_step(arr, c, prev or 38, tgt, rng, lo, hi)
                acc = 6 if b in (0, 2) else 0
                notes.append(Note(hum(rng, arr.time(beat), 0.005), step * arr.beat_sec * 0.9, n,
                                  vel(rng, 78 + 14 * sec.intensity + acc, 10)))
                # ghost note / skip (8th triplet feel) sesekali
                if sty == "walking" and rng.random() < 0.06 * (0.5 + layer.density):
                    gn = n + rng.choice([-2, -1, 1, 2])
                    notes.append(Note(arr.time(beat + 0.5), arr.beat_sec * 0.3, max(lo, min(hi, gn)), vel(rng, 55)))
                prev = n
    return notes
