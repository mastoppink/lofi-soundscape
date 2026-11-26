# songgen: generator lagu instrumental berbasis layer

Membuat lagu instrumental (jazz dulu; bossa nova & cinematic menyusul) **layer per layer**:
piano, bass, drum, melodi, strings, dan seterusnya. Setiap layer punya instrumen, gaya main,
kepadatan, volume, pan, dan reverb sendiri, dan bisa **diacak ulang sendiri** tanpa mengubah
layer lain. Mood diatur dengan dua slider: **valence** (sedih ↔ senang) dan **energy**
(tenang ↔ enerjik).

Bawaan jazz adalah **piano trio** dengan instrumen rekaman asli: Salamander Grand Piano
(16 tingkat kekuatan tekan), upright bass pizzicato dari VSCO-2, dan drum kit dari VCSL (snare, kick, hi-hat, cymbal rekaman asli). Instrumen lain memakai
SoundFont GeneralUser GS. GUI di browser menyusul (tahap 3); saat ini dipakai lewat command line.

> Status: **tahap 1**: engine berbasis layer + genre jazz. Lihat [Rencana](#rencana).

## Instalasi

**Mac:** `brew install python ffmpeg` · **Windows:** python.org + `winget install ffmpeg` ·
**Linux:** `sudo apt install python3-venv ffmpeg`

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install --no-deps tinysoundfont
python -m songgen setup          # unduh soundfont + library piano, bass, drum (~140 MB)
```

## Pemakaian

```bash
# langsung render: jazz sedih & tenang, ±5 menit
python -m songgen render --genre jazz --valence 0.2 --energy 0.3 --duration 5m -o lagu.wav

# preview 30 detik pertama saja
python -m songgen render --valence 0.7 --energy 0.6 --preview 30s -o coba.wav
```

Setiap render menyimpan juga `lagu.json`, berisi semua pengaturan lagu dan layer. File ini
bisa diedit lalu dirender ulang:

```bash
python -m songgen info lagu.json                 # lihat struktur & akor
python -m songgen reroll lagu.json --layer lead  # acak ulang melodi saja
python -m songgen render lagu.json -o lagu_v2.wav
python -m songgen render lagu.json --solo bass,drums --preview 30s   # dengar sebagian layer
python -m songgen render lagu.json --mute strings --stems stems/     # simpan audio per layer
```

### Ekspor MIDI (untuk GarageBand / Logic)

```bash
python -m songgen midi --valence 0.3 --energy 0.3 -o lagu.mid             # semua layer
python -m songgen midi lagu.json --no-drums -o lagu.mid                    # tanpa drum (pakai Drummer GarageBand)
```

Satu track per layer, tempo & penanda bagian lagu ikut tersimpan; `lagu.txt` berisi struktur dan akor.

### Melodi ditulis AI (opsional)

Melodi bisa ditulis oleh **Anticipatory Music Transformer** (Stanford CRFM, Apache-2.0). Model ini
"mendengar" piano dan bass yang sudah dibuat, lalu menulis melodi di atasnya. Tema head ditulis
sekali lalu diulang; solo ditulis bebas. Model diunduh otomatis saat pertama dipakai
(small ±0,5 GB, medium ±1,4 GB).

```bash
pip install -r requirements-ai.txt
python -m songgen render --valence 0.3 --energy 0.4 --ai -o lagu.wav               # model medium
python -m songgen render --valence 0.3 --energy 0.4 --ai --ai-model small -o lagu.wav
```

Di file `.json`, layer melodi dengan `"style": "ai"` memakai AI; `reroll` layer itu menghasilkan
melodi AI yang lain.

Atau buat file lagu dulu tanpa render: `python -m songgen new --valence 0.4 --energy 0.5 -o lagu.json`.

### Opsi global

| Opsi | Arti |
|---|---|
| `--valence` | 0 sedih (minor, akor gelap) .. 1 senang (mayor, cerah) |
| `--energy` | 0 tenang (ballad, brush) .. 1 enerjik (up-tempo, ride) |
| `--duration` | target durasi, mis. `3m`, `5m`, `10m` (lagu berhenti di akhir frasa terdekat) |
| `--seed` | angka; seed sama = lagu sama persis |
| `--tempo`, `--key`, `--mode`, `--swing` | menimpa nilai otomatis |
| `--lofi` | 0 bersih .. 1 efek kaset/vinyl |

### Layer di file `.json`

```json
{ "id": "lead", "role": "melody",
  "instrument": {"preset": 66, "bank": 0, "drums": false, "name": "Tenor Sax"},
  "style": "head+solo", "density": 0.5, "volume": 0.8, "pan": 0.2, "reverb": 0.3,
  "octave": 0, "sections": ["head", "solo", "ending"], "seed": null,
  "enabled": true, "mute": false, "solo": false }
```

| Peran (`role`) | Gaya (`style`) jazz |
|---|---|
| `chords` | `comping`, `ballad`, `stabs`, `sustain` |
| `bass` | `walking`, `two`, `pedal` |
| `drums` | `ride`, `brush`, `sparse` |
| `melody` | `head+solo`, `ai` (ditulis model AI), `head` (tema), `solo` (improvisasi), `fills` |
| `pad` | `sustain`, `swell` |

Field `lib` memilih library rekaman asli (`salamander_piano`, `upright_bass`); kalau kosong,
instrumen dimainkan dari SoundFont dengan nomor General MIDI, mis. 0 Grand Piano, 4 Rhodes, 11 Vibraphone,
26 Jazz Guitar, 32 Acoustic Bass, 56 Trumpet, 59 Muted Trumpet, 65 Alto Sax, 66 Tenor Sax,
73 Flute, 49 Strings. Drum: `bank 128`, preset 32 Jazz, 40 Brush.

`sections` menentukan di bagian lagu mana layer bunyi: `intro`, `head`, `solo`, `ending`.

## Cara kerja (jazz)

1. **Bentuk lagu:** intro 4 bar → head (tema AABA 32 bar) → solo (jumlah putaran menyesuaikan
   durasi) → head → ending.
2. **Harmoni:** frasa A dan B dipilih dari pustaka progresi (ii-V-I, turnaround, rhythm-changes
   bridge, minor ii-V); mood menentukan mayor/minor, tempo, dan swing.
3. **Tiap layer** dibuat oleh generator perannya dengan seed sendiri:
   - piano comping (pola Charleston, voicing rootless, voice leading)
   - walking bass (root di awal akor, approach kromatik ke akor berikutnya)
   - drum ride "spang-a-lang" / brush
   - melodi: **tema berbasis motif** yang diulang tiap A, improvisasi saat solo
4. **Mix:** level otomatis per peran, pan, satu reverb ruangan bersama, kompresor master,
   limiter (puncak -1 dB).

## Struktur

```
songgen/
  cli.py
  engine/
    song.py          SongSpec + Layer (JSON)
    arrangement.py   tempo, kunci, bagian lagu, akor per ketukan, swing
    theory.py        akor, skala, voicing
    genres/jazz.py   bentuk, progresi, nilai bawaan layer
    roles/           chords, bass, drums, melody, pad
    mixer.py         render per layer + mix
    render.py        pipeline lengkap
    ai/amt.py        melodi AI (Anticipatory Music Transformer)
    sampler.py       pemutar multi-sampel (velocity layer, round robin, release)
    libraries.py     unduh library instrumen
    sfrender.py, fx.py, ambience.py, video.py
tests/
```

## Rencana

1. ✅ Engine berbasis layer + jazz
2. Bossa nova & cinematic
3. GUI mode Simpel (browser, localhost)
4. GUI mode Advanced + simpan preset
5. Mix panjang 1–3 jam, tracklist, MP4, layer ambience
6. Ekspor MIDI & stem

## Lisensi aset

- **Salamander Grand Piano V3** oleh Alexander Holm: **CC BY 3.0**. Wajib dicantumkan di
  deskripsi video, mis.: `Piano samples: Salamander Grand Piano V3 by Alexander Holm (CC BY 3.0)`.
- **VSCO-2 CE** (upright bass) dan **VCSL** (drum) oleh Versilian Studios: CC0.
- **Brush kit**: rekaman Freesound CC0 (#843460 "Brushes on Drum Kit Sample Set" oleh Srirachasocks,
  #556129 brush swirl), dipotong otomatis oleh `setup`.
- **GeneralUser GS** oleh S. Christian Collins: bebas dipakai, termasuk untuk musik komersial.
Sampel ambience di `samples/`: public domain/CC0 (lihat `samples/CREDITS.md`).
