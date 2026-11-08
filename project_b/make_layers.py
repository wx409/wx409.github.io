#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分层：把大肥鱼立绘拆成 3 层（底图去眼嘴 / 眼睛 / 嘴），供 Blender 驱动。

为什么先做 3 层而不是 5 层：
  头发单独分层需要手绘蒙版，自动切不干净；而"眨眼 + 说话 + 点头"已经能解决
  「她呆」的问题，头发的摆动可以先用整体微旋代替。5 层留到下一步。

输出（透明 PNG，与底图同尺寸 629×820）
  layers/base.png   去掉眼睛和嘴的底图（皮肤色填补）
  layers/eyes.png   眼睛（带原始像素）
  layers/mouth.png  嘴部区域
  layers/meta.json  位置信息
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

BASE = Path(r"E:\wx\论文素材_王晰作传")
SRC = BASE / "_char_front_v3.png"
OUT = BASE / "layers"
OUT.mkdir(exist_ok=True)


def find_eyes(im: Image.Image):
    """在脸部区域找两块最大近白区域 = 眼白。"""
    w, h = im.size
    px = im.load()
    y0, y1 = int(h * 0.30), int(h * 0.52)
    x0, x1 = int(w * 0.28), int(w * 0.72)
    pts = [(x, y) for y in range(y0, y1) for x in range(x0, x1)
           if px[x, y][3] > 200 and px[x, y][0] > 240 and px[x, y][1] > 240 and px[x, y][2] > 240]
    if not pts:
        return []
    pts.sort()
    mid = len(pts) // 2
    boxes = []
    for grp in (pts[:mid], pts[mid:]):
        xs = [p[0] for p in grp]; ys = [p[1] for p in grp]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return boxes


def skin_color(im: Image.Image):
    """取脸颊颜色作为填补色。"""
    w, h = im.size
    px = im.load()
    cx, cy = int(w * 0.36), int(h * 0.47)
    vals = [px[cx + dx, cy + dy] for dx in range(-6, 7) for dy in range(-6, 7)
            if px[cx + dx, cy + dy][3] > 200]
    if not vals:
        return (255, 240, 230, 255)
    r = sorted(v[0] for v in vals)[len(vals) // 2]
    g = sorted(v[1] for v in vals)[len(vals) // 2]
    b = sorted(v[2] for v in vals)[len(vals) // 2]
    return (r, g, b, 255)


def main() -> int:
    im = Image.open(SRC).convert("RGBA")
    w, h = im.size
    eyes = [(210, 290, 275, 355), (350, 290, 420, 355)]  # 实测坐标
    print("眼睛框:", eyes)

    if len(eyes) < 2:
        # 兜底：按比例给两个框
        eyes = [(int(w * .34), int(h * .38), int(w * .46), int(h * .46)),
                (int(w * .54), int(h * .38), int(w * .66), int(h * .46))]
        print("用比例兜底:", eyes)

    # 嘴：眼睛下方中央
    ex_l, ey_t, ex_r, ey_b = eyes[0][0], eyes[0][1], eyes[1][2], eyes[1][3]
    mcx = (ex_l + ex_r) // 2
    mouth = (295, 415, 340, 440)
    print("嘴框:", mouth)

    # 眼睛层
    eyes_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for b in eyes:
        box = (max(0, b[0] - 4), max(0, b[1] - 4), min(w, b[2] + 4), min(h, b[3] + 4))
        eyes_img.paste(im.crop(box), box)
    eyes_img.save(OUT / "eyes.png")

    # 嘴层
    mouth_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mbox = (max(0, mouth[0]), max(0, mouth[1]), min(w, mouth[2]), min(h, mouth[3]))
    mouth_img.paste(im.crop(mbox), mbox)
    mouth_img.save(OUT / "mouth.png")

    # 底图：把眼睛/嘴区域涂成皮肤色，再轻微模糊
    base = im.copy()
    d = ImageDraw.Draw(base)
    col = skin_color(im)
    for b in eyes:
        d.ellipse([b[0] - 5, b[1] - 5, b[2] + 5, b[3] + 5], fill=col)
    d.ellipse([mouth[0] - 3, mouth[1] - 3, mouth[2] + 3, mouth[3] + 3], fill=col)
    # 只模糊被涂的区域（用蒙版）
    mask = Image.new("L", (w, h), 0)
    dm = ImageDraw.Draw(mask)
    for b in eyes:
        dm.ellipse([b[0] - 8, b[1] - 8, b[2] + 8, b[3] + 8], fill=255)
    dm.ellipse([mouth[0] - 6, mouth[1] - 6, mouth[2] + 6, mouth[3] + 6], fill=255)
    blur = base.filter(ImageFilter.GaussianBlur(2.2))
    base = Image.composite(blur, base, mask)
    base.save(OUT / "base.png")

    meta = {"size": [w, h], "eyes": eyes, "mouth": list(mouth), "skin": list(col)}
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("已输出：", [p.name for p in OUT.glob("*.png")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
