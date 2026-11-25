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


JAZZ_KIT_FILES = ['Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_HitSN_v3_rr1_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_HitSN_v3_rr2_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_HitSN_v5_rr1_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_HitSN_v5_rr2_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_HitSN_v6_rr1_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_HitSN_v6_rr2_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_HitSN_v7_rr1_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_HitSN_v7_rr2_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_HitSN_v9_rr1_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_HitSN_v9_rr2_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_stick_v1_rr1_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_stick_v1_rr2_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_taps_v4_rr1_Mid.wav', 'Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_taps_v4_rr2_Mid.wav', 'Membranophones/Struck Membranophones/Bass Drum 1/BDrumNew_hit_v2_rr1_Sum.wav', 'Membranophones/Struck Membranophones/Bass Drum 1/BDrumNew_hit_v2_rr2_Sum.wav', 'Membranophones/Struck Membranophones/Bass Drum 1/BDrumNew_hit_v3_rr1_Sum.wav', 'Membranophones/Struck Membranophones/Bass Drum 1/BDrumNew_hit_v3_rr2_Sum.wav', 'Membranophones/Struck Membranophones/Bass Drum 1/BDrumNew_hit_v5_rr1_Sum.wav', 'Membranophones/Struck Membranophones/Bass Drum 1/BDrumNew_hit_v5_rr2_Sum.wav', 'Membranophones/Struck Membranophones/Bass Drum 1/BDrumNew_hit_v7_rr1_Sum.wav', 'Membranophones/Struck Membranophones/Bass Drum 1/BDrumNew_hit_v7_rr2_Sum.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_Close_rr1_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_Close_rr2_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitC_v1_rr1_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitC_v1_rr2_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitC_v2_rr1_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitC_v2_rr2_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitC_v3_rr1_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitC_v3_rr2_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitC_v4_rr1_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitC_v4_rr2_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitLoose_rr1_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitLoose_rr2_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitOC_rr5_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitO_rr1_Mid.wav', 'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitO_rr2_Mid.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 1/susCymb1_hit_bell_mf1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 1/susCymb1_hit_bell_pp1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 1/susCymb1_hit_f1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 1/susCymb1_hit_fff1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 1/susCymb1_hit_mp1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 1/susCymb1_hit_stick_f1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 1/susCymb1_hit_stick_mp1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 1/susCymb1_hit_stick_pp1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 2/susCymb2_hit_bell_f1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 2/susCymb2_hit_bell_p1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 2/susCymb2_hit_f1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 2/susCymb2_hit_fff1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 2/susCymb2_hit_mf1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 2/susCymb2_hit_stick_mf1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 2/susCymb2_hit_stick_mp1.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 2/susCymb2_hit_stick_pp1.wav']
JAZZ_KIT_MAP = {'36': [['BDrumNew_hit_v2_rr1_Sum.wav', 1, 35], ['BDrumNew_hit_v2_rr2_Sum.wav', 1, 35], ['BDrumNew_hit_v3_rr1_Sum.wav', 36, 60], ['BDrumNew_hit_v3_rr2_Sum.wav', 36, 60], ['BDrumNew_hit_v5_rr1_Sum.wav', 61, 90], ['BDrumNew_hit_v5_rr2_Sum.wav', 61, 90], ['BDrumNew_hit_v7_rr1_Sum.wav', 91, 127], ['BDrumNew_hit_v7_rr2_Sum.wav', 91, 127]], '38': [['Snare2_HitSN_v3_rr1_Mid.wav', 1, 40], ['Snare2_HitSN_v3_rr2_Mid.wav', 1, 40], ['Snare2_HitSN_v5_rr1_Mid.wav', 41, 60], ['Snare2_HitSN_v5_rr2_Mid.wav', 41, 60], ['Snare2_HitSN_v6_rr1_Mid.wav', 61, 80], ['Snare2_HitSN_v6_rr2_Mid.wav', 61, 80], ['Snare2_HitSN_v7_rr1_Mid.wav', 81, 105], ['Snare2_HitSN_v7_rr2_Mid.wav', 81, 105], ['Snare2_HitSN_v9_rr1_Mid.wav', 106, 127], ['Snare2_HitSN_v9_rr2_Mid.wav', 106, 127]], '37': [['Snare2_stick_v1_rr1_Mid.wav', 1, 127], ['Snare2_stick_v1_rr2_Mid.wav', 1, 127]], '39': [['Snare2_taps_v4_rr1_Mid.wav', 1, 127], ['Snare2_taps_v4_rr2_Mid.wav', 1, 127]], '40': [['Snare2_taps_v4_rr1_Mid.wav', 1, 127], ['Snare2_taps_v4_rr2_Mid.wav', 1, 127]], '42': [['HiHat_HitC_v1_rr1_Mid.wav', 1, 40], ['HiHat_HitC_v1_rr2_Mid.wav', 1, 40], ['HiHat_HitC_v2_rr1_Mid.wav', 41, 70], ['HiHat_HitC_v2_rr2_Mid.wav', 41, 70], ['HiHat_HitC_v3_rr1_Mid.wav', 71, 100], ['HiHat_HitC_v3_rr2_Mid.wav', 71, 100], ['HiHat_HitC_v4_rr1_Mid.wav', 101, 127], ['HiHat_HitC_v4_rr2_Mid.wav', 101, 127]], '44': [['HiHat_Close_rr1_Mid.wav', 1, 127], ['HiHat_Close_rr2_Mid.wav', 1, 127]], '46': [['HiHat_HitLoose_rr1_Mid.wav', 1, 90], ['HiHat_HitLoose_rr2_Mid.wav', 1, 90], ['HiHat_HitOC_rr5_Mid.wav', 1, 90], ['HiHat_HitO_rr1_Mid.wav', 91, 127], ['HiHat_HitO_rr2_Mid.wav', 91, 127]], '49': [['susCymb1_hit_mp1.wav', 1, 60], ['susCymb2_hit_mf1.wav', 1, 60], ['susCymb1_hit_f1.wav', 61, 100], ['susCymb2_hit_f1.wav', 61, 100], ['susCymb1_hit_fff1.wav', 101, 127], ['susCymb2_hit_fff1.wav', 101, 127]], '51': [['susCymb1_hit_stick_pp1.wav', 1, 45], ['susCymb2_hit_stick_pp1.wav', 1, 45], ['susCymb1_hit_stick_mp1.wav', 46, 75], ['susCymb2_hit_stick_mp1.wav', 46, 75], ['susCymb1_hit_stick_f1.wav', 76, 127], ['susCymb2_hit_stick_mf1.wav', 76, 127]], '53': [['susCymb1_hit_bell_pp1.wav', 1, 60], ['susCymb2_hit_bell_p1.wav', 1, 60], ['susCymb1_hit_bell_mf1.wav', 61, 127], ['susCymb2_hit_bell_f1.wav', 61, 127]]}


def _jazz_kit(dest: Path, log):
    # Versilian Community Sample Library (CC0): snare, kick, hi-hat, cymbal -> kit jazz
    base = "https://raw.githubusercontent.com/sgossner/VCSL/master/"
    log(f"  jazz kit ({len(JAZZ_KIT_FILES)} file) ...")
    for f in JAZZ_KIT_FILES:
        (dest / Path(f).name).write_bytes(_get(base + urllib.parse.quote(f)))
    return {"name": "Jazz Kit (VCSL)", "map": JAZZ_KIT_MAP, "release": 0.4, "max_len": 5, "vel_curve": 0.8,
            "credit": "Versilian Community Sample Library (VCSL) by Versilian Studios (CC0)"}


LIBRARIES = {"salamander_piano": _salamander, "upright_bass": _upright, "jazz_kit": _jazz_kit}


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
