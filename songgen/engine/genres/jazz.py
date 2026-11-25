"""Genre jazz: bentuk AABA 32 bar, head - solo - head, progresi ii-V-I, swing."""
from __future__ import annotations

import random

from ..arrangement import Arrangement, Section, add_phrase, parse_phrase
from ..song import Instrument, Layer, SongSpec
from ..theory import pc_of

NAME = "jazz"
LABEL = "Jazz"

# gaya yang tersedia per peran (pertama = bawaan "auto")
STYLES = {
    "chords": ["comping", "ballad", "stabs", "sustain"],
    "bass": ["walking", "two", "pedal"],
    "drums": ["ride", "brush", "sparse"],
    "melody": ["head+solo", "head", "solo", "fills"],
    "pad": ["sustain", "swell"],
}

INSTRUMENTS = {
    "chords": [(0, "Grand Piano"), (4, "Rhodes"), (11, "Vibraphone"), (26, "Jazz Guitar")],
    "bass": [(32, "Acoustic Bass"), (33, "Finger Bass")],
    "drums": [(32, "Jazz Kit"), (40, "Brush Kit"), (8, "Room Kit")],
    "melody": [(66, "Tenor Sax"), (65, "Alto Sax"), (56, "Trumpet"), (59, "Muted Trumpet"),
               (11, "Vibraphone"), (73, "Flute"), (71, "Clarinet"), (0, "Grand Piano")],
    "pad": [(49, "Slow Strings"), (48, "Strings"), (89, "Warm Pad")],
}

# ---- harmoni (derajat relatif ke tonika) ----
A_MAJOR = [
    "I:maj7 | vi:m7 | ii:m7 | V:7 | iii:m7 | VI:7 | ii:m7 | ii:m7/2 V:7/2",
    "I:maj7 | IV:7#11 | iii:m7 | VI:7b9 | ii:m7 | V:7 | I:6 | ii:m7/2 V:7/2",
    "ii:m7 | V:7 | I:maj7 | I:6 | v:m7 | I:7 | IV:maj7 | iv:m7/2 bVII:7/2",
    "I:maj7 | #I:dim7 | ii:m7 | V:7 | iii:m7/2 VI:7/2 | ii:m7/2 V:7/2 | I:6 | ii:m7/2 V:7/2",
]
B_MAJOR = [
    "III:7 | III:7 | VI:7 | VI:7 | II:7 | II:7 | ii:m7 | V:7",
    "IV:maj7 | iv:m7 | iii:m7 | VI:7b9 | ii:m7 | V:7 | I:maj7 | ii:m7/2 V:7/2",
    "v:m7 | I:7 | IV:maj7 | IV:maj7 | iv:m7 | bVII:7 | iii:m7/2 VI:7/2 | ii:m7/2 V:7/2",
]
A_MINOR = [
    "i:m7 | i:m7 | iv:m7 | iv:m7 | ii:m7b5 | V:7b9 | i:m6 | ii:m7b5/2 V:7b9/2",
    "i:mMaj7 | i:m7 | i:m6 | bVI:7 | ii:m7b5 | V:7alt | i:m7 | ii:m7b5/2 V:7alt/2",
    "i:m7 | iv:m7 | bVII:7 | bIII:maj7 | bVI:maj7 | ii:m7b5 | V:7b9 | i:m7/2 V:7b9/2",
]
B_MINOR = [
    "iv:m7 | bVII:7 | bIII:maj7 | bVI:maj7 | ii:m7b5 | V:7b9 | i:m7 | ii:m7b5/2 V:7b9/2",
    "bVI:maj7 | bVI:maj7 | bII:maj7 | bII:maj7 | ii:m7b5 | V:7alt | i:m6 | ii:m7b5/2 V:7b9/2",
]
INTRO = {"major": "I:maj7/2 vi:m7/2 | ii:m7/2 V:7/2 | I:maj7/2 vi:m7/2 | ii:m7/2 V:7/2",
         "minor": "i:m7/2 bVI:7/2 | ii:m7b5/2 V:7b9/2 | i:m7/2 bVI:7/2 | ii:m7b5/2 V:7b9/2"}
ENDING = {"major": "ii:m7 | V:7 | I:maj7 | I:maj7", "minor": "ii:m7b5 | V:7b9 | i:m6 | i:m6"}

KEYS = {"major": ["F", "Bb", "Eb", "C", "G", "Ab", "D"], "minor": ["C", "D", "G", "F", "A", "E", "Bb"]}


