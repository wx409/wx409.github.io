#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_story_card.py —— 生成 1080x1440 数据故事卡（带 wx409.github.io 水印）"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"D:\wx409.github.io")
FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def wrap(draw, text, f, width):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=f) <= width:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--number", required=True)
    ap.add_argument("--sub", default="")
    ap.add_argument("--bullets", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    W, H = 1080, 1440
    img = Image.new("RGB", (W, H), "#faf9f7")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 12], fill="#a8323d")
    d.text((70, 90), "王晰 · 数据故事", font=font(38, True), fill="#a8323d")
    y = 200
    for line in wrap(d, a.title, font(64, True), W - 140):
        d.text((70, y), line, font=font(64, True), fill="#1f2328")
        y += 92
    y += 40
    d.text((70, y), a.number, font=font(190, True), fill="#a8323d")
    y += 240
    if a.sub:
        for line in wrap(d, a.sub, font(42), W - 140):
            d.text((70, y), line, font=font(42), fill="#444")
            y += 60
    y += 30
    for b in [x.strip() for x in a.bullets.split("|") if x.strip()]:
        d.ellipse([76, y + 18, 92, y + 34], fill="#b8912e")
        for line in wrap(d, b, font(36), W - 200):
            d.text((110, y), line, font=font(36), fill="#333")
            y += 52
        y += 18
    d.text((70, H - 120), "数据与方法：wx409.github.io", font=font(32, True), fill="#6b5320")
    d.text((70, H - 76), "全站数字附口径与出处，可复核", font=font(26), fill="#888")
    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print("写入", out)


if __name__ == "__main__":
    raise SystemExit(main())
