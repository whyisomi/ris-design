#!/usr/bin/env python3
"""
Оптимизация медиа сайта РИС-Дизайн.

Что делает:
  1) Фото проектов из RIS_ORIGINALS (по умолчанию /home/iso/rissite-originals)
     -> media/portfolio/<проект>/<комната>/
     - полное: WebP, длинная сторона 1400px, quality 82
     - превью: WebP, длинная сторона 420px, quality 72
  2) Генерирует media/portfolio/manifest.js с порядком как на Яндекс Диске.
  3) Оптимизирует текущие медиа сайта (logo, instagram, photo1-5, отзывы) -> WebP.
  4) Оригиналы складывает в media/_originals/ (на деплой не попадут).

Запуск:
    python3 tools/optimize.py            # всё
    python3 tools/optimize.py --media    # только текущие медиа
"""

import argparse
import json
import os
import pathlib
import re
import shutil
import sys

from PIL import Image

SITE = pathlib.Path(__file__).resolve().parent.parent
RAW = pathlib.Path(os.environ.get("RIS_ORIGINALS", "/home/iso/rissite-originals"))
PORTFOLIO = SITE / "media" / "portfolio"

FULL_MAX = 1400
FULL_Q = 82
THUMB_MAX = 420
THUMB_Q = 72

# Обложки подобраны вручную по контактным листам — самые эффектные кадры.
COVERS = {
    "ЖК Волжские огни. 112 кв.м.": "ЖК Волжские огни. 112 кв.м./Кухня/13.jpg",
    "ЖК Волжские огни. 80 кв.м.": "ЖК Волжские огни. 80 кв.м./Кухня, коридор, гардероб/22.jpg",
    "ЖК Империал. 91 кв.м.": "ЖК Империал. 91 кв.м./Кухня и коридор/2.jpg",
    "Пр-кт Карла Маркса. 97 кв.м.": "Пр-кт Карла Маркса. 97 кв.м./Кухня и коридор/15.jpg",
}

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}


def slugify(text):
    """Кириллица -> латиница, пробелы/пунктуация -> дефис."""
    out = []
    for ch in text.lower():
        if ch in TRANSLIT:
            out.append(TRANSLIT[ch])
        elif ch.isdigit():
            out.append(ch)
        elif ch in " \t":
            out.append("-")
    slug = re.sub(r"-{2,}", "-", "".join(out)).strip("-")
    return slug


def natkey(name):
    """Естественная сортировка: 2.jpg < 10.jpg, '5,5.jpg' идёт после '5.jpg'."""
    stem = pathlib.Path(name).stem
    nums = re.findall(r"\d+", stem)
    parts = []
    for part in re.split(r"(\d+)", stem):
        if part.isdigit():
            parts.append((0, int(part), ""))
        elif part:
            parts.append((1, 0, part))
    return (parts, stem)


def room_slug(name):
    """Имя комнаты -> slug. Регистр и синонимы приводим к единому виду."""
    key = name.strip().lower()
    key = key.replace("ё", "е")
    key = re.sub(r"[.,()]", "", key)
    key = re.sub(r"\s+", " ", key).strip()
    return slugify(key)


def project_meta(name):
    """'ЖК Волжские огни. 112 кв.м.' -> (title, area)."""
    base = name.rsplit(".", 1)[0].strip() if name.strip().endswith(".") else name.strip()
    m = re.search(r"(\d+)\s*кв", name)
    area = int(m.group(1)) if m else None
    title = re.sub(r"[.,]?\s*\d+\s*кв\.?\s*м\.?\s*$", "", name).strip(" .,")
    return title, area


def convert(src, dst, max_side, quality):
    """JPEG -> WebP с ограничением по длинной стороне. Возвращает размер в байтах."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        if max(w, h) > max_side:
            scale = max_side / max(w, h)
            im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        im.save(dst, "WEBP", quality=quality, method=6)
    return dst.stat().st_size


def convert_png(src, dst, max_side, quality):
    """PNG -> WebP (сохраняет альфу)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGBA")
        w, h = im.size
        if max(w, h) > max_side:
            scale = max_side / max(w, h)
            im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        im.save(dst, "WEBP", quality=quality, method=6)
    return dst.stat().st_size


