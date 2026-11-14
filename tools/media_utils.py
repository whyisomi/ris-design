#!/usr/bin/env python3
"""
Общие утилиты для работы с медиа портфолио РИС-Дизайн.

Используется скриптами:
  tools/optimize.py        — сборка медиа сайта и дизайн-проектов
  /home/iso/tg-tools/...   — сборка раздела «Реализованные проекты» из Telegram
"""

import pathlib

from PIL import Image

SITE = pathlib.Path(__file__).resolve().parent.parent

FULL_MAX = 1400
FULL_Q = 82
THUMB_MAX = 420
THUMB_Q = 72
COVER_MAX = 1200

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}


def slugify(text):
    """Кириллица -> латиница, пробелы/пунктуация -> дефис."""
    import re

    out = []
    for ch in text.lower():
        if ch in TRANSLIT:
            out.append(TRANSLIT[ch])
        elif ch.isdigit():
            out.append(ch)
        elif ch in " \t":
            out.append("-")
    return re.sub(r"-{2,}", "-", "".join(out)).strip("-")


def convert(src, dst, max_side, quality):
    """JPEG/PNG -> WebP с ограничением по длинной стороне (без увеличения)."""
    dst = pathlib.Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        if max(w, h) > max_side:
            scale = max_side / max(w, h)
            im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        im.save(dst, "WEBP", quality=quality, method=6)
    return dst.stat().st_size
