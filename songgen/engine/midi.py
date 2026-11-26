"""Ekspor lagu ke file MIDI (satu track per layer), untuk dibuka di GarageBand / Logic / DAW lain."""
from __future__ import annotations

from pathlib import Path

import mido

from .arrangement import Arrangement
from .song import SongSpec

TPB = 960   # tick per ketukan


def export(spec: SongSpec, arr: Arrangement, notes: dict, out: Path, include_drums: bool = True) -> Path:
    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("track_name", name="songgen", time=0))
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(arr.tempo), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    meta.append(mido.MetaMessage("key_signature", key=arr.key_name, time=0))
    last = 0
    for s in arr.sections:                      # penanda bagian lagu (marker di DAW)
        t = s.start_bar * arr.beats_per_bar * TPB
        meta.append(mido.MetaMessage("marker", text=f"{s.kind} {s.label}", time=t - last))
        last = t
    mid.tracks.append(meta)
    spt = arr.beat_sec / TPB                    # detik per tick (tempo konstan)
    ch = 0
    for layer in spec.layers:
        if layer.id not in notes or not notes[layer.id]:
            continue
        if layer.instrument.drums and not include_drums:
            continue
        if layer.instrument.drums:
            chan = 9
        else:
            chan = ch
            ch = ch + 1 if ch + 1 != 9 else 10
        tr = mido.MidiTrack()
        tr.append(mido.MetaMessage("track_name", name=f"{layer.id} ({layer.instrument.name})", time=0))
        if not layer.instrument.drums:
            tr.append(mido.Message("program_change", channel=chan, program=layer.instrument.preset, time=0))
        ev = []
        for n in notes[layer.id]:
            on = max(0, round(n.start / spt))
            off = max(on + 1, round((n.start + n.dur) / spt))
            ev.append((on, 1, n.key, n.vel))
            ev.append((off, 0, n.key, 0))
        ev.sort(key=lambda e: (e[0], e[1]))
        now = 0
        for t, kind, key, v in ev:
            tr.append(mido.Message("note_on" if kind else "note_off", channel=chan, note=key, velocity=v, time=t - now))
            now = t
        mid.tracks.append(tr)
    out = Path(out)
    mid.save(str(out))
    return out
