# Sampel ambience

Taruh rekaman asli di folder sesuai nama layer (`rain/`, `cafe/`, `ocean/`, …).
Format: `.wav`, `.flac`, `.ogg`, `.mp3`, `.aiff`. Satu folder boleh berisi beberapa file;
generator akan memutarnya bergantian dari titik acak dengan crossfade 4 detik, jadi tidak
terdengar berulang. Volume otomatis dinormalisasi.

Kalau folder kosong, `rain`, `wind`, `ocean`, dan `fire` memakai versi sintetis (cadangan,
kurang realistis). `cafe`, `birds`, `thunder` hanya bunyi kalau ada rekamannya.

## Lisensi: wajib aman untuk YouTube (monetisasi)

Gunakan rekaman **CC0 / public domain** atau lisensi yang mengizinkan pemakaian komersial
tanpa atribusi. Catat sumbernya di `samples/CREDITS.md`.

| Sumber | Cara cari |
|---|---|
| Freesound.org | cari mis. `rain window`, lalu filter **License: Creative Commons 0** |
| Pixabay Sounds | semua sound effect bebas dipakai komersial |
| BBC Sound Effects | ⚠️ hanya untuk penggunaan non-komersial: **jangan** untuk channel monetisasi |

## Rekomendasi isi

| Folder | Cari | Tips |
|---|---|---|
| `rain/` | rain on window, light rain, rain on roof | rekaman ≥ 1 menit, tanpa petir/suara orang |
| `cafe/` | coffee shop ambience, cafe murmur | tanpa musik latar (hindari copyright!) |
| `ocean/` | gentle waves, beach ambience | |
| `birds/` | morning birds, forest birds | |
| `fire/` | fireplace crackling, campfire | |
| `wind/` | soft wind, night wind | |
| `thunder/` | distant thunder | volume kecil saja (0.1–0.2) |

Untuk memakai layer baru, cukup buat folder baru lalu tambahkan namanya di bagian
`ambience:` pada preset.
