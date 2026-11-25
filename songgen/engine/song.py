"""Model lagu: pengaturan global + daftar layer. Bisa disimpan/dimuat sebagai JSON."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


@dataclass
class Instrument:
    preset: int                 # nomor program General MIDI (0-127)
    bank: int = 0               # 128 = drum kit
    drums: bool = False
    name: str = ""


@dataclass
class Layer:
    id: str                     # nama unik, mis. "piano"
    role: str                   # chords | bass | drums | melody | pad
    instrument: Instrument
    style: str = "auto"         # gaya main, tergantung peran (lihat ROLE_STYLES)
    density: float = 0.5        # 0 jarang .. 1 ramai
    volume: float = 0.8         # 0..1.5
    pan: float = 0.0            # -1 kiri .. 1 kanan
    reverb: float = 0.25        # kirim ke reverb ruangan, 0..1
    octave: int = 0             # geser register (-2..2)
    sections: list[str] | None = None   # bagian lagu tempat layer bunyi; None = bawaan genre
    seed: int | None = None     # None = turunan dari seed lagu; ubah untuk acak ulang layer ini saja
    enabled: bool = True
    mute: bool = False
    solo: bool = False

    @staticmethod
    def from_dict(d: dict) -> "Layer":
        d = dict(d)
        d["instrument"] = Instrument(**d["instrument"])
        known = {f.name for f in fields(Layer)}
        return Layer(**{k: v for k, v in d.items() if k in known})


@dataclass
class SongSpec:
    genre: str = "jazz"
    valence: float = 0.5        # 0 sedih .. 1 senang
    energy: float = 0.5         # 0 tenang .. 1 enerjik
    duration: float = 300.0     # detik (target; lagu selesai di akhir frasa terdekat)
    seed: int = 1
    tempo: float | None = None  # None = otomatis dari genre + energy
    key: str | None = None      # mis. "F", "Bb"; None = otomatis
    mode: str | None = None     # "major" / "minor"; None = dari valence
    swing: float | None = None  # 0.5 lurus .. 0.67 triplet; None = otomatis
    lofi: float = 0.0           # 0 bersih .. 1 tape/vinyl
    room: float = 0.5           # ukuran ruang reverb
    layers: list[Layer] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "SongSpec":
        d = dict(d)
        d["layers"] = [Layer.from_dict(x) for x in d.get("layers", [])]
        known = {f.name for f in fields(SongSpec)}
        return SongSpec(**{k: v for k, v in d.items() if k in known})

    def save(self, path: str | Path):
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))

    @staticmethod
    def load(path: str | Path) -> "SongSpec":
        return SongSpec.from_dict(json.loads(Path(path).read_text()))

    def layer(self, layer_id: str) -> Layer:
        for l in self.layers:
            if l.id == layer_id:
                return l
        raise KeyError(f"layer '{layer_id}' tidak ada (ada: {', '.join(l.id for l in self.layers)})")


@dataclass
class Note:
    start: float    # detik
    dur: float      # detik
    key: int        # nada MIDI
    vel: int        # 1..127
