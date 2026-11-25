"""Melodi dengan Anticipatory Music Transformer (Thickstun dkk., Stanford CRFM, Apache-2.0).

Model menulis melodi sambil 'mendengar' iringan (piano + bass) yang sudah dibuat engine sebagai
kontrol yang diantisipasi. Konstanta token mengikuti paket `anticipation` (Apache-2.0).
Tema head (A/B) ditulis sekali lalu diulang; solo ditulis bebas.
"""
from __future__ import annotations

import math
import random

from ..song import Note

# ---- konstanta vocab (dari anticipation/config.py & vocab.py) ----
TIME_RES = 100
MAX_TIME = TIME_RES * 100
MAX_DUR = TIME_RES * 10
MAX_PITCH = 128
MAX_NOTE = MAX_PITCH * 129
TIME_OFFSET = 0
DUR_OFFSET = TIME_OFFSET + MAX_TIME
NOTE_OFFSET = DUR_OFFSET + MAX_DUR
REST = NOTE_OFFSET + MAX_NOTE
CONTROL_OFFSET = NOTE_OFFSET + MAX_NOTE + 1
ATIME_OFFSET = CONTROL_OFFSET
ADUR_OFFSET = ATIME_OFFSET + MAX_TIME
ANOTE_OFFSET = ADUR_OFFSET + MAX_DUR
SPECIAL_OFFSET = ANOTE_OFFSET + MAX_NOTE
ANTICIPATE = SPECIAL_OFFSET + 2
DELTA = 5 * TIME_RES
WINDOW = 1017               # token riwayat maksimum (konteks 1024)
KEEP = 600                  # token yang dipertahankan saat jendela digeser

MODELS = {"small": "stanford-crfm/music-small-800k", "medium": "stanford-crfm/music-medium-800k",
          "large": "stanford-crfm/music-large-800k"}

_cache = {}


def load(size: str = "medium"):
    import torch
    from transformers import AutoModelForCausalLM
    if size in _cache:
        return _cache[size]
    dev = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
    m = AutoModelForCausalLM.from_pretrained(MODELS[size]).to(dev).eval()
    _cache[size] = m
    return m


def _tick(sec: float) -> int:
    return max(0, int(round(sec * TIME_RES)))


class _Stream:
    """Urutan token + KV cache dengan jendela geser."""

    def __init__(self, model, rng: random.Random, top_p: float, temperature: float):
        import torch
        self.torch = torch
        self.m = model
        self.rng = rng
        self.top_p, self.temp = top_p, temperature
        self.tokens: list[int] = []
        self.wstart = 0
        self.offset = 0
        self.past = None
        self.fed = 0          # jumlah token jendela yang sudah masuk cache
        self.logits = None
        self.gen = torch.Generator().manual_seed(rng.randrange(1 << 30))

    @staticmethod
    def _time(tok):
        return tok - ATIME_OFFSET if tok >= CONTROL_OFFSET else tok - TIME_OFFSET

    def _rel(self, i, tok):
        if (i - self.wstart) % 3 == 0:
            return tok - self.offset
        return tok

    def _refresh(self):
        torch = self.torch
        if len(self.tokens) - self.wstart > WINDOW:
            self.wstart = len(self.tokens) - KEEP
            self.wstart -= (self.wstart % 3)
            self.past = None
        if self.past is None:
            win = self.tokens[self.wstart:]
            self.offset = min((self._time(t) for t in win[0::3]), default=0)
            inp = [ANTICIPATE] + [self._rel(self.wstart + j, t) for j, t in enumerate(win)]
            with torch.no_grad():
                out = self.m(torch.tensor([inp], device=self.m.device), use_cache=True)
            self.past, self.logits = out.past_key_values, out.logits[0, -1].float().cpu()
            self.fed = len(win)
            return
        new = self.tokens[self.wstart + self.fed:]
        if new:
            inp = [self._rel(self.wstart + self.fed + j, t) for j, t in enumerate(new)]
            with torch.no_grad():
                out = self.m(torch.tensor([inp], device=self.m.device), past_key_values=self.past, use_cache=True)
            self.past, self.logits = out.past_key_values, out.logits[0, -1].float().cpu()
            self.fed += len(new)

    def push(self, toks):
        self.tokens.extend(toks)
        # jangan biarkan jendela meluap sebelum token berikutnya di-sample
        if len(self.tokens) - self.wstart > WINDOW:
            self._refresh()

    def sample(self, lo: int, hi: int, bias=None) -> int:
        """Sample token di rentang [lo, hi) (indeks absolut vocab, sebelum relativisasi waktu)."""
        torch = self.torch
        self._refresh()
        logits = self.logits.clone()
        mask = torch.full_like(logits, -math.inf)
        mask[lo:hi] = 0
        logits = logits / self.temp + mask
        if bias is not None:
            logits[lo:hi] += bias
        if self.top_p < 1.0:
            s, idx = torch.sort(logits, descending=True)
            cp = torch.cumsum(torch.softmax(s, -1), -1)
            rm = cp > self.top_p
            rm[1:] = rm[:-1].clone()
            rm[0] = False
            logits[idx[rm]] = -math.inf
        return int(torch.multinomial(torch.softmax(logits, -1), 1, generator=self.gen))


