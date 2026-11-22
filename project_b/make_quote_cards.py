#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_quote_cards.py —— 把瞬间库金句生成 1080x1440 竖屏卡（带水印）"""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"D:\wx409.github.io")
SRC = ROOT / "data" / "moments.json"
OUT = ROOT / "assets" / "share" / "quotes"
FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"


def wrap(d, text, f, width):
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=f) <= width:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for i, q in enumerate(d.get("quotes") or [], 1):
        img = Image.new("RGB", (1080, 1440), "#faf9f7")
        dr = ImageDraw.Draw(img)
        dr.rectangle([0, 0, 1080, 12], fill="#a8323d")
        dr.text((70, 90), "王晰 · 半夜的话", font=ImageFont.truetype(FONT_B, 38), fill="#a8323d")
        y = 260
        for line in wrap(dr, "“%s”" % q["quote"], ImageFont.truetype(FONT_B, 58), 900):
            dr.text((70, y), line, font=ImageFont.truetype(FONT_B, 58), fill="#1f2328")
            y += 92
        dr.text((70, 980), "%s · %s" % (q.get("episode") or "", q.get("time") or ""),
                font=ImageFont.truetype(FONT, 34), fill="#666")
        dr.text((70, 1320), "出处与时间码：wx409.github.io/moments.html", font=ImageFont.truetype(FONT_B, 30), fill="#6b5320")
        dr.text((70, 1370), "短引用 · 匿名 · 可回链", font=ImageFont.truetype(FONT, 26), fill="#999")
        img.save(OUT / ("q%02d.png" % i))
    print("生成", len(d.get("quotes") or []), "张 →", OUT)


if __name__ == "__main__":
    main()
