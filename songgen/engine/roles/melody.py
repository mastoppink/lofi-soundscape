"""Peran melodi: tema (head) berbasis motif yang diulang, improvisasi (solo), dan isian (fills)."""
from __future__ import annotations

from ..song import Note
from ..theory import CHORD_SCALES, CHORDS
from . import RANGES, active, hum, vel


def _scale(c, lo, hi):
    pcs = {(c.root + i) % 12 for i in CHORD_SCALES[c.quality]}
    return [n for n in range(lo, hi + 1) if n % 12 in pcs]


def _tones(c, lo, hi, guide=False):
    iv = CHORDS[c.quality]
    sel = [iv[1], iv[3] if len(iv) > 3 else iv[2]] if guide else iv[1:]
    pcs = {(c.root + i) % 12 for i in sel}
    return [n for n in range(lo, hi + 1) if n % 12 in pcs]


def _closest(cands, x):
    return min(cands, key=lambda n: abs(n - x)) if cands else x


def _step(arr, beat, note, k, lo, hi):
    sc = _scale(arr.chord_at(beat), lo, hi)
    if not sc:
        return note
    i = min(range(len(sc)), key=lambda j: abs(sc[j] - note))
    return sc[max(0, min(len(sc) - 1, i + k))]


def _motif_rhythm(rng, density):
    """Ritme motif 2 bar (8 ketukan): daftar (posisi, panjang)."""
    pos = rng.choice([0.0, 0.5, 1.0, 0.0])
    out = []
    n_target = int(3 + density * 4 + rng.random() * 2)
    while pos < 6.5 and len(out) < n_target:
        ln = rng.choice([0.5, 0.5, 1.0, 1.0, 1.5, 2.0] if density < 0.6 else [0.5, 0.5, 0.5, 1.0, 1.5])
        out.append((pos, ln))
        pos += ln
    # nada terakhir motif ditahan
    p, _ = out[-1]
    out[-1] = (p, max(1.5, min(8 - p, 3.0)))
    return out


def _head_phrase(arr, sec, rng, lo, hi, density):
    """Membuat melodi tema untuk satu frasa (8 bar). Hasil: (ketukan relatif, panjang, nada)."""
    b0 = sec.start_bar * arr.beats_per_bar
    rhythm = _motif_rhythm(rng, density)
    steps = [rng.choice([-2, -1, -1, 1, 1, 2, 3, -3]) for _ in rhythm]
    center = (lo + hi) // 2
    out = []
    n_units = sec.bars // 2
    note = _closest(_tones(arr.chord_at(b0), lo, hi, True), center + rng.randint(-2, 4))
    for u in range(n_units):
        ub = u * 8
        rh = list(rhythm)
        last_unit = u == n_units - 1
        if u % 2 == 1:
            # variasi: buang 1 nada / geser, akhiri lebih awal untuk 'bernapas'
            if len(rh) > 3 and rng.random() < 0.6:
                rh.pop(rng.randrange(1, len(rh) - 1))
            p, _ = rh[-1]
            rh[-1] = (p, max(1.0, min(6.5 - p, 2.5)))
        if last_unit:
            # kadens: lebih sedikit nada, nada akhir panjang di nada stabil
            rh = rh[: max(2, len(rh) - 2)]
            p, _ = rh[-1]
            rh[-1] = (p, max(2.0, 7.5 - p))
        # sekuens: motif dimulai dari chord tone akor saat ini, pola interval sama
        start_beat = b0 + ub + rh[0][0]
        note = _closest(_tones(arr.chord_at(start_beat), lo, hi), note + rng.choice([-2, 0, 2]))
        for i, (p, ln) in enumerate(rh):
            beat = b0 + ub + p
            if i > 0:
                note = _step(arr, beat, note, steps[i], lo, hi)
            strong = abs(p - round(p)) < 1e-6 and int(round(p)) % 2 == 0
            c = arr.chord_at(beat)
            if strong or i == len(rh) - 1:
                note = _closest(_tones(c, lo, hi, guide=(i == len(rh) - 1)), note)
            if note > hi - 2:
                note -= 12 if note - 12 >= lo else 0
            if note < lo + 2:
                note += 12 if note + 12 <= hi else 0
            out.append((ub + p, ln, note))
    return out


