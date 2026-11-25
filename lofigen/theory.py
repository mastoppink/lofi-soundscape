"""Teori musik: tangga nada, akor jazzy, progression, voicing."""
from __future__ import annotations

NOTE_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# interval akor relatif terhadap root
CHORDS = {
    "maj7": [0, 4, 7, 11, 14],     # maj9
    "m7": [0, 3, 7, 10, 14],       # m9
    "7": [0, 4, 7, 10, 14],        # 9
    "m7b5": [0, 3, 6, 10],
    "maj7#11": [0, 4, 7, 11, 18],
    "7b9": [0, 4, 7, 10, 13],
    "m11": [0, 3, 7, 10, 17],
}

# derajat (semitone dari tonic) + kualitas akor, untuk mayor & minor
PROGRESSIONS = {
    "major": [
        [(2, "m7"), (7, "7"), (0, "maj7"), (0, "maj7")],          # ii-V-I
        [(0, "maj7"), (9, "m7"), (2, "m7"), (7, "7")],            # I-vi-ii-V
        [(5, "maj7"), (4, "m7"), (2, "m7"), (0, "maj7")],         # IV-iii-ii-I
        [(5, "maj7"), (7, "7"), (4, "m7"), (9, "m7")],            # IV-V-iii-vi
        [(0, "maj7"), (4, "7b9"), (9, "m7"), (5, "maj7#11")],
        [(2, "m7"), (5, "maj7"), (4, "m7"), (9, "m11")],
    ],
    "minor": [
        [(0, "m7"), (5, "m7"), (10, "7"), (3, "maj7")],           # i-iv-VII-III
        [(0, "m11"), (8, "maj7"), (2, "m7b5"), (7, "7b9")],       # i-VI-iiø-V
        [(5, "m7"), (10, "7"), (3, "maj7"), (8, "maj7")],
        [(0, "m7"), (0, "m7"), (8, "maj7"), (7, "7b9")],
        [(8, "maj7"), (7, "7b9"), (0, "m7"), (0, "m11")],
    ],
}

SCALES = {
    "major": [0, 2, 4, 7, 9],          # pentatonik mayor (aman untuk melodi)
    "minor": [0, 3, 5, 7, 10],         # pentatonik minor
}


def voice_chord(root_pc: int, quality: str, prev: list[int] | None, low: int = 50, high: int = 74) -> list[int]:
    """Voicing rapat di register tengah, dengan voice-leading ke akor sebelumnya."""
    ivs = CHORDS[quality]
    # rootless-ish voicing: buang root (bass yang memainkan), pakai sisanya
    tones = [(root_pc + i) % 12 for i in ivs[1:]]
    best, best_cost = None, 1e9
    for base in range(low, low + 12):
        notes = []
        cur = base
        for pc in tones:
            while cur % 12 != pc:
                cur += 1
            notes.append(cur)
            cur += 1
        if notes[-1] > high:
            continue
        center = sum(notes) / len(notes)
        cost = abs(center - 62) * 0.5
        if prev:
            cost += sum(min(abs(n - p) for p in prev) for n in notes)
        if cost < best_cost:
            best, best_cost = notes, cost
    return best or [low + (t - low) % 12 for t in tones]
