"""Render daftar Note ke audio stereo pakai SoundFont (instrumen sampel asli)."""
from __future__ import annotations

import numpy as np
import tinysoundfont

from . import SR


class Instrument:
    def __init__(self, sf_bytes: bytes, bank: int, preset: int, drums: bool = False, gain_db: float = 0.0):
        self.synth = tinysoundfont.Synth(samplerate=SR, gain=gain_db)
        sfid = self.synth.sfload(sf_bytes)
        self.synth.program_select(0, sfid, bank, preset, is_drums=drums)
        if drums:
            self.synth.program_select(9, sfid, bank, preset, is_drums=True)
        self.chan = 9 if drums else 0

    def render(self, notes, duration: float) -> np.ndarray:
        s = self.synth
        s.sounds_off()
        total = int(duration * SR)
        ev = []
        for n in notes:
            on = int(n.start * SR)
            off = int((n.start + n.dur) * SR)
            if on >= total:
                continue
            ev.append((on, 1, n.key, n.vel))
            ev.append((min(off, total - 1), 0, n.key, 0))
        ev.sort(key=lambda e: (e[0], e[1]))  # note-off dulu sebelum note-on di sampel yang sama
        out = np.zeros((total, 2), dtype=np.float32)
        pos = 0
        for at, kind, key, vel in ev:
            if at > pos:
                buf = s.generate_simple(at - pos)
                out[pos:at] = np.frombuffer(buf, dtype=np.float32).reshape(-1, 2)
                pos = at
            if kind:
                s.noteon(self.chan, key, vel)
            else:
                s.noteoff(self.chan, key)
        if pos < total:
            buf = s.generate_simple(total - pos)
            out[pos:] = np.frombuffer(buf, dtype=np.float32).reshape(-1, 2)
        return out