def _solo_bar(arr, b0, state, rng, lo, hi, density, inten):
    """Improvisasi: frasa 8th-note dengan chord tone di ketukan, approach kromatik, jeda napas."""
    out = []
    pos = 0.0
    while pos < 4 - 1e-6:
        if state["rest"] > 0:
            take = min(state["rest"], 4 - pos)
            state["rest"] -= take
            pos += take
            continue
        if state["left"] <= 0:
            state["left"] = rng.uniform(3, 6 + 6 * density)
            state["dir"] = rng.choice([-1, 1])
        triplet = inten > 0.7 and rng.random() < 0.12 * density and abs(pos % 1) < 1e-6
        subdiv = [1 / 3] * 3 if triplet else [0.5] if rng.random() < 0.55 + 0.4 * density else [1.0]
        for ln in subdiv:
            beat = b0 + pos
            c = arr.chord_at(beat)
            note = state["note"]
            on_beat = abs(pos - round(pos)) < 1e-6
            if on_beat:
                note = _closest(_tones(c, lo, hi), note + state["dir"] * rng.choice([1, 2, 3]))
            elif rng.random() < 0.18:
                # approach kromatik ke chord tone berikutnya
                nxt = _closest(_tones(arr.chord_at(beat + 0.5), lo, hi), note + state["dir"] * 2)
                note = nxt + rng.choice([-1, 1])
            elif rng.random() < 0.1:
                note = _step(arr, beat, note, state["dir"] * rng.choice([3, 4]), lo, hi)   # lompatan
            else:
                note = _step(arr, beat, note, state["dir"] * rng.choice([1, 1, 2]), lo, hi)
            if note >= hi - 1 or note <= lo + 1:
                state["dir"] *= -1
            if rng.random() < 0.15:
                state["dir"] *= -1
            note = max(lo, min(hi, note))
            accent = 8 if not on_beat else 0
            v = 55 + 30 * inten + accent + 10 * (state["left"] / 8)
            out.append((pos, ln * 0.95, note, v))
            state["note"] = note
            pos += ln
            state["left"] -= ln
        if state["left"] <= 0:
            # akhiri frasa dengan nada panjang, lalu istirahat
            if out:
                p, l, n, v = out[-1]
                out[-1] = (p, l + 0.5, _closest(_tones(arr.chord_at(b0 + p), lo, hi), n), v)
            state["rest"] = rng.choice([1.0, 1.5, 2.0, 2.5, 4.0]) * (1.3 - density * 0.6)
    return out


def generate(arr, layer, rng):
    notes = []
    style = layer.style if layer.style != "auto" else "head+solo"
    lo, hi = RANGES.get(layer.instrument.preset, (55, 84))
    lo, hi = lo + 12 * layer.octave, hi + 12 * layer.octave
    bpb = arr.beats_per_bar
    themes = {}
    solo_state = {"note": (lo + hi) // 2, "dir": 1, "left": 0.0, "rest": 0.0}
    for sec in arr.sections:
        if not active(layer, sec):
            continue
        b0 = sec.start_bar * bpb
        kind = sec.kind
        mode = None
        if kind == "ending":
            c = arr.chord_at(b0 + (sec.bars - 2) * bpb)
            # dua bar pertama: sisa frasa singkat; lalu nada panjang penutup
            n = _closest(_tones(c, lo, hi), (lo + hi) // 2 + 3)
            notes.append(Note(arr.time(b0 + (sec.bars - 2) * bpb), 6 * arr.beat_sec, n, vel(rng, 62)))
            continue
        if style in ("head", "head+solo") and kind in ("head", "theme", "verse", "chorus"):
            mode = "head"
        elif style in ("solo", "head+solo") and kind in ("solo", "head", "climax"):
            mode = "solo"
        elif style == "fills":
            mode = "fills"
        if mode is None:
            continue
        if mode == "head":
            key = sec.label
            if key not in themes:
                themes[key] = _head_phrase(arr, sec, rng, lo, hi, layer.density)
            for rel, ln, n in themes[key]:
                beat = b0 + rel
                v = 62 + 22 * sec.intensity + rng.uniform(-6, 6)
                notes.append(Note(hum(rng, arr.time(beat), 0.012), ln * arr.beat_sec * 0.96, n, int(v)))
        elif mode == "solo":
            for bar in range(sec.start_bar, sec.end_bar):
                for p, ln, n, v in _solo_bar(arr, bar * bpb, solo_state, rng, lo, hi, layer.density, sec.intensity):
                    notes.append(Note(hum(rng, arr.time(bar * bpb + p), 0.008), ln * arr.beat_sec, n, vel(rng, v, 8)))
        elif mode == "fills":
            for bar in range(sec.start_bar, sec.end_bar):
                if (bar - sec.start_bar) % 4 == 3 and rng.random() < 0.5 + 0.5 * layer.density:
                    st = {"note": (lo + hi) // 2, "dir": rng.choice([-1, 1]), "left": 2.5, "rest": 1.0}
                    for p, ln, n, v in _solo_bar(arr, bar * bpb, st, rng, lo, hi, 0.5, sec.intensity * 0.8):
                        notes.append(Note(hum(rng, arr.time(bar * bpb + p)), ln * arr.beat_sec, n, vel(rng, v - 10, 8)))
    return notes
