"""Registry genre. Setiap genre menyediakan: default_spec(), arrange(), dan gaya bawaan per peran."""
from __future__ import annotations

from . import jazz

GENRES = {"jazz": jazz}


def get(name: str):
    if name not in GENRES:
        raise ValueError(f"genre '{name}' belum ada. Pilihan: {', '.join(GENRES)}")
    return GENRES[name]
