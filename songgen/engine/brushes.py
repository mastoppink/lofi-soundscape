"""Kit brush dari rekaman asli Freesound (CC0), dipotong otomatis:
- tepukan snare brush & kick: 'Brushes on Drum Kit Sample Set' (Srirachasocks, freesound #843460)
- sapuan melingkar: 'MuseScore_Brush_kit' brush stirring/swirling (freesound #556129)
Ditambah hi-hat & ride dari VCSL (CC0)."""
from __future__ import annotations

import io
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf

from .. import SR

SOURCES = {
    "hits": "https://cdn.freesound.org/previews/843/843460_16471070-hq.mp3",
    "swirl": "https://cdn.freesound.org/previews/556/556129_11237444-hq.mp3",
}
UA = {"User-Agent": "Mozilla/5.0 (songgen)"}


def _load(url_or_path) -> np.ndarray:
    if str(url_or_path).startswith("http"):
        data = urllib.request.urlopen(urllib.request.Request(url_or_path, headers=UA), timeout=120).read()
        import librosa
        y, _ = librosa.load(io.BytesIO(data), sr=SR, mono=False)
    else:
        import librosa
        y, _ = librosa.load(str(url_or_path), sr=SR, mono=False)
    y = np.atleast_2d(y)
    if y.shape[0] == 1:
        y = np.vstack([y, y])
    return y.T.astype(np.float32)


def _onsets(mono):
    import librosa
    return librosa.onset.onset_detect(y=mono, sr=SR, units="samples", backtrack=True)


def _fade(x, fi=0.002, fo=0.03):
    a, b = int(fi * SR), int(fo * SR)
    x = x.copy()
    x[:a] *= np.linspace(0, 1, a)[:, None]
    x[-b:] *= np.linspace(1, 0, b)[:, None]
    return x


def build(dest: Path, hits_src=SOURCES["hits"], swirl_src=SOURCES["swirl"]) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    m: dict[str, list] = {"39": [], "40": [], "36": []}
    hits = _load(hits_src)
    mono = hits.mean(1)
    on = _onsets(mono)

    def slices(t0, t1, max_len):
        seg = [o for o in on if t0 * SR <= o < t1 * SR]
        out = []
        for i, o in enumerate(seg):
            end = min(seg[i + 1] if i + 1 < len(seg) else int(t1 * SR), o + int(max_len * SR))
            if end - o > int(0.05 * SR):
                out.append(_fade(hits[o:end]))
        return out

    # tepukan snare brush (detik 24.6-59.8) -> 3 layer velocity berdasar kekerasan
    for key, t0, t1, ml in (("39", 24.6, 59.8, 0.8), ("36", 125.3, 143.0, 0.9)):
        sl = slices(t0, t1, ml)
        peaks = np.array([np.abs(s).max() for s in sl])
        order = np.argsort(peaks)
        groups = np.array_split(order, 3)
        bounds = [(1, 50), (51, 85), (86, 127)]
        for g, (lo, hi) in zip(groups, bounds):
            for j, idx in enumerate(g[:8]):
                f = f"brush_{'tap' if key == '39' else 'kick'}_v{bounds.index((lo, hi)) + 1}_rr{j + 1}.wav"
                sf.write(str(dest / f), sl[idx], SR)
                m[key].append([f, lo, hi])
    # sapuan: potongan 0.55 dtk dari bagian yang stabil
    sw = _load(swirl_src)
    rms = np.sqrt(np.convolve(sw.mean(1) ** 2, np.ones(2048) / 2048, mode="same"))
    win = int(0.55 * SR)
    cands = []
    for s in range(0, len(sw) - win, win // 2):
        r = rms[s:s + win]
        if r.mean() > rms.max() * 0.15 and r.std() / (r.mean() + 1e-9) < 0.6:
            cands.append((r.mean(), s))
    cands.sort()
    groups = np.array_split(np.arange(len(cands)), 3)
    for gi, (g, (lo, hi)) in enumerate(zip(groups, [(1, 45), (46, 80), (81, 127)])):
        for j, idx in enumerate(g[:6]):
            s = cands[idx][1]
            x = sw[s:s + win].copy()
            env = np.sin(np.linspace(0, np.pi, win)) ** 0.7     # masuk-keluar halus seperti gerak melingkar
            f = f"brush_swirl_v{gi + 1}_rr{j + 1}.wav"
            sf.write(str(dest / f), x * env[:, None], SR)
            m["40"].append([f, lo, hi])
    return m
