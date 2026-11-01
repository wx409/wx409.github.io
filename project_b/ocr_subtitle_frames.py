"""批量 OCR 字幕帧（复用 GOT-OCR run_ocr 的推理方式，模型只加载一次）

用法：python -X utf8 project_b/ocr_subtitle_frames.py <帧目录> [起始秒] [帧间隔秒] [输出前缀]
"""
import glob
import json
import os
import sys

sys.path.insert(0, r"D:\AI\GOT-OCR")
from pathlib import Path

import torch
from PIL import Image
from run_ocr import _stop_string, load_engine  # noqa: E402

MODEL = Path(r"D:\AI\GOT-OCR\models\GOT-OCR-2.0-hf")
frames_dir = sys.argv[1]
start_s = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
step = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
prefix = sys.argv[4] if len(sys.argv) > 4 else "sub"

files = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")) + glob.glob(os.path.join(frames_dir, "*.png")))
print("帧数", len(files))
if not files:
    raise SystemExit(2)

model, processor, device = load_engine(MODEL)
stop = _stop_string(processor)

rows, prev = [], None
for i, f in enumerate(files):
    t = start_s + i * step
    try:
        img = Image.open(f).convert("RGB")
        inputs = processor(img, return_tensors="pt").to(model.device)
        with torch.inference_mode():
            ids = model.generate(**inputs, do_sample=False, tokenizer=processor.tokenizer,
                                 stop_strings=stop, max_new_tokens=256)
        txt = processor.decode(ids[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        txt = " ".join(txt.split())
    except Exception:
        txt = ""
    if txt and txt != prev:
        rows.append({"t": round(t, 1), "text": txt})
        prev = txt
    if i % 100 == 0:
        print("  %d/%d" % (i, len(files)), flush=True)

json.dump(rows, open(os.path.join(frames_dir, "%s.json" % prefix), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
with open(os.path.join(frames_dir, "%s.txt" % prefix), "w", encoding="utf-8") as fh:
    for r in rows:
        mm, ss = int(r["t"]) // 60, int(r["t"]) % 60
        fh.write("[%02d:%02d] %s\n" % (mm, ss, r["text"]))
print("字幕行", len(rows))
