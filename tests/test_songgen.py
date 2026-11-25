"""Test engine songgen (cepat, tanpa soundfont) + render end-to-end bila soundfont ada."""
import json

import numpy as np
import pytest
import soundfile as sf

from songgen import SR
from songgen.cli import DEFAULT_SF, main, parse_duration
from songgen.engine.arrangement import parse_phrase
from songgen.engine.fx import StreamLimiter
from songgen.engine.genres import jazz
from songgen.engine.mixer import compose, layer_seed
from songgen.engine.song import SongSpec
from songgen.engine.theory import CHORDS, voice


def test_parse_duration():
    assert parse_duration("5m") == 300 and parse_duration("1h30m") == 5400 and parse_duration("45") == 45


def test_parse_phrase():
    bars = parse_phrase("I:maj7 | ii:m7/2 V:7/2 | #I:dim7 | bVII:7")
    assert bars[0] == [(0, "maj7", 4.0)]
    assert bars[1] == [(2, "m7", 2.0), (7, "7", 2.0)]
    assert bars[2][0][0] == 1 and bars[3][0][0] == 10


def test_voicing_is_chord_tones_and_in_range():
    for root in range(12):
        for q in ("maj7", "m7", "7", "m7b5", "7alt"):
            v = voice(root, q, None, 50, 76)
            pcs = {(root + i) % 12 for i in CHORDS[q]}
            assert all(n % 12 in pcs for n in v) and all(50 <= n <= 76 for n in v)


@pytest.mark.parametrize("valence,energy", [(0.1, 0.1), (0.5, 0.5), (0.9, 0.9)])
def test_jazz_arrangement(valence, energy):
    spec = jazz.default_spec(valence, energy, 300, 7)
    arr = jazz.arrange(spec)
    assert 200 < arr.duration < 420              # mendekati 5 menit
    assert arr.sections[0].kind == "intro" and arr.sections[-1].kind == "ending"
    assert arr.chords[0].start == 0
    # akor berurutan tanpa celah
    for a, b in zip(arr.chords, arr.chords[1:]):
        assert abs(a.end - b.start) < 1e-6
    if valence < 0.35:
        assert arr.mode == "minor"
    if valence > 0.65:
        assert arr.mode == "major"
    if energy < 0.2:
        assert arr.tempo < 90


def test_long_duration_adds_solos():
    short = jazz.arrange(jazz.default_spec(0.5, 0.5, 180, 1))
    long = jazz.arrange(jazz.default_spec(0.5, 0.5, 900, 1))
    assert long.total_bars > short.total_bars
    assert any(s.kind == "solo" for s in long.sections)


def test_compose_all_layers_reasonable():
    spec = jazz.default_spec(0.6, 0.6, 240, 3)
    for l in spec.layers:
        l.enabled = True
    arr = jazz.arrange(spec)
    notes = compose(spec, arr)
    for l in spec.layers:
        ns = notes[l.id]
        assert ns, l.id
        assert all(0 <= n.start < arr.duration and 0 < n.vel <= 127 and 0 <= n.key <= 127 for n in ns)
    assert all(28 <= n.key <= 55 for n in notes["bass"])


def test_reroll_changes_only_that_layer():
    spec = jazz.default_spec(0.5, 0.5, 200, 5)
    arr = jazz.arrange(spec)
    a = compose(spec, arr)
    spec.layer("melody").seed = layer_seed(spec, spec.layer("melody")) + 1
    b = compose(spec, arr)
    assert [n.key for n in a["melody"]] != [n.key for n in b["melody"]]
    for lid in ("comping", "bass", "drums"):
        assert [(n.start, n.key) for n in a[lid]] == [(n.start, n.key) for n in b[lid]]


def test_head_theme_repeats():
    spec = jazz.default_spec(0.6, 0.5, 300, 9)
    arr = jazz.arrange(spec)
    lead = compose(spec, arr)["melody"]
    bs = arr.beat_sec
    a_secs = [s for s in arr.sections if s.kind == "head" and s.label == "A"][:2]

    def rel(sec):
        st, en = arr.time(sec.start_bar * 4), arr.time(sec.end_bar * 4)
        return [(n.key, round((n.start - st) / bs)) for n in lead if st - 0.05 <= n.start < en - 0.05]

    assert rel(a_secs[0]) == rel(a_secs[1]) and rel(a_secs[0])


def test_spec_json_roundtrip(tmp_path):
    spec = jazz.default_spec(0.3, 0.7, 300, 2)
    p = tmp_path / "s.json"
    spec.save(p)
    back = SongSpec.load(p)
    assert back.to_dict() == spec.to_dict()
    assert json.loads(p.read_text())["layers"][0]["instrument"]["preset"] == spec.layers[0].instrument.preset


def test_limiter_ceiling():
    lim = StreamLimiter(gain_db=12, ceiling_db=-1)
    x = (np.random.default_rng(0).standard_normal((SR * 2, 2)) * 0.3).astype(np.float32)
    out = np.concatenate([lim(x[i:i + 9000]) for i in range(0, len(x), 9000)] + [lim(x[:0], final=True)])
    assert len(out) == len(x) and np.abs(out).max() <= 10 ** (-1 / 20) + 1e-6


@pytest.mark.skipif(not DEFAULT_SF.exists(), reason="soundfont belum diunduh (python -m songgen setup)")
def test_render_preview_end_to_end(tmp_path):
    out = tmp_path / "x.wav"
    main(["render", "--valence", "0.4", "--energy", "0.6", "--seed", "3", "--preview", "20s", "-o", str(out),
          "--stems", str(tmp_path / "stems")])
    x, sr = sf.read(out)
    assert sr == SR and 19 * SR <= len(x) <= 21 * SR
    assert 0.3 < np.abs(x).max() <= 0.9
    assert (tmp_path / "stems" / "bass.wav").exists()
    assert out.with_suffix(".json").exists()
    main(["render", str(out.with_suffix(".json")), "--preview", "10s", "--solo", "bass", "-o", str(tmp_path / "b.wav")])
    assert sf.info(str(tmp_path / "b.wav")).duration == pytest.approx(10, abs=0.5)


def test_ai_tidy_monophonic_and_snapped():
    from songgen.engine.ai.amt import _tidy
    from songgen.engine.song import Note
    arr = jazz.arrange(jazz.default_spec(0.5, 0.5, 200, 1))
    bs = arr.beat_sec
    notes = [Note(0.0, 2.0, 60, 70), Note(0.01, 1.0, 64, 70), Note(bs * 1.03, 3.0, 62, 70), Note(bs * 2.1, 0.5, 65, 70)]
    out = _tidy(arr, notes)
    assert [n.key for n in out] == [64, 62, 65]          # nada bersamaan -> ambil yang tertinggi
    for a, b in zip(out, out[1:]):
        assert a.start + a.dur <= b.start                  # tidak bertumpuk
    assert abs(out[1].start - bs) < abs(bs * 1.03 - bs)    # ditarik ke grid