def compose_melody(arr, accompaniment: list[tuple[float, float, int, int]], lo: int, hi: int,
                   active_sections, rng: random.Random, size: str = "medium", program: int = 65,
                   top_p: float = 0.95, temperature: float = 1.0, density: float = 0.5, log=print) -> list[Note]:
    """accompaniment: (start_detik, durasi, nada, program GM). Mengembalikan Note melodi."""
    import torch
    from ..theory import CHORD_SCALES, CHORDS
    model = load(size)
    st = _Stream(model, rng, top_p, temperature)
    instr = program
    # kontrol terurut waktu
    ctrl = sorted(accompaniment)
    ci = 0

    def feed_controls(until_tick):
        nonlocal ci
        while ci < len(ctrl) and _tick(ctrl[ci][0]) - DELTA <= until_tick:
            s, d, p, prog = ctrl[ci]
            st.push([ATIME_OFFSET + _tick(s), ADUR_OFFSET + max(1, min(MAX_DUR - 1, _tick(d))),
                     ANOTE_OFFSET + prog * 128 + p])
            ci += 1

    def push_event(s, d, p):
        feed_controls(_tick(s))
        st.push([TIME_OFFSET + _tick(s), DUR_OFFSET + max(1, min(MAX_DUR - 1, _tick(d))), NOTE_OFFSET + instr * 128 + p])

    themes: dict[str, list[tuple[float, float, int]]] = {}
    out: list[Note] = []
    cur = 0
    bpb = arr.beats_per_bar
    total = len(arr.sections)
    for si, sec in enumerate(arr.sections):
        t0 = arr.time(sec.start_bar * bpb, False)
        t1 = arr.time(sec.end_bar * bpb, False)
        if not active_sections(sec):
            cur = _tick(t1)
            feed_controls(cur)
            continue
        log(f"    AI melodi: bagian {si + 1}/{total} ({sec.kind} {sec.label})")
        key = sec.label if sec.kind == "head" else None
        if key and key in themes:
            for rel, d, p in themes[key]:
                push_event(t0 + rel, d, p)
                out.append(Note(t0 + rel, d, p, 0))
            cur = _tick(t1)
            continue
        mine = []
        cur = max(cur, _tick(t0))
        end = _tick(t1) if sec is not arr.sections[-1] else _tick(t1 + 2)
        while True:
            feed_controls(cur)
            # waktu: tidak mundur, tidak lompat > 2 bar
            gap_max = _tick(2 * bpb * arr.beat_sec)
            t_lo, t_hi = cur - st.offset, min(cur - st.offset + gap_max, MAX_TIME - 1)
            if t_lo >= MAX_TIME - 1:
                st._refresh()
                t_lo, t_hi = cur - st.offset, min(cur - st.offset + gap_max, MAX_TIME - 1)
            # sample dihitung pada waktu relatif terhadap offset jendela
            st._refresh()
            # monofonik: nada berikutnya minimal ~1/16 ketukan setelah nada sebelumnya
            min_gap = _tick(arr.beat_sec / 4) if mine or out else 0
            t_lo = cur - st.offset + (min_gap if out and _tick(out[-1].start) >= cur - 1 else 0)
            t_hi = min(t_lo + gap_max, MAX_TIME - 1)
            tt = st.sample(TIME_OFFSET + t_lo, TIME_OFFSET + t_hi + 1) - TIME_OFFSET + st.offset
            if tt >= end:
                break
            st.push([TIME_OFFSET + tt])
            dd = st.sample(DUR_OFFSET + 4, DUR_OFFSET + min(MAX_DUR, _tick(4 * arr.beat_sec) + 1)) - DUR_OFFSET
            st.push([DUR_OFFSET + dd])
            # nada: hanya instrumen melodi & rentang; dorong ke nada skala akor saat itu
            c = arr.chord_at(tt / TIME_RES / arr.beat_sec - 1e-3)
            pcs = {(c.root + i) % 12 for i in CHORD_SCALES[c.quality]} | {(c.root + i) % 12 for i in CHORDS[c.quality]}
            base = NOTE_OFFSET + instr * 128
            ctones = {(c.root + i) % 12 for i in CHORDS[c.quality]}
            strong = abs((tt / TIME_RES / arr.beat_sec) % 1) < 0.08
            target = (lo + hi) / 2 + 2
            bias = torch.tensor([(0.0 if (p % 12) in pcs else -2.5) + (0.6 if strong and (p % 12) in ctones else 0.0)
                                 - abs(p - target) * 0.06 for p in range(lo, hi + 1)])
            pp = st.sample(base + lo, base + hi + 1, bias) - base
            st.push([NOTE_OFFSET + instr * 128 + pp])
            s = tt / TIME_RES
            d = min(dd / TIME_RES, max(0.05, end / TIME_RES - s))
            out.append(Note(s, d, pp, 0))
            mine.append((s - t0, d, pp))
            cur = tt
        if key:
            themes[key] = mine
        cur = max(cur, _tick(t1))
    return _tidy(arr, out)


def _tidy(arr, notes: list[Note], snap: float = 0.7) -> list[Note]:
    """Tarik waktu ke grid swing 8th (sebagian), lalu pastikan monofonik (tanpa tumpukan nada)."""
    bs = arr.beat_sec
    for n in notes:
        b = n.start / bs
        w = int(b)
        cands = [w, w + arr.swing, w + 1]
        g = min(cands, key=lambda x: abs(x - b))
        if abs(g - b) * bs < 0.12:
            n.start = (b + (g - b) * snap) * bs
    notes.sort(key=lambda n: n.start)
    clean = []
    for n in notes:
        if clean and n.start - clean[-1].start < 0.06:
            # dua nada hampir bersamaan: simpan yang lebih tinggi (garis melodi)
            if n.key > clean[-1].key:
                clean[-1] = n
            continue
        clean.append(n)
    for a, b in zip(clean, clean[1:]):
        a.dur = max(0.05, min(a.dur, b.start - a.start - 0.01))
    return clean
