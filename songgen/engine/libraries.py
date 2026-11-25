"""Unduh library instrumen rekaman asli ke folder instruments/."""
from __future__ import annotations

import io
import json
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path

from .sampler import LIB_DIR_DEFAULT

UA = {"User-Agent": "songgen/0.2"}


def _get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()


def _salamander(dest: Path, log):
    # Salamander Grand Piano V3 (Alexander Holm, CC BY 3.0) via paket npm @audio-samples
    for v in (2, 4, 6, 8, 10, 12, 14, 16):
        url = f"https://registry.npmjs.org/@audio-samples/piano-velocity{v}/-/piano-velocity{v}-1.0.5.tgz"
        log(f"  piano layer {v}/16 ...")
        with tarfile.open(fileobj=io.BytesIO(_get(url)), mode="r:gz") as t:
            for m in t.getmembers():
                if m.name.startswith("package/audio/") and m.name.endswith(".ogg"):
                    (dest / Path(m.name).name).write_bytes(t.extractfile(m).read())
    return {"name": "Salamander Grand Piano", "glob": "*.ogg",
            "pattern": "(?P<note>[A-G]#?)(?P<oct>-?\\d)v(?P<vel>\\d+)", "octave_offset": 1,
            "release": 0.35, "max_len": 14, "vel_curve": 0.5,
            "credit": "Salamander Grand Piano V3 by Alexander Holm (CC BY 3.0)"}


UPRIGHT_FILES = ['BKCtbss_Pizz_A#0_v1_rr1.wav', 'BKCtbss_Pizz_A#0_v1_rr2.wav', 'BKCtbss_Pizz_A#0_v3_rr1.wav', 'BKCtbss_Pizz_A#0_v3_rr2.wav', 'BKCtbss_Pizz_A1_v1_rr1.wav', 'BKCtbss_Pizz_A1_v1_rr2.wav', 'BKCtbss_Pizz_B2_v1_rr1.wav', 'BKCtbss_Pizz_B2_v1_rr2.wav', 'BKCtbss_Pizz_C#2_v1_rr1.wav', 'BKCtbss_Pizz_C#2_v1_rr2.wav', 'BKCtbss_Pizz_C1_v1_rr1.wav', 'BKCtbss_Pizz_C1_v1_rr2.wav', 'BKCtbss_Pizz_C1_v3_rr1.wav', 'BKCtbss_Pizz_C1_v3_rr2.wav', 'BKCtbss_Pizz_D1_v1_rr1.wav', 'BKCtbss_Pizz_D1_v1_rr2.wav', 'BKCtbss_Pizz_E0_v1_rr1.wav', 'BKCtbss_Pizz_E0_v1_rr2.wav', 'BKCtbss_Pizz_E0_v3_rr1.wav', 'BKCtbss_Pizz_E0_v3_rr2.wav', 'BKCtbss_Pizz_E1_v1_rr1.wav', 'BKCtbss_Pizz_E1_v1_rr2.wav', 'BKCtbss_Pizz_E1_v3_rr1.wav', 'BKCtbss_Pizz_E1_v3_rr2.wav', 'BKCtbss_Pizz_E2_v1_rr1.wav', 'BKCtbss_Pizz_E2_v1_rr2.wav', 'BKCtbss_Pizz_F#0_v1_rr1.wav', 'BKCtbss_Pizz_F#0_v1_rr2.wav', 'BKCtbss_Pizz_F#0_v3_rr1.wav', 'BKCtbss_Pizz_F#0_v3_rr2.wav', 'BKCtbss_Pizz_F#1_v1_rr1.wav', 'BKCtbss_Pizz_F#1_v1_rr2.wav', 'BKCtbss_Pizz_G#1_v1_rr1.wav', 'BKCtbss_Pizz_G#1_v1_rr2.wav', 'BKCtbss_Pizz_G#2_v1_rr1.wav', 'BKCtbss_Pizz_G#2_v1_rr2.wav', 'BKCtbss_Pizz_G0_v1_rr1.wav', 'BKCtbss_Pizz_G0_v1_rr2.wav', 'BKCtbss_Pizz_G0_v3_rr1.wav', 'BKCtbss_Pizz_G0_v3_rr2.wav']


def _upright(dest: Path, log):
    # VSCO-2 Community Edition, Solo Contrabass Pizz (Versilian Studios, CC0)
    base = "https://raw.githubusercontent.com/sgossner/VSCO-2-CE/master/Strings/Solo%20Contrabass/Pizz/"
    log(f"  upright bass ({len(UPRIGHT_FILES)} file) ...")
    for n in UPRIGHT_FILES:
        (dest / n).write_bytes(_get(base + urllib.parse.quote(n)))
    return {"name": "Upright Bass (pizz)", "glob": "*.wav",
            "pattern": "BKCtbss_Pizz_(?P<note>[A-G]#?)(?P<oct>-?\\d)_v(?P<vel>\\d+)_rr(?P<rr>\\d+)",
            "octave_offset": 2, "release": 0.12, "max_len": 4, "vel_curve": 0.6,
            "credit": "VSCO-2 Community Edition by Versilian Studios (CC0)"}


LIBRARIES = {"salamander_piano": _salamander, "upright_bass": _upright}


def install(names=None, root: Path = LIB_DIR_DEFAULT, log=print):
    for name in names or LIBRARIES:
        dest = root / name
        if (dest / "instrument.json").exists():
            log(f"Library '{name}' sudah ada.")
            continue
        dest.mkdir(parents=True, exist_ok=True)
        log(f"Mengunduh library '{name}' ...")
        meta = LIBRARIES[name](dest, log)
        (dest / "instrument.json").write_text(json.dumps(meta, indent=1))
    log("Library instrumen siap.")