def auto_tempo(energy: float, rng: random.Random) -> float:
    # tenang = ballad 60-75; sedang = medium swing 110-140; enerjik = up-tempo 160-190
    return max(56.0, min(200.0, 60 + 130 * energy ** 1.5 + rng.uniform(-6, 6)))


def arrange(spec: SongSpec) -> Arrangement:
    rng = random.Random(spec.seed)
    mode = spec.mode or ("minor" if spec.valence < 0.35 else "major" if spec.valence > 0.65
                         else ("minor" if rng.random() > spec.valence else "major"))
    tempo = spec.tempo or auto_tempo(spec.energy, rng)
    key_pc = pc_of(spec.key) if spec.key else pc_of(rng.choice(KEYS[mode]))
    swing = spec.swing if spec.swing is not None else (0.62 if tempo < 90 else 0.64 if tempo < 160 else 0.58)
    arr = Arrangement(NAME, tempo, key_pc, mode, swing, spec.valence, spec.energy)

    a_lib, b_lib = (A_MAJOR, B_MAJOR) if mode == "major" else (A_MINOR, B_MINOR)
    A = parse_phrase(rng.choice(a_lib))
    B = parse_phrase(rng.choice(b_lib))
    bar_sec = 4 * 60.0 / tempo
    # jumlah putaran solo supaya mendekati durasi target
    fixed = 4 + 32 + 32 + 4
    solos = max(0, round(((spec.duration - 4) / bar_sec - fixed) / 32)) if spec.duration else 1
    solos = int(min(solos, 40))
    e = spec.energy
    bar = 0

    def sec(kind, label, phrase, inten, chorus=0):
        nonlocal bar
        arr.sections.append(Section(kind, label, bar, len(phrase), max(0.05, min(1.0, inten)), chorus))
        add_phrase(arr, bar, phrase)
        bar += len(phrase)

    sec("intro", "I", parse_phrase(INTRO[mode]), 0.3 + 0.2 * e)
    total_choruses = solos + 2
    for ch in range(total_choruses):
        kind = "head" if ch in (0, total_choruses - 1) else "solo"
        # dinamika: solo makin panas di tengah, lalu turun lagi
        if kind == "solo":
            mid = (solos + 1) / 2
            inten = 0.55 + 0.3 * e + 0.15 * (1 - abs(ch - mid) / max(mid, 1))
        else:
            inten = 0.45 + 0.3 * e
        for lbl, ph in (("A", A), ("A", A), ("B", B), ("A", A)):
            sec(kind, lbl, ph, inten + (0.05 if lbl == "B" else 0), ch)
    sec("ending", "E", parse_phrase(ENDING[mode]), 0.35 + 0.2 * e)
    return arr


def default_spec(valence: float = 0.5, energy: float = 0.5, duration: float = 300, seed: int = 1) -> SongSpec:
    rng = random.Random(seed * 7 + 3)
    ballad = energy < 0.3
    sad = valence < 0.4
    lead = rng.choice([(66, "Tenor Sax"), (59, "Muted Trumpet")] if sad else
                      [(65, "Alto Sax"), (56, "Trumpet"), (66, "Tenor Sax"), (11, "Vibraphone")])
    layers = [
        Layer("piano", "chords", Instrument(0, name="Grand Piano"), "ballad" if ballad else "comping",
              density=0.5, volume=0.8, pan=-0.25, reverb=0.25),
        Layer("bass", "bass", Instrument(32, name="Acoustic Bass"), "two" if ballad else "walking",
              density=0.5, volume=0.95, pan=0.05, reverb=0.1),
        Layer("drums", "drums", Instrument(40, 128, True, "Brush Kit") if ballad or energy < 0.45
              else Instrument(32, 128, True, "Jazz Kit"), "brush" if ballad or energy < 0.45 else "ride",
              density=0.5, volume=0.7, pan=0.1, reverb=0.2),
        Layer("lead", "melody", Instrument(lead[0], name=lead[1]), "head+solo",
              density=0.5, volume=0.8, pan=0.2, reverb=0.3, sections=["head", "solo", "ending"]),
        Layer("strings", "pad", Instrument(49, name="Slow Strings"), "swell",
              density=0.3, volume=0.35, pan=-0.1, reverb=0.5, enabled=ballad or sad,
              sections=["head", "ending"]),
    ]
    return SongSpec(genre=NAME, valence=valence, energy=energy, duration=duration, seed=seed, layers=layers)