def build_portfolio():
    manifest_path = RAW / "manifest.json"
    if not manifest_path.exists():
        print(f"Нет манифеста {manifest_path} — сначала скачай фото с Диска.", file=sys.stderr)
        return None

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    projects = []

    for project in data["projects"]:
        p_title, p_area = project_meta(project["name"])
        p_slug = slugify(project["name"])

        rooms = []
        all_photos = []
        for room in project["rooms"]:
            r_name = room["name"].strip()
            r_slug = room_slug(r_name)
            files = sorted(room["files"], key=lambda f: natkey(f["name"]))
            photos = []
            for idx, f in enumerate(files, 1):
                src = RAW / f["path"].lstrip("/")
                if not src.exists():
                    print(f"  !! нет {src}")
                    continue
                num = f"{idx:02d}"
                full_rel = f"media/portfolio/{p_slug}/{r_slug}/{num}.webp"
                thumb_rel = f"media/portfolio/{p_slug}/{r_slug}/{num}.thumb.webp"
                full = SITE / full_rel
                thumb = SITE / thumb_rel
                if not full.exists():
                    convert(src, full, FULL_MAX, FULL_Q)
                if not thumb.exists():
                    convert(src, thumb, THUMB_MAX, THUMB_Q)
                photos.append({
                    "n": idx,
                    "full": full_rel,
                    "thumb": thumb_rel,
                    "w": Image.open(full).size[0],
                    "h": Image.open(full).size[1],
                })
                all_photos.append(photos[-1])
            rooms.append({"name": r_name, "slug": r_slug, "photos": photos})

        cover_src = COVERS.get(project["name"])
        cover_rel = None
        if cover_src:
            src = RAW / cover_src.lstrip("/")
            if src.exists():
                cover_rel = f"media/portfolio/{p_slug}/cover.webp"
                if not (SITE / cover_rel).exists():
                    convert(src, SITE / cover_rel, 1200, FULL_Q)
            else:
                print(f"  !! обложка не найдена: {cover_src}")

        photos_count = sum(len(r["photos"]) for r in rooms)
        # Заголовок с площадью — иначе «ЖК Волжские огни» повторяется дважды.
        display = f"{p_title}, {p_area} м²" if p_area else p_title
        projects.append({
            "slug": p_slug,
            "title": p_title,
            "display": display,
            "area": p_area,
            "areaLabel": f"{p_area} м²" if p_area else "",
            "rooms": rooms,
            "photos": photos_count,
            "cover": cover_rel,
        })
        print(f"  {display:34} {photos_count:3} фото  {len(rooms)} комнат  -> {p_slug}")

    manifest_js = (
        "/* Сгенерировано tools/optimize.py. Не редактировать вручную. */\n"
        "window.RIS_PORTFOLIO = " + json.dumps(projects, ensure_ascii=False, indent=1) + ";\n"
    )
    (PORTFOLIO / "manifest.js").write_text(manifest_js, encoding="utf-8")
    print(f"  манифест: media/portfolio/manifest.js ({len(projects)} проекта)")
    return projects


def optimize_site_media():
    """Текущие медиа сайта -> WebP. Оригиналы остаются в папке-бэкапе."""
    media = SITE / "media"
    # Исходники ищем в media/, затем в папке-бэкапе RIS_MEDIA_BACKUP.
    backup = pathlib.Path(
        os.environ.get("RIS_MEDIA_BACKUP", "/home/iso/rissite-media-backup/_originals")
    )
    jobs = [
        # (исходник, результат, макс. сторона, качество, режим)
        ("logo.jpg", "logo.webp", 256, 90, "rgb"),
        ("photo1.jpg", "photo1.webp", 1400, 78, "rgb"),
        ("photo2.jpg", "photo2.webp", 1400, 78, "rgb"),
        ("photo3.jpg", "photo3.webp", 1400, 78, "rgb"),
        ("photo4.jpg", "photo4.webp", 1920, 74, "rgb"),
        ("photo5.jpg", "photo5.webp", 1280, 78, "rgb"),
        ("отзыв1@2x.png", "отзыв1.webp", 1228, 86, "png"),
        ("отзыв2@2x.png", "отзыв2.webp", 1258, 86, "png"),
        ("отзыв3@2x.png", "отзыв3.webp", 1228, 86, "png"),
    ]
    for src_name, dst_name, max_side, quality, mode in jobs:
        src = media / src_name
        if not src.exists():
            src = backup / src_name
        if not src.exists():
            print(f"  !! нет исходника {src_name}")
            continue
        dst = media / dst_name
        if mode == "png":
            size = convert_png(src, dst, max_side, quality)
        else:
            size = convert(src, dst, max_side, quality)
        old = src.stat().st_size
        print(f"  {src_name:16} {old/1024:7.0f} КБ -> {dst_name:16} {size/1024:6.0f} КБ")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--media", action="store_true", help="только медиа сайта")
    args = parser.parse_args()

    if not args.media:
        print("Портфолио:")
        build_portfolio()
    print("Медиа сайта:")
    optimize_site_media()
    print("Готово.")


if __name__ == "__main__":
    main()
