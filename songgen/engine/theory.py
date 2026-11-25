"""Teori musik: nama nada, kualitas akor, voicing dengan voice leading."""
from __future__ import annotations

NOTE_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
_ALIASES = {"C#": 1, "D#": 3, "F#": 6, "G#": 8, "A#": 10, "Cb": 11, "Fb": 4, "E#": 5, "B#": 0}


def pc_of(name: str) -> int:
    name = name.strip().capitalize() if len(name) == 1 else name[0].upper() + name[1:]
    if name in NOTE_NAMES:
        return NOTE_NAMES.index(name)
    if name in _ALIASES:
        return _ALIASES[name]
    raise ValueError(f"nama nada tidak dikenal: {name}")


# interval dari root. Urutan: root, 3rd, 5th, 7th, tensions
CHORDS = {
    "maj7": [0, 4, 7, 11, 14],
    "6": [0, 4, 7, 9, 14],
    "m7": [0, 3, 7, 10, 14],
    "m6": [0, 3, 7, 9, 14],
    "mMaj7": [0, 3, 7, 11, 14],
    "7": [0, 4, 7, 10, 14],
    "13": [0, 4, 10, 14, 21],
    "7b9": [0, 4, 7, 10, 13],
    "7alt": [0, 4, 10, 13, 20],
    "7#11": [0, 4, 10, 14, 18],
    "m7b5": [0, 3, 6, 10, 14],
    "dim7": [0, 3, 6, 9],
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "sus4": [0, 5, 7],
    "add9": [0, 4, 7, 14],
    "madd9": [0, 3, 7, 14],
}

# skala untuk melodi, per kualitas akor (relatif ke root akor)
CHORD_SCALES = {
    "maj7": [0, 2, 4, 7, 9, 11], "6": [0, 2, 4, 7, 9], "maj": [0, 2, 4, 7, 9], "add9": [0, 2, 4, 7, 9],
    "m7": [0, 2, 3, 5, 7, 10], "m6": [0, 2, 3, 5, 7, 9], "mMaj7": [0, 2, 3, 7, 11], "min": [0, 2, 3, 5, 7, 10],
    "madd9": [0, 2, 3, 5, 7],
    "7": [0, 2, 4, 7, 9, 10], "13": [0, 2, 4, 7, 9, 10], "7#11": [0, 2, 4, 6, 7, 10],
    "7b9": [0, 1, 4, 7, 8, 10], "7alt": [0, 1, 3, 4, 8, 10],
    "m7b5": [0, 3, 5, 6, 10], "dim7": [0, 3, 6, 9], "sus4": [0, 2, 5, 7, 10],
}


def chord_tones(root_pc: int, quality: str) -> list[int]:
    return [(root_pc + i) % 12 for i in CHORDS[quality]]


def guide_tones(root_pc: int, quality: str) -> list[int]:
    """3rd dan 7th (nada yang paling menentukan warna akor)."""
    iv = CHORDS[quality]
    return [(root_pc + iv[1]) % 12, (root_pc + (iv[3] if len(iv) > 3 else iv[2])) % 12]


def voice(root_pc: int, quality: str, prev: list[int] | None, low: int = 50, high: int = 76,
          rootless: bool = True, max_notes: int = 4) -> list[int]:
    """Voicing rapat di register tengah; memilih posisi yang paling dekat ke akor sebelumnya."""
    iv = CHORDS[quality]
    tones = iv[1:] if rootless and len(iv) >= 4 else iv
    tones = tones[:max_notes]
    pcs = [(root_pc + i) % 12 for i in tones]
    best, best_cost = None, 1e9
    for start in range(len(pcs)):              # inversi
        order = pcs[start:] + pcs[:start]
        for base in range(low, low + 12):
            if base % 12 != order[0]:
                continue
            notes, cur = [base], base
            for pc in order[1:]:
                cur += 1
                while cur % 12 != pc:
                    cur += 1
                notes.append(cur)
            if notes[-1] > high or notes[-1] - notes[0] > 14:
                continue
            center = sum(notes) / len(notes)
            cost = abs(center - (low + high) / 2) * 0.4
            if prev:
                cost += sum(min(abs(n - p) for p in prev) for n in notes)
            if cost < best_cost:
                best, best_cost = notes, cost
    if best is None:
        best = sorted(low + (pc - low) % 12 for pc in pcs)
    return best


def nearest(pc: int, target: int, low: int = 0, high: int = 127) -> int:
    """Nada dengan pitch-class pc yang paling dekat ke target."""
    cands = [n for n in range(target - 6, target + 7) if n % 12 == pc and low <= n <= high]
    return min(cands, key=lambda n: abs(n - target)) if cands else target
