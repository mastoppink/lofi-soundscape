"""Arrangement: hasil 'menerjemahkan' SongSpec menjadi tempo, kunci, bagian lagu, dan akor per ketukan."""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field

from .theory import NOTE_NAMES

ROMAN = {"I": 0, "#I": 1, "bII": 1, "II": 2, "bIII": 3, "III": 4, "IV": 5, "#IV": 6, "bV": 6, "V": 7,
         "bVI": 8, "VI": 9, "bVII": 10, "VII": 11}


@dataclass
class Chord:
    root: int           # pitch class
    quality: str
    start: float        # ketukan absolut
    beats: float

    @property
    def end(self) -> float:
        return self.start + self.beats


@dataclass
class Section:
    kind: str           # intro | head | solo | ending | (genre lain: verse, chorus, build, ...)
    label: str          # A / B / ... (frasa yang sama = melodi tema yang sama)
    start_bar: int
    bars: int
    intensity: float    # 0..1
    chorus: int = 0     # nomor putaran (untuk dinamika solo)

    @property
    def end_bar(self) -> int:
        return self.start_bar + self.bars


@dataclass
class Arrangement:
    genre: str
    tempo: float
    key_pc: int
    mode: str
    swing: float
    valence: float
    energy: float
    sections: list[Section] = field(default_factory=list)
    chords: list[Chord] = field(default_factory=list)
    beats_per_bar: int = 4
    tail: float = 4.0

    @property
    def beat_sec(self) -> float:
        return 60.0 / self.tempo

    @property
    def total_bars(self) -> int:
        return self.sections[-1].end_bar if self.sections else 0

    @property
    def total_beats(self) -> float:
        return self.total_bars * self.beats_per_bar

    @property
    def duration(self) -> float:
        return self.total_beats * self.beat_sec + self.tail

    @property
    def key_name(self) -> str:
        return NOTE_NAMES[self.key_pc] + ("m" if self.mode == "minor" else "")

    def time(self, beat: float, swing: bool = True) -> float:
        """Ketukan absolut -> detik, dengan swing pada 8th note off-beat."""
        if swing:
            whole = int(beat)
            frac = beat - whole
            if abs(frac - 0.5) < 1e-6:
                beat = whole + self.swing
            elif 0 < frac < 1:
                # pecahan lain dipetakan linear supaya tetap konsisten dengan swing
                beat = whole + (frac / 0.5 * self.swing if frac < 0.5 else self.swing + (frac - 0.5) / 0.5 * (1 - self.swing))
        return beat * self.beat_sec

    def _starts(self):
        if not hasattr(self, "_cs") or len(self._cs) != len(self.chords):
            self._cs = [c.start for c in self.chords]
        return self._cs

    def chord_at(self, beat: float) -> Chord:
        i = bisect.bisect_right(self._starts(), beat + 1e-6) - 1
        return self.chords[max(0, min(i, len(self.chords) - 1))]

    def section_at_bar(self, bar: int) -> Section:
        for s in self.sections:
            if s.start_bar <= bar < s.end_bar:
                return s
        return self.sections[-1]

    def describe(self) -> str:
        lines = [f"{self.genre} | {self.key_name} | {self.tempo:.0f} BPM | swing {self.swing:.2f} | "
                 f"{self.total_bars} bar | {self.duration / 60:.1f} menit"]
        for s in self.sections:
            chs = [c for c in self.chords if s.start_bar * 4 <= c.start < s.end_bar * 4]
            txt = " ".join(f"{NOTE_NAMES[c.root]}{c.quality}" for c in chs)
            lines.append(f"  bar {s.start_bar + 1:>3}  {s.kind:<7}{s.label:<2} x{s.bars:<2} int={s.intensity:.2f}  {txt}")
        return "\n".join(lines)


def parse_phrase(text: str) -> list[list[tuple[int, str, float]]]:
    """'I:maj7 | ii:m7/2 V:7/2' -> per bar: [(derajat_semitone, kualitas, ketukan)]"""
    bars = []
    for bar in text.split("|"):
        items = []
        toks = bar.split()
        for tok in toks:
            m = re.fullmatch(r"([b#]?[IViv]+):([\w#]+)(?:/([\d.]+))?", tok)
            if not m:
                raise ValueError(f"token akor salah: {tok}")
            deg = ROMAN[m.group(1).upper() if not m.group(1)[0] in "b#" else m.group(1)[0] + m.group(1)[1:].upper()]
            beats = float(m.group(3)) if m.group(3) else 4.0 / len(toks)
            items.append((deg, m.group(2), beats))
        bars.append(items)
    return bars


def add_phrase(arr: Arrangement, start_bar: int, phrase: list[list[tuple[int, str, float]]]):
    for bi, items in enumerate(phrase):
        pos = (start_bar + bi) * arr.beats_per_bar
        for deg, q, beats in items:
            arr.chords.append(Chord((arr.key_pc + deg) % 12, q, pos, beats))
            pos += beats
