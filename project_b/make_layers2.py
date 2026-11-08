# -*- coding: utf-8 -*-
"""输出紧凑的眼睛/嘴小块 + 偏移，供 Blender 定位。"""
import io, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

BASE = Path(r"E:\wx\论文素材_王晰作传")
SRC = BASE / "_char_front_v3.png"
OUT = BASE / "layers"
OUT.mkdir(exist_ok=True)
EYES = [(210, 290, 275, 355), (350, 290, 420, 355)]
MOUTH = (295, 415, 340, 440)

im = Image.open(SRC).convert("RGBA")
w, h = im.size

# 底图：去掉眼睛与嘴
base = im.copy()
d = ImageDraw.Draw(base)
px = im.load()
col = px[int(w * .36), int(h * .47)]
for b in EYES:
    d.ellipse([b[0] - 4, b[1] - 4, b[2] + 4, b[3] + 4], fill=col)
d.ellipse([MOUTH[0] - 3, MOUTH[1] - 3, MOUTH[2] + 3, MOUTH[3] + 3], fill=col)
mask = Image.new("L", (w, h), 0)
dm = ImageDraw.Draw(mask)
for b in EYES:
    dm.ellipse([b[0] - 8, b[1] - 8, b[2] + 8, b[3] + 8], fill=255)
dm.ellipse([MOUTH[0] - 6, MOUTH[1] - 6, MOUTH[2] + 6, MOUTH[3] + 6], fill=255)
base = Image.composite(base.filter(ImageFilter.GaussianBlur(2.0)), base, mask)
# 穿衣服：白围裙 + 深蓝马甲 + 腰带
ap = Image.new("RGBA", (w, h), (0, 0, 0, 0))
da = ImageDraw.Draw(ap)
top, bot = int(h * 0.615), int(h * 0.90)
da.polygon([(int(w * .41), top), (int(w * .59), top),
            (int(w * .64), bot), (int(w * .36), bot)], fill=(247, 250, 252, 232))
da.line([(int(w * .43), int(h * .50)), (int(w * .43), top)], fill=(247, 250, 252, 232), width=8)
da.line([(int(w * .57), int(h * .50)), (int(w * .57), top)], fill=(247, 250, 252, 232), width=8)
da.polygon([(int(w * .35), int(h * .60)), (int(w * .41), int(h * .60)),
            (int(w * .41), int(h * .86)), (int(w * .34), int(h * .86))], fill=(38, 62, 104, 220))
da.polygon([(int(w * .65), int(h * .60)), (int(w * .59), int(h * .60)),
            (int(w * .59), int(h * .86)), (int(w * .66), int(h * .86))], fill=(38, 62, 104, 220))
da.rectangle([int(w * .39), int(h * .625), int(w * .61), int(h * .645)], fill=(30, 48, 82, 225))
base = Image.alpha_composite(base, ap.filter(ImageFilter.GaussianBlur(0.6)))
base.save(OUT / "base.png")

def crop_save(box, name):
    c = im.crop(box)
    c.save(OUT / name)
    return {"file": name, "box": list(box), "w": c.width, "h": c.height}

meta = {"size": [w, h], "base": "base.png",
        "parts": [crop_save(EYES[0], "eye_l.png"), crop_save(EYES[1], "eye_r.png"),
                  crop_save(MOUTH, "mouth.png")]}
(OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
print("分层完成:", [p["file"] for p in meta["parts"]], "| 画布", w, h)
