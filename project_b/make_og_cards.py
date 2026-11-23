#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_og_cards.py —— 1200x630 分享封面（why/moments/ammo）"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"D:\wx409.github.io")
F = r"C:\Windows\Fonts\msyh.ttc"
FB = r"C:\Windows\Fonts\msyhbd.ttc"

CARDS = [
    ("og_why.png", "为什么王晰被低估", "一把用错的尺子", "wx409.github.io/why.html"),
    ("og_moments.png", "值得转发的王晰", "金句 · 现场弹幕峰值 · 路人梗", "wx409.github.io/moments.html"),
    ("og_ammo.png", "内容补给站", "脚本 · 文案 · 事实卡", "wx409.github.io/ammo.html"),
]


def wrap(d, text, font, width):
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=font) <= width:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


for name, title, sub, url in CARDS:
    img = Image.new("RGB", (1200, 630), "#faf9f7")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1200, 14], fill="#a8323d")
    d.text((70, 90), "王晰 · 数字档案", font=ImageFont.truetype(FB, 34), fill="#a8323d")
    y = 180
    for line in wrap(d, title, ImageFont.truetype(FB, 76), 1000):
        d.text((70, y), line, font=ImageFont.truetype(FB, 76), fill="#1f2328")
        y += 96
    y += 20
    for line in wrap(d, sub, ImageFont.truetype(F, 38), 1000):
        d.text((70, y), line, font=ImageFont.truetype(F, 38), fill="#555")
        y += 54
    d.text((70, 545), url, font=ImageFont.truetype(FB, 28), fill="#6b5320")
    img.save(ROOT / "assets" / "share" / name)
    print(name)
