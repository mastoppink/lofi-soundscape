"""Test cepat (tanpa soundfont) + render end-to-end bila soundfont tersedia."""
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from lofigen import SR
from lofigen.ambience import Ambience
from lofigen.cli import DEFAULT_SF, ROOT, load_preset, main, parse_duration
from lofigen.composer import compose
from lofigen.fx import StreamLimiter, Vinyl, sidechain
from lofigen.theory import voice_chord


def test_parse_duration():
    assert parse_duration("1h") == 3600
    assert parse_duration("1h30m") == 5400
    assert parse_duration("45s") == 45
    assert parse_duration("90") == 90


def test_voicing_in_range():
    for pc in range(12):
        v = voice_chord(pc, "m7", None)
        assert all(48 <= n <= 76 for n in v) and v == sorted(v)


def test_compose_deterministic():
    opts = load_preset("rainy_cafe")["music"]
    a, b = compose(42, opts), compose(42, opts)
    assert a.title == b.title and a.bpm == b.bpm
    assert [n.key for n in a.tracks["keys"]] == [n.key for n in b.tracks["keys"]]
    assert compose(43, opts).tracks["keys"] != a.tracks["keys"]
    assert 90 < a.duration < 240
    assert all(n.start >= 0 for t in a.tracks.values() for n in t)


def test_all_presets_load():
    for p in (ROOT / "presets").glob("*.yaml"):
        d = load_preset(p.stem)
        assert {"keys", "bass", "drums"} <= set(d["instruments"])


def test_limiter_streaming_ceiling():
    lim = StreamLimiter(gain_db=12, ceiling_db=-1)
    x = (np.random.default_rng(0).standard_normal((SR * 3, 2)) * 0.3).astype(np.float32)
    out = np.concatenate([lim(x[i:i + 10_000]) for i in range(0, len(x), 10_000)] + [lim(x[:0], final=True)])
    assert len(out) == len(x)
    assert np.abs(out).max() <= 10 ** (-1 / 20) + 1e-6


def test_sidechain_and_vinyl():
    x = np.ones((SR, 2), np.float32)
    y = sidechain(x, [0.5], depth=0.5)
    assert y[int(0.5 * SR)].max() < 0.6 and y[0].max() == 1.0
    v = Vinyl(1)(SR, 1.0)
    assert v.shape == (SR, 2) and np.isfinite(v).all()


def test_ambience_synth_and_samples(tmp_path):
    a = Ambience({"rain": 0.5, "wind": 0.5, "ocean": 0.5, "fire": 0.5, "nothing": 0.5}, tmp_path, 1, log=lambda *_: None)
    x = a.read(SR * 2)
    assert x.shape == (SR * 2, 2) and np.isfinite(x).all() and np.abs(x).max() > 0
    (tmp_path / "cafe").mkdir()
    sf.write(tmp_path / "cafe" / "c.wav", np.random.default_rng(0).standard_normal((SR * 3, 2)) * 0.1, 22050)
    (tmp_path / "thunder").mkdir()
    sf.write(tmp_path / "thunder" / "t.wav", np.random.default_rng(1).standard_normal((SR * 12, 1)) * 0.1, SR)
    a = Ambience({"cafe": 0.5, "thunder": {"volume": 1, "every": 1}}, tmp_path, 1, log=lambda *_: None)
    y = np.concatenate([a.read(SR) for _ in range(30)])
    assert np.isfinite(y).all() and np.abs(y).max() > 0


@pytest.mark.skipif(not DEFAULT_SF.exists(), reason="soundfont belum diunduh (python -m lofigen setup)")
def test_render_end_to_end(tmp_path):
    out = tmp_path / "mix.wav"
    main(["render", "--preset", "night_study", "--duration", "40s", "--seed", "1", "--out", str(out)])
    x, sr = sf.read(out)
    assert sr == SR and len(x) == 40 * SR
    assert np.abs(x).max() <= 0.9
    assert out.with_suffix(".tracklist.txt").read_text().startswith("00:00 ")
