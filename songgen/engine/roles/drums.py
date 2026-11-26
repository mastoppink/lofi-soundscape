"""Peran drum jazz: ride (spang-a-lang), brush, sparse."""
from __future__ import annotations

from ..song import Note
from . import active, hum, vel

KICK, STICK, SNARE, BR_SLAP, BR_SWIRL, CLHAT, HH_PEDAL, HH_OPEN, CRASH, RIDE, RIDE_BELL = 36, 37, 38, 39, 40, 42, 44, 46, 49, 51, 53
BR_TAP = 38


def generate(arr, layer, rng):
    notes = []
    style = layer.style if layer.style != "auto" else "ride"
    bpb = arr.beats_per_bar
    bs = arr.beat_sec

    def hit(beat, key, v, dur=0.25, amt=0.006):
        notes.append(Note(hum(rng, arr.time(beat), amt), dur, key, max(1, min(127, int(v)))))

    for sec in arr.sections:
        if not active(layer, sec):
            continue
        it = sec.intensity
        last_sec = sec is arr.sections[-1]
        if sec.kind != "intro" and sec.label in ("A", "B", "E") and sec.start_bar > 0 and style not in ("sparse", "soft"):
            prev_sec = arr.section_at_bar(sec.start_bar - 1)
            if prev_sec.kind != sec.kind or sec.label == "B":
                hit(sec.start_bar * bpb, CRASH, 55 + 30 * it, 2.0)
                hit(sec.start_bar * bpb, KICK, 55 + 30 * it)
        for bar in range(sec.start_bar, sec.end_bar):
            b0 = bar * bpb
            if last_sec and bar >= sec.end_bar - 2:
                if bar == sec.end_bar - 2:          # pukulan penutup
                    hit(b0, CRASH, 45 if style == "soft" else 70, 4.0)
                    hit(b0, KICK, 50 if style == "soft" else 75)
                    if style == "brush":
                        hit(b0, BR_SWIRL, 50, 4 * bs)
                continue
            phrase_end = (bar - sec.start_bar) == sec.bars - 1
            fill = phrase_end and rng.random() < 0.35 + 0.4 * layer.density * it
            if style == "soft":
                # ballad tenang: hi-hat lembut, cross-stick di ketukan 4, kick halus; tanpa ride terus-menerus
                for b in range(bpb):
                    hit(b0 + b, CLHAT, 22 + 14 * it + (6 if b % 2 else 0), 0.3)
                    if b % 2 == 1:
                        hit(b0 + b, HH_PEDAL, 30 + 10 * it)
                    if rng.random() < 0.2 * layer.density:
                        hit(b0 + b + 0.5, CLHAT, 16 + 10 * it, 0.2)
                if rng.random() < 0.8:
                    hit(b0 + 3, STICK, 30 + 20 * it)
                if rng.random() < 0.5:
                    hit(b0, KICK, 22 + 12 * it)
                if (bar - sec.start_bar) % 8 == 0 and bar > 0 and rng.random() < 0.5:
                    hit(b0, RIDE, 30 + 10 * it, 1.5)   # sesekali, sangat pelan
            elif style == "ride" or style == "sparse":
                for b in range(bpb):
                    hit(b0 + b, RIDE, 55 + 25 * it + (8 if b % 2 else 0), 1.0)
                    if b % 2 == 1 and style == "ride" and rng.random() < 0.9:
                        hit(b0 + b + 0.5, RIDE, 40 + 20 * it, 0.5)   # 'skip' note
                    if b % 2 == 1:
                        hit(b0 + b, HH_PEDAL, 50 + 15 * it)
                    if style == "ride" and rng.random() < 0.6:
                        hit(b0 + b, KICK, 18 + 10 * it)            # feathering
                if style == "ride" and not fill:
                    # comping snare/kick acak di swung 8th
                    n = int((0.5 + 2.5 * layer.density) * it + rng.random())
                    for _ in range(n):
                        pos = rng.choice([0.5, 1.5, 2, 2.5, 3, 3.5, 1])
                        if rng.random() < 0.75:
                            hit(b0 + pos, SNARE, 30 + 35 * it * rng.uniform(0.6, 1.2))
                        else:
                            hit(b0 + pos, KICK, 45 + 30 * it)
            elif style == "brush":
                hit(b0, BR_SWIRL, 30 + 20 * it, 2 * bs, 0.004)
                hit(b0 + 2, BR_SWIRL, 30 + 20 * it, 2 * bs, 0.004)
                for b in range(bpb):
                    hit(b0 + b, BR_TAP, 40 + 25 * it + (12 if b % 2 else 0))
                    if b % 2 == 1:
                        hit(b0 + b, BR_SLAP, 30 + 30 * it)
                        hit(b0 + b, HH_PEDAL, 45 + 10 * it)
                    if rng.random() < 0.5 + 0.4 * layer.density:
                        hit(b0 + b + 0.5, BR_TAP, 28 + 18 * it)
                    if rng.random() < 0.35:
                        hit(b0 + b, KICK, 25 + 15 * it)
            if fill:
                start = 2 if rng.random() < 0.6 else 3
                pos = start
                while pos < bpb - 0.01:
                    k = SNARE if style != "brush" else BR_SLAP
                    hit(b0 + pos, k, 45 + 40 * it * (pos / bpb) + rng.uniform(-5, 5))
                    pos += rng.choice([1 / 3, 0.5]) if it > 0.5 else 0.5
                if style == "ride":
                    hit(b0 + 3.5, KICK, 60 + 25 * it)
    return notes
