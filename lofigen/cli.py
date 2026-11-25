"""Command line: python -m lofigen ..."""
from __future__ import annotations

import argparse
import random
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PRESETS = ROOT / "presets"
SAMPLES = ROOT / "samples"
DEFAULT_SF = ROOT / "soundfonts" / "GeneralUser-GS.sf2"
SF_URL = "https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/main/GeneralUser-GS.sf2"


def parse_duration(s: str) -> float:
    """'1h', '90m', '1h30m', '45s', '3600' -> detik"""
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", s.strip().lower())
    if not m or not any(m.groups()):
        raise argparse.ArgumentTypeError(f"durasi tidak valid: {s}")
    h, mi, se = (int(g or 0) for g in m.groups())
    return h * 3600 + mi * 60 + se


def load_preset(name: str) -> dict:
    p = Path(name)
    if not p.exists():
        p = PRESETS / f"{name}.yaml"
    if not p.exists():
        raise SystemExit(f"Preset '{name}' tidak ada. Pilihan: {', '.join(x.stem for x in PRESETS.glob('*.yaml'))}")
    return yaml.safe_load(p.read_text())


def cmd_setup(a):
    DEFAULT_SF.parent.mkdir(exist_ok=True)
    if DEFAULT_SF.exists():
        print(f"Soundfont sudah ada: {DEFAULT_SF}")
    else:
        print(f"Mengunduh GeneralUser GS (~32 MB) ke {DEFAULT_SF} ...")
        urllib.request.urlretrieve(SF_URL, DEFAULT_SF)
        print("Selesai.")
    for name in ("rain", "cafe", "wind", "ocean", "birds", "fire", "thunder"):
        (SAMPLES / name).mkdir(parents=True, exist_ok=True)
    print(f"Folder ambience siap di {SAMPLES}/ — isi dengan rekaman CC0 (lihat samples/README.md).")


def cmd_list(a):
    for p in sorted(PRESETS.glob("*.yaml")):
        d = yaml.safe_load(p.read_text())
        print(f"{p.stem:18} {d.get('description', '')}")


def cmd_render(a):
    from .render import render
    preset = load_preset(a.preset)
    if a.lofi is not None:
        preset["lofi"] = a.lofi
    if a.mood is not None:
        preset.setdefault("music", {})["mood"] = a.mood
    if a.music_volume is not None:
        preset["music_volume"] = a.music_volume
    if a.ambience_volume is not None:
        preset["ambience"] = {k: v * a.ambience_volume for k, v in preset.get("ambience", {}).items()}
    sf = Path(a.soundfont)
    if not sf.exists():
        raise SystemExit(f"Soundfont tidak ditemukan: {sf}\nJalankan dulu: python -m lofigen setup")
    seed = a.seed if a.seed is not None else random.randrange(1_000_000)
    out = Path(a.out or f"{Path(a.preset).stem}_{seed}.wav")
    print(f"Preset: {preset.get('name', a.preset)} | durasi {a.duration:.0f}s | seed {seed}")
    render(preset, out, a.duration, seed, sf, Path(a.samples))
    if a.video or a.cover:
        from .video import make_video
        if not a.cover:
            raise SystemExit("--video butuh --cover gambar.jpg")
        make_video(out, Path(a.cover), out.with_suffix(".mp4"))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lofigen", description="Generator musik lofi + soundscape untuk YouTube")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="unduh soundfont & siapkan folder sampel").set_defaults(fn=cmd_setup)
    sub.add_parser("presets", help="daftar preset").set_defaults(fn=cmd_list)
    r = sub.add_parser("render", help="render mix panjang")
    r.add_argument("--preset", default="rainy_cafe")
    r.add_argument("--duration", type=parse_duration, default="1h", help="mis. 30m, 1h, 2h30m")
    r.add_argument("--seed", type=int)
    r.add_argument("--out", help="file output (.wav / .flac)")
    r.add_argument("--lofi", type=float, help="0..1 seberapa 'kotor'")
    r.add_argument("--mood", type=float, help="0 sendu .. 1 ceria")
    r.add_argument("--music-volume", type=float)
    r.add_argument("--ambience-volume", type=float, help="pengali volume semua ambience")
    r.add_argument("--soundfont", default=str(DEFAULT_SF))
    r.add_argument("--samples", default=str(SAMPLES))
    r.add_argument("--cover", help="gambar untuk video")
    r.add_argument("--video", action="store_true", help="buat juga MP4 (butuh ffmpeg + --cover)")
    r.set_defaults(fn=cmd_render)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main(sys.argv[1:])
