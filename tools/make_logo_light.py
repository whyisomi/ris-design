#!/usr/bin/env python3
"""
Светлая версия логотипа для тёмной заставки.

Исходный логотип — тёмно-серый квадрат (#393939) с белым «РИС» и
серебристым «дизайн». На тёмном фоне заставки он тонет, поэтому:
  * убираем тёмный фон, оставляем мягкое свечение;
  * «РИС» делаем белым;
  * «дизайн» — золотым (в тон акценту сайта).
"""

import pathlib

from PIL import Image

SRC = pathlib.Path("/home/iso/rissite-media-backup/_originals/logo.jpg")
DST = pathlib.Path("/home/iso/rissite/media/logo-light.webp")

im = Image.open(SRC).convert("RGB")
w, h = im.size
px = im.load()

BG = (57, 57, 57)


def is_bg(c):
    return abs(c[0] - BG[0]) <= 26 and abs(c[1] - BG[1]) <= 26 and abs(c[2] - BG[2]) <= 26


# Собираем маску: белым по тёмному (буквы) + золотым (курсив «дизайн»)
out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
op = out.load()

# Сначала находим, где светлые пиксели (это буквы РИС — почти белые)
light = Image.new("L", (w, h), 0)
lp = light.load()
for y in range(h):
    for x in range(w):
        r, g, b = px[x, y]
        if not is_bg((r, g, b)) and r > 120 and g > 120 and b > 120:
            lp[x, y] = 255

# Золотой — средняя яркость, ниже белого, но выше фона
gold = Image.new("L", (w, h), 0)
gp = gold.load()
for y in range(h):
    for x in range(w):
        r, g, b = px[x, y]
        if not is_bg((r, g, b)) and 75 < r < 200 and 75 < g < 200 and 75 < b < 200:
            gp[x, y] = 255

# Наложение: сначала золото, потом белое сверху
white_layer = Image.new("RGBA", (w, h), (255, 255, 255, 0))
gold_layer = Image.new("RGBA", (w, h), (214, 178, 122, 0))
white_layer.putalpha(light)
gold_layer.putalpha(gold)
out = Image.alpha_composite(gold_layer, white_layer)

# Мягкое свечение вокруг букв, чтобы логотип не «вырезался» из фото
glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
glow.paste(out, (0, 0), out)
from PIL import ImageFilter

glow = glow.filter(ImageFilter.GaussianBlur(10))
final = Image.alpha_composite(glow, out)

final.thumbnail((512, 512), Image.LANCZOS)
final.save(DST, "WEBP", quality=92, method=6)
print(f"logo-light.webp: {final.size}, {DST.stat().st_size/1024:.1f} КБ")
