#!/usr/bin/env python3
"""Генерирует sitemap-images.xml из media/portfolio/manifest.js.

Запуск:
    python3 tools/make_image_sitemap.py
"""

import json
import pathlib
from urllib.parse import quote
from xml.sax.saxutils import escape

SITE = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://ris-design63.ru/"
MANIFEST = SITE / "media" / "portfolio" / "manifest.js"
OUT = SITE / "sitemap-images.xml"

# сколько фото на проект включать (кроме обложки), чтобы карта не разрасталась
PER_PROJECT = 12

MAIN_IMAGES = [
    ("photo1.webp", "Дизайн интерьера в Самаре — РИС-Дизайн"),
    ("photo2.webp", "Гостиная с зелёными фасадами и стеклянной перегородкой"),
    ("photo3.webp", "Кухня-гостиная в проекте РИС-Дизайн"),
    ("photo4.webp", "Спальня с тёплой подсветкой"),
    ("photo5.webp", "Детская комната в современном стиле"),
    ("intro.webp", "Дизайнер интерьера за работой над проектом"),
    ("portfolio-hero.webp", "Портфолио дизайн-проектов РИС-Дизайн"),
]


def load_projects():
    text = MANIFEST.read_text(encoding="utf-8")
    data = text[text.index("=") + 1:].rstrip().rstrip(";")
    return json.loads(data)


def image_entry(path, title, caption):
    url = BASE + quote(path, safe="/-_.~")
    return (
        "    <image:image>\n"
        f"      <image:loc>{escape(url)}</image:loc>\n"
        f"      <image:title>{escape(title)}</image:title>\n"
        f"      <image:caption>{escape(caption)}</image:caption>\n"
        "    </image:image>"
    )


def main():
    projects = load_projects()

    main_block = [image_entry(p, t, t) for p, t in MAIN_IMAGES]

    portfolio_block = []
    for p in projects:
        display = p.get("display") or p.get("title") or ""
        if p.get("cover"):
            portfolio_block.append(image_entry(
                p["cover"], f"{display} — обложка проекта",
                f"Дизайн-проект: {display}, Самара"))
        left = PER_PROJECT
        for room in p.get("rooms", []):
            for photo in room.get("photos", []):
                if left <= 0:
                    break
                caption = f"{display} — {room['name']}, фото {photo['n']}"
                portfolio_block.append(image_entry(photo["full"], caption, caption))
                left -= 1
            if left <= 0:
                break

    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
        "  <url>",
        f"    <loc>{BASE}</loc>",
        "    <lastmod>2026-11-19</lastmod>",
        *main_block,
        "  </url>",
        "  <url>",
        f"    <loc>{BASE}portfolio.html</loc>",
        "    <lastmod>2026-11-19</lastmod>",
        *portfolio_block,
        "  </url>",
        "</urlset>",
        "",
    ]
    OUT.write_text("\n".join(xml), encoding="utf-8")
    print(f"{OUT.name}: {len(main_block) + len(portfolio_block)} изображений, "
          f"{OUT.stat().st_size / 1024:.1f} КБ")


if __name__ == "__main__":
    main()
