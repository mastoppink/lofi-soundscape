"""Membuat satu 'lagu' lofi secara prosedural dari seed."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .theory import NOTE_NAMES, PROGRESSIONS, SCALES, voice_chord

# GM drum keys
KICK, SNARE, RIM, CLHAT, PEDHAT, OPHAT, RIDE, SHAKER = 36, 38, 37, 42, 44, 46, 51, 70


@dataclass
class Note:
    start: float      # detik
    dur: float        # detik
    key: int          # MIDI note
    vel: int          # 1-127


@dataclass
class Song:
    seed: int
    title: str
    bpm: float
    key_name: str
    mode: str
    duration: float
    tracks: dict[str, list[Note]] = field(default_factory=dict)
    kick_times: list[float] = field(default_factory=list)


ADJ = ["Rainy", "Quiet", "Late", "Faded", "Warm", "Sleepy", "Velvet", "Hazy", "Golden", "Blue",
       "Paper", "Soft", "Dusty", "Midnight", "Lazy", "Cloudy", "Amber", "Distant", "Mellow", "Foggy"]
NOUN = ["Window", "Streets", "Coffee", "Letters", "Afternoon", "Polaroids", "Train", "Lanterns",
        "Notebook", "Rooftop", "Daydream", "Tapes", "Sunday", "Moon", "Garden", "Pages", "Balcony",
        "Memories", "Harbor", "Bicycle"]


def compose(seed: int, opts: dict) -> Song:
    rng = random.Random(seed)
    bpm_lo, bpm_hi = opts.get("bpm", [70, 85])
    bpm = rng.uniform(bpm_lo, bpm_hi)
    beat = 60.0 / bpm
    bar = beat * 4
    swing = opts.get("swing", 0.6)          # 0.5 = lurus, 0.66 = triplet
    mood = opts.get("mood", 0.5)            # 0 sendu .. 1 ceria
    mode = "major" if rng.random() < mood else "minor"
    tonic = rng.randrange(12)
    prog = rng.choice(PROGRESSIONS[mode])
    scale = SCALES[mode]
    energy = opts.get("energy", 0.5)

    def t(bar_i: int, beat_f: float) -> float:
        """Waktu dengan swing pada 8th note off-beat."""
        whole = int(beat_f)
        frac = beat_f - whole
        if abs(frac - 0.5) < 1e-6:
            frac = swing
        return bar_i * bar + (whole + frac) * beat

    def hum(x: float, amt: float = 0.012) -> float:
        return max(0.0, x + rng.gauss(0, amt))

    # struktur: (nama, jumlah bar, keys, bass, drums, melodi)
    sections = [
        ("intro", 4, True, False, False, False),
        ("A", 8, True, True, True, False),
        ("B", 8, True, True, True, True),
        ("break", 4, True, False, False, True),
        ("A2", 8, True, True, True, rng.random() < 0.5),
        ("B2", 8, True, True, True, True),
        ("outro", 4, True, True, False, False),
    ]
    keys, bass, drums, mel = [], [], [], []
    kick_times = []
    prev_voicing = None
    drum_pat = rng.choice(["boombap", "laid", "halftime"])
    hat_kind = rng.choice([CLHAT, CLHAT, SHAKER, RIDE])
    comp_style = rng.choice(["sustain", "stab", "arp"])
    bar_i = 0
    for name, nbars, k_on, b_on, d_on, m_on in sections:
        for b in range(nbars):
            # 1 akor per bar (kadang 2 bar per akor dirasa lebih santai)
            deg, qual = prog[(bar_i // (2 if bpm < 72 else 1)) % len(prog)]
            root_pc = (tonic + deg) % 12
            voicing = voice_chord(root_pc, qual, prev_voicing)
            prev_voicing = voicing
            last = (name == "outro" and b == nbars - 1)
            # --- keys ---
            if k_on:
                if comp_style == "sustain" or name in ("intro", "outro") or last:
                    hits = [(0.0, 4.0 if not last else 8.0)]
                elif comp_style == "stab":
                    hits = [(0.0, 1.4), (1.5, 0.9), (2.5, 1.4)] if rng.random() < 0.6 else [(0.0, 2.3), (2.5, 1.4)]
                else:
                    hits = [(0.0, 4.0)]
                for (pos, length) in hits:
                    st = t(bar_i, pos)
                    strum = rng.uniform(0.008, 0.03)
                    for i, n in enumerate(voicing):
                        if comp_style == "arp" and name not in ("intro", "outro") and not last:
                            st_i = t(bar_i, i * 0.5)
                            keys.append(Note(hum(st_i, 0.008), bar - i * 0.5 * beat, n, rng.randint(50, 72)))
                        else:
                            keys.append(Note(hum(st + i * strum, 0.005), length * beat * 0.97, n,
                                             rng.randint(48, 68)))
            # --- bass ---
            if b_on:
                broot = 36 + (root_pc - 0) % 12
                if broot > 47:
                    broot -= 12
                fifth = broot + 7
                pat = rng.choice([[(0, 1.8, broot), (2.5, 1.3, broot)],
                                  [(0, 1.4, broot), (1.5, 0.4, broot), (2.5, 1.0, fifth)],
                                  [(0, 3.5, broot)],
                                  [(0, 1.0, broot), (2.0, 1.0, broot + 12 if broot < 40 else broot), (3.5, 0.4, fifth)]])
                for pos, ln, nn in pat:
                    bass.append(Note(hum(t(bar_i, pos), 0.006), ln * beat, nn, rng.randint(80, 100)))
            # --- drums ---
            if d_on:
                fill = (b == nbars - 1) and rng.random() < 0.6
                if drum_pat == "halftime":
                    kicks = [0, 2.5] if rng.random() < 0.7 else [0, 1.5, 2.5]
                    snares = [2]
                elif drum_pat == "laid":
                    kicks = [0, 1.5, 2.75] if rng.random() < 0.5 else [0, 2.5]
                    snares = [1, 3]
                else:
                    kicks = [0, 0.5 + 1.0 * (rng.random() < 0.3), 2.5]
                    snares = [1, 3]
                for k in kicks:
                    tt = hum(t(bar_i, k), 0.006)
                    drums.append(Note(tt, 0.3, KICK, rng.randint(95, 115)))
                    kick_times.append(tt)
                snare_key = RIM if (energy < 0.3 and rng.random() < 0.7) else SNARE
                for s in snares:
                    # snare lofi sedikit telat (laid back)
                    drums.append(Note(hum(t(bar_i, s) + 0.018, 0.006), 0.3, snare_key, rng.randint(85, 108)))
                for h in [x * 0.5 for x in range(8)]:
                    if rng.random() < 0.08 + (0.3 * (1 - energy)) * (h % 1 == 0.5):
                        continue
                    acc = 1.0 if h % 1 == 0 else 0.7
                    drums.append(Note(hum(t(bar_i, h), 0.008), 0.15, hat_kind, int(rng.randint(55, 80) * acc)))
                if rng.random() < 0.3:
                    drums.append(Note(t(bar_i, 3.5), 0.4, OPHAT, rng.randint(45, 65)))
                # ghost snare
                if rng.random() < 0.4:
                    drums.append(Note(hum(t(bar_i, rng.choice([1.75, 2.75, 3.75])), 0.005), 0.2, SNARE, rng.randint(25, 40)))
                if fill:
                    for f in (3.0, 3.25, 3.5, 3.75):
                        if rng.random() < 0.6:
                            drums.append(Note(hum(t(bar_i, f), 0.005), 0.2, SNARE, rng.randint(40, 75)))
            # --- melodi ---
            if m_on and rng.random() < 0.85:
                pool = [60 + tonic + o * 12 + s for o in (0, 1) for s in scale]
                pool = [p for p in pool if 62 <= p <= 82]
                pos = rng.choice([0.0, 0.5, 1.0])
                idx = rng.randrange(len(pool))
                while pos < 3.6:
                    ln = rng.choice([0.5, 0.5, 1.0, 1.5])
                    if rng.random() < 0.72:
                        mel.append(Note(hum(t(bar_i, pos), 0.01), ln * beat * 0.95, pool[idx], rng.randint(55, 80)))
                    idx = max(0, min(len(pool) - 1, idx + rng.choice([-2, -1, -1, 1, 1, 2, 0])))
                    pos += ln
            bar_i += 1

    duration = bar_i * bar + 3.0  # ekor reverb/sustain
    title = f"{rng.choice(ADJ)} {rng.choice(NOUN)}"
    song = Song(seed, title, bpm, NOTE_NAMES[tonic], mode, duration,
                {"keys": keys, "bass": bass, "drums": drums, "melody": mel}, sorted(kick_times))
    return song
