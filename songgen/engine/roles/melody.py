"""Peran melodi: disusun seperti penulis lagu.

1. Ritme dari pustaka pola 2-bar (dipilih sesuai kepadatan), disusun jadi frasa 4 bar tanya-jawab.
2. Kerangka: setiap nada kuat (ketukan 1/3 atau nada panjang) = nada akor, bergerak sedekat mungkin
   dari nada sebelumnya, mengikuti kontur melengkung (naik ke puncak lalu turun ke kadens).
3. Isian: nada lemah hanya boleh nada lewat (melangkah di skala akor) atau nada tetangga/approach
   yang langsung selesai ke nada kerangka berikutnya.
4. Tema head ditulis sekali dan diulang; motif diulang/digeser mengikuti akor.
"""
from __future__ import annotations

import math

from ..song import Note
from ..theory import CHORD_SCALES, CHORDS
from . import RANGES, active, hum, vel

# pola ritme 2 bar: (posisi ketukan, panjang). Selalu ada ruang napas di akhir.
RHYTHMS = {
    "sparse": [
        [(0, 2), (2, 1), (3, 1), (4, 3)],
        [(0.5, 1.5), (2, 2), (4, 1), (5, 2)],
        [(0, 1), (1, 1), (2, 2), (4, 3.5)],
        [(0, 3), (3, 1), (4, 3)],
        [(1, 1), (2, 1), (3, 1), (4, 3)],
    ],
    "medium": [
        [(0, 1), (1, 0.5), (1.5, 1.5), (3.5, 0.5), (4, 3)],
        [(0.5, 0.5), (1, 0.5), (1.5, 1), (2.5, 0.5), (3, 1), (4, 2.5)],
        [(0, 1.5), (1.5, 0.5), (2, 1), (3, 1), (4, 1.5), (5.5, 0.5), (6, 1.5)],
        [(1, 0.5), (1.5, 0.5), (2, 0.5), (2.5, 1.5), (4, 0.5), (4.5, 0.5), (5, 2)],
        [(0, 0.5), (0.5, 1), (1.5, 0.5), (2, 2), (4, 1), (5, 0.5), (5.5, 1.5)],
    ],
    "dense": [
        [(0, .5), (.5, .5), (1, .5), (1.5, .5), (2, 1), (3, .5), (3.5, .5), (4, .5), (4.5, .5), (5, 1.5)],
        [(.5, .5), (1, .5), (1.5, .5), (2, .5), (2.5, .5), (3, 1), (4, .5), (4.5, .5), (5, .5), (5.5, 1.5)],
        [(0, 1), (1, .5), (1.5, .5), (2, .5), (2.5, .5), (3, .5), (3.5, .5), (4, 2), (6, .5), (6.5, .5)],
        [(1, .5), (1.5, .5), (2, .5), (2.5, .5), (3, .5), (3.5, .5), (4, 1), (5, .5), (5.5, 1.5)],
    ],
}


def _pcs(c, scale=True):
    s = {(c.root + i) % 12 for i in CHORDS[c.quality]}
    if scale:
        s |= {(c.root + i) % 12 for i in CHORD_SCALES[c.quality]}
    return s


def _in_range(pcs, lo, hi):
    return [n for n in range(lo, hi + 1) if n % 12 in pcs]


def _strong(pos, ln):
    return (abs(pos - round(pos)) < 1e-6 and int(round(pos)) % 2 == 0) or ln >= 1.5


