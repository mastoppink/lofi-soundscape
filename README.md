# lofigen: generator musik lofi + soundscape untuk YouTube

Membuat mix lofi panjang (30 menit – berjam-jam) secara prosedural: setiap "lagu" dikomposisi
dari seed (akor jazzy, bass, drum ber-swing, melodi), dimainkan dengan instrumen **sampel asli**
dari SoundFont, diberi efek lofi (tape wow/flutter, saturasi, filter, crackle vinyl, sidechain),
lalu dicampur dengan **rekaman ambience** (hujan, kafe, ombak, api unggun …).

Hasil: file WAV + tracklist dengan timestamp untuk deskripsi YouTube, dan (opsional) MP4 siap upload.
Render ~15–20× lebih cepat dari realtime (1 jam ≈ 3–4 menit) dengan memori kecil.

## Instalasi

Butuh Python 3.10+ dan (untuk video) ffmpeg.

**Mac**
```bash
brew install python ffmpeg
```
**Windows**: instal Python dari python.org, lalu `winget install ffmpeg`.
**Linux**: `sudo apt install python3-venv ffmpeg libsndfile1`.

Lalu (semua OS):
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install --no-deps tinysoundfont
python -m lofigen setup          # unduh soundfont GeneralUser GS (~32 MB) + buat folder sampel
```

Lalu isi `samples/` dengan rekaman ambience CC0: lihat [samples/README.md](samples/README.md).

## Pemakaian

```bash
python -m lofigen presets                                  # lihat daftar preset
python -m lofigen render --preset rainy_cafe --duration 1h --out mix.wav
python -m lofigen render --preset night_study --duration 2h --seed 42 --cover cover.jpg --video
```

Opsi `render`:

| Opsi | Arti |
|---|---|
| `--preset` | `rainy_cafe`, `night_study`, `beach_sunset`, `cozy_fireplace`, atau path ke file `.yaml` |
| `--duration` | `30m`, `1h`, `2h30m`, … |
| `--seed` | angka; seed sama = hasil sama persis (tercetak di log) |
| `--out` | `.wav` atau `.flac` (FLAC ~50% lebih kecil, juga diterima YouTube) |
| `--lofi` | 0..1, seberapa "kotor"/tape |
| `--mood` | 0 sendu (minor) .. 1 ceria (mayor) |
| `--music-volume`, `--ambience-volume` | pengali volume |
| `--cover gambar.jpg --video` | buat juga `.mp4` 1080p (gambar diam) |

Output tambahan: `<nama>.tracklist.txt`, tinggal copy ke deskripsi YouTube.

## Membuat preset sendiri

Salin salah satu file di `presets/` lalu ubah. Instrumen memakai nomor General MIDI
(0 Grand Piano, 4 Rhodes, 11 Vibraphone, 24 Nylon Guitar, 32/33 bass, 73 Flute, 89 Warm Pad;
drum bank 128: 0 Standard, 8 Room, 32 Jazz, 40 Brush). Bisa juga pakai soundfont lain yang lebih
realistis (mis. piano `.sf2` khusus) lewat `--soundfont path.sf2`.

## Struktur

```
lofigen/
  theory.py     akor, progression, voicing
  composer.py   komposisi lagu dari seed (struktur, keys, bass, drum, melodi)
  sfrender.py   render not → audio via SoundFont
  fx.py         efek per instrumen, master lofi, vinyl, limiter
  ambience.py   layer rekaman (loop crossfade) + cadangan sintetis
  render.py     playlist, crossfade antar lagu, tulis per potongan, tracklist
  video.py      ffmpeg → MP4
  cli.py        command line
presets/        preset YAML
samples/        rekaman ambience (isi sendiri)
```

## Lisensi aset

- **GeneralUser GS** oleh S. Christian Collins: bebas dipakai, termasuk untuk musik komersial.
- Musik yang dihasilkan adalah milikmu. Pastikan sampel ambience berlisensi CC0/komersial.
