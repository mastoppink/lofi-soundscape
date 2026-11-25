"""Command line: python -m songgen ..."""
from __future__ import annotations

import argparse
import random
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SF = ROOT / "soundfonts" / "GeneralUser-GS.sf2"
SF_URL = "https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/main/GeneralUser-GS.sf2"


def parse_duration(s: str) -> float:
    """'5m', '1h', '1h30m', '45s', '300' -> detik"""
    s = str(s).strip().lower()
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", s)
    if not m or not any(m.groups()):
        raise argparse.ArgumentTypeError(f"durasi tidak valid: {s}")
    h, mi, se = (int(g or 0) for g in m.groups())
    return h * 3600 + mi * 60 + se


def _spec_from_args(a):
    from .engine import genres
    from .engine.song import SongSpec
    if getattr(a, "spec", None):
        spec = SongSpec.load(a.spec)
    else:
        seed = a.seed if a.seed is not None else random.randrange(1_000_000)
        spec = genres.get(a.genre).default_spec(a.valence, a.energy, a.duration, seed)
    for k in ("tempo", "key", "mode", "swing", "lofi"):
        v = getattr(a, k, None)
        if v is not None:
            setattr(spec, k, v)
    if getattr(a, "spec", None) and a.seed is not None:
        spec.seed = a.seed
    return spec


def _apply_layer_flags(spec, a):
    for lid in (a.mute or "").split(","):
        if lid:
            spec.layer(lid).mute = True
    for lid in (a.solo or "").split(","):
        if lid:
            spec.layer(lid).solo = True


def cmd_setup(a):
    DEFAULT_SF.parent.mkdir(exist_ok=True)
    if DEFAULT_SF.exists():
        print(f"Soundfont sudah ada: {DEFAULT_SF}")
        return
    print(f"Mengunduh GeneralUser GS (~32 MB) ke {DEFAULT_SF} ...")
    urllib.request.urlretrieve(SF_URL, DEFAULT_SF)
    print("Selesai.")


def cmd_new(a):
    spec = _spec_from_args(a)
    out = Path(a.out or f"{spec.genre}_{spec.seed}.json")
    spec.save(out)
    print(f"Spesifikasi lagu disimpan: {out}")
    for l in spec.layers:
        print(f"  {'✓' if l.enabled else '·'} {l.id:<8} {l.role:<7} {l.instrument.name:<15} {l.style}")


def cmd_info(a):
    from .engine.render import arrange, title_for
    spec = _spec_from_args(a)
    print(f"'{title_for(spec)}'")
    print(arrange(spec).describe())


def cmd_reroll(a):
    from .engine.song import SongSpec
    spec = SongSpec.load(a.spec)
    for lid in a.layer.split(","):
        l = spec.layer(lid)
        l.seed = random.randrange(1_000_000)
        print(f"Layer '{lid}' diacak ulang (seed {l.seed})")
    spec.save(a.spec)


def cmd_render(a):
    from .engine.render import render_song
    spec = _spec_from_args(a)
    _apply_layer_flags(spec, a)
    sf = Path(a.soundfont)
    if not sf.exists():
        raise SystemExit(f"Soundfont tidak ditemukan: {sf}\nJalankan dulu: python -m songgen setup")
    out = Path(a.out or f"{spec.genre}_{spec.seed}.wav")
    res = render_song(spec, out, sf, a.preview, Path(a.stems) if a.stems else None)
    if not a.spec:
        spec.save(out.with_suffix(".json"))
        print(f"Spesifikasi: {out.with_suffix('.json')} (pakai lagi untuk render ulang/ubah layer)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="songgen", description="Generator lagu instrumental berbasis layer")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="unduh soundfont").set_defaults(fn=cmd_setup)

    def common(p, with_spec=True):
        if with_spec:
            p.add_argument("spec", nargs="?", help="file lagu .json (opsional)")
        p.add_argument("--genre", default="jazz")
        p.add_argument("--valence", type=float, default=0.5, help="0 sedih .. 1 senang")
        p.add_argument("--energy", type=float, default=0.5, help="0 tenang .. 1 enerjik")
        p.add_argument("--duration", type=parse_duration, default="5m", help="mis. 3m, 5m")
        p.add_argument("--seed", type=int)
        p.add_argument("--tempo", type=float)
        p.add_argument("--key", help="mis. F, Bb, C#")
        p.add_argument("--mode", choices=["major", "minor"])
        p.add_argument("--swing", type=float)
        p.add_argument("--lofi", type=float, help="0 bersih .. 1 tape/vinyl")

    p = sub.add_parser("new", help="buat file lagu .json dari genre + mood")
    common(p, with_spec=False)
    p.add_argument("-o", "--out")
    p.set_defaults(fn=cmd_new, spec=None)

    p = sub.add_parser("info", help="tampilkan struktur & akor")
    common(p)
    p.set_defaults(fn=cmd_info)

    p = sub.add_parser("reroll", help="acak ulang layer tertentu di file .json")
    p.add_argument("spec")
    p.add_argument("--layer", required=True, help="id layer, pisahkan dengan koma")
    p.set_defaults(fn=cmd_reroll)

    p = sub.add_parser("render", help="render lagu ke audio")
    common(p)
    p.add_argument("-o", "--out")
    p.add_argument("--preview", type=parse_duration, help="render hanya N detik pertama, mis. 30s")
    p.add_argument("--mute", help="id layer yang dimatikan, pisahkan koma")
    p.add_argument("--solo", help="hanya layer ini, pisahkan koma")
    p.add_argument("--stems", help="folder untuk menyimpan audio per layer")
    p.add_argument("--soundfont", default=str(DEFAULT_SF))
    p.set_defaults(fn=cmd_render)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main(sys.argv[1:])