def _skeleton_pick(arr, beat, prev, target, lo, hi, rng, cadence=False):
    c = arr.chord_at(beat)
    iv = CHORDS[c.quality]
    tones = _in_range({(c.root + i) % 12 for i in iv}, lo, hi)
    if cadence:
        # akhir frasa: root/3rd/5th (stabil)
        stable = _in_range({(c.root + i) % 12 for i in iv[:3]}, lo, hi)
        tones = stable or tones
    color = {(c.root + i) % 12 for i in iv[1:2] + iv[3:]}  # 3rd, 7th, tension
    best, bc = None, 1e9
    for t in tones:
        move = abs(t - prev) if prev is not None else 0
        cost = move * 1.0 + abs(t - target) * 0.55 + (0 if (t % 12) in color or cadence else 0.6)
        if move > 7:
            cost += (move - 7) * 3
        if prev is not None and t == prev:
            cost += 1.2  # hindari nada sama terus
        cost += rng.random() * 0.8
        if cost < bc:
            best, bc = t, cost
    return best if best is not None else (prev or (lo + hi) // 2)


def _scale_path(arr, beat, a, b, k, lo, hi, rng):
    """k nada lemah dari a menuju b: lewat (melangkah) atau tetangga/approach."""
    if k <= 0:
        return []
    out = []
    c = arr.chord_at(beat)
    sc = sorted(_in_range(_pcs(c), lo - 2, hi + 2))
    if b is None:
        b = a
    direction = 1 if b > a else -1 if b < a else rng.choice([-1, 1])
    between = [n for n in sc if (a < n < b) or (b < n < a)]
    if direction < 0:
        between = between[::-1]
    if len(between) >= k:
        # ambil langkah yang tersebar rata
        idx = [round((i + 1) * len(between) / (k + 1)) - 1 for i in range(k)]
        out = [between[max(0, min(len(between) - 1, j))] for j in idx]
    else:
        cur = a
        for i in range(k):
            last = i == k - 1
            if last:
                # approach ke b: nada skala tepat di atas/bawah b, atau kromatik dari bawah
                above = [n for n in sc if n > b]
                below = [n for n in sc if n < b]
                opts = ([min(above)] if above else []) + ([max(below)] if below else []) + [b - 1]
                cur = rng.choice(opts)
            else:
                nb = [n for n in sc if 0 < abs(n - cur) <= 2]
                cur = rng.choice(nb) if nb else cur
            out.append(cur)
    return out


def _line(arr, start_beat, rhythm, rng, lo, hi, prev, contour, cadence_last, template=None):
    """Menyusun satu potong 2 bar. contour(x in 0..1) -> nada target. template: nada kerangka motif
    yang diulang (digeser) supaya ada identitas."""
    notes = []
    strong_idx = [i for i, (p, l) in enumerate(rhythm) if _strong(p, l)]
    if not strong_idx:
        strong_idx = [0]
    sk = {}
    shift = None
    for j, i in enumerate(strong_idx):
        p, l = rhythm[i]
        beat = start_beat + p
        target = contour(p / 8)
        if template is not None and j < len(template):
            if shift is None:
                first = _skeleton_pick(arr, beat, prev, template[0], lo, hi, rng)
                shift = first - template[0]
            target = template[j] + shift
            prev_for = target
        else:
            prev_for = prev
        cad = cadence_last and i == strong_idx[-1]
        pitch = _skeleton_pick(arr, beat, prev_for if prev_for is not None else prev, target, lo, hi, rng, cad)
        sk[i] = pitch
        prev = pitch
    # isi nada lemah di antara kerangka
    order = sorted(sk)
    pitches = [None] * len(rhythm)
    for i in order:
        pitches[i] = sk[i]
    # sebelum kerangka pertama (pickup)
    first = order[0]
    if first > 0:
        path = _scale_path(arr, start_beat + rhythm[0][0], sk[first] + rng.choice([-3, -2, 2, 3]), sk[first], first, lo, hi, rng)
        for k in range(first):
            pitches[k] = path[k]
    for a, b in zip(order, order[1:]):
        k = b - a - 1
        path = _scale_path(arr, start_beat + rhythm[a + 1][0], sk[a], sk[b], k, lo, hi, rng)
        for m in range(k):
            pitches[a + 1 + m] = path[m]
    last = order[-1]
    if last < len(rhythm) - 1:
        k = len(rhythm) - 1 - last
        # setelah kerangka terakhir: turun pelan (jawaban)
        path = _scale_path(arr, start_beat + rhythm[last + 1][0], sk[last], sk[last] - rng.choice([2, 3, 4]), k, lo, hi, rng)
        for m in range(k):
            pitches[last + 1 + m] = path[m]
    for (p, l), n in zip(rhythm, pitches):
        notes.append((p, l, max(lo - 2, min(hi + 2, n)), (p, l) in [rhythm[i] for i in sk]))
    return notes, [sk[i] for i in order]


def _section_melody(arr, sec, rng, lo, hi, density, peak_shift=0):
    """Melodi 1 bagian (biasanya 8 bar): frasa 4 bar tanya-jawab, motif diulang."""
    tier = "sparse" if density < 0.35 or arr.tempo < 80 else "dense" if density > 0.75 else "medium"
    lib = RHYTHMS[tier]
    motif_r = rng.choice(lib)
    answer_r = rng.choice([r for r in lib if r is not motif_r] or lib)
    cadence_r = rng.choice(RHYTHMS["sparse"])
    center = (lo + hi) / 2
    span = (hi - lo) / 2
    out = []
    prev = int(center - 2)
    motif_sk = None
    units = sec.bars // 2
    b0 = sec.start_bar * arr.beats_per_bar
    for u in range(units):
        # kontur: naik di tengah bagian (puncak sekitar 60%), turun ke akhir
        def contour(x, u=u):
            pos = (u + x) / units
            arch = math.sin(math.pi * min(1, pos / 0.62) / 2) if pos < 0.62 else math.cos(math.pi * (pos - 0.62) / 0.76)
            return center - span * 0.55 + span * (1.05 + peak_shift) * arch
        last_unit = u == units - 1
        if u % 2 == 0:
            r, tmpl = motif_r, (motif_sk if u > 0 else None)
        else:
            r, tmpl = (cadence_r if last_unit else answer_r), None
        notes, skel = _line(arr, b0 + u * 8, r, rng, lo, hi, prev, contour, cadence_last=(u % 2 == 1), template=tmpl)
        if u == 0:
            motif_sk = skel
        for p, l, n, strong in notes:
            out.append((u * 8 + p, l, n, strong))
        prev = notes[-1][2]
    return out


def generate(arr, layer, rng):
    notes = []
    style = layer.style if layer.style not in ("auto", "ai") else "head+solo"
    lo, hi = RANGES.get(layer.instrument.preset, (55, 84))
    lo, hi = lo + 12 * layer.octave, hi + 12 * layer.octave
    hi = min(hi, lo + 17)          # rentang nyanyi: ±1,5 oktaf
    bpb = arr.beats_per_bar
    themes = {}
    for sec in arr.sections:
        if not active(layer, sec):
            continue
        b0 = sec.start_bar * bpb
        if sec.kind == "ending":
            c = arr.chord_at(b0 + (sec.bars - 2) * bpb)
            iv = CHORDS[c.quality]
            n = min(_in_range({(c.root + iv[1]) % 12, c.root % 12}, lo, hi), key=lambda x: abs(x - (lo + hi) / 2), default=lo + 5)
            notes.append(Note(arr.time(b0 + (sec.bars - 2) * bpb), 6 * arr.beat_sec, n, vel(rng, 60)))
            continue
        if style in ("head", "head+solo") and sec.kind in ("head", "theme", "verse", "chorus"):
            if sec.label not in themes:
                themes[sec.label] = _section_melody(arr, sec, rng, lo, hi, layer.density,
                                                    peak_shift=0.15 if sec.label == "B" else 0)
            phrase, base = themes[sec.label], 64
        elif style in ("solo", "head+solo") and sec.kind in ("solo", "climax"):
            dens = min(1.0, layer.density + 0.25 + 0.2 * sec.intensity)
            phrase, base = _section_melody(arr, sec, rng, lo, hi, dens, peak_shift=0.1 * sec.intensity), 66
        elif style == "fills":
            phrase = [(p, l, n, s) for p, l, n, s in _section_melody(arr, sec, rng, lo, hi, 0.3)
                      if int(p // 8) % 2 == 1]
            base = 54
        else:
            continue
        center = (lo + hi) / 2
        for p, l, n, strong in phrase:
            beat = b0 + p
            v = base + 18 * sec.intensity + (n - center) * 0.8 + (5 if strong else -4)
            dur = l * arr.beat_sec * (0.97 if l >= 1 else 0.88)
            notes.append(Note(hum(rng, arr.time(beat), 0.008), dur, n, vel(rng, v, 6)))
    return notes
