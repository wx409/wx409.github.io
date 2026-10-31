"""对「处理队列」执行：视频本地转写（faster-whisper）+ 图片本地 OCR（GOT-OCR）"""
import json, os, subprocess, sys, time

BASE = r"E:\wx\私有\王晰全文库\采访目录"
Q = os.path.join(BASE, "处理队列.json")
TXT = os.path.join(BASE, "全文")
VID = os.path.join(BASE, "视频")
OCR_PY = r"D:\AI\GOT-OCR\run_ocr.py"

q = json.load(open(Q, encoding="utf-8"))
items = q["items"]

# 1) 视频转写
vids = [it for it in items if it.get("video_path") and not it.get("transcript")]
if vids:
    from faster_whisper import WhisperModel
    print("加载 faster-whisper（本地 small/int8）…")
    model = WhisperModel('C:/Users/yezhe/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120', device="cpu", compute_type="int8")
    for it in vids:
        p = os.path.join(VID, it["video_path"])
        if not os.path.exists(p):
            continue
        t0 = time.time()
        segs, info = model.transcribe(p, language="zh", vad_filter=True, beam_size=5)
        lines = []
        for s in segs:
            lines.append("[%02d:%02d] %s" % (int(s.start) // 60, int(s.start) % 60, s.text.strip()))
        body = "\n".join(lines)
        out = os.path.join(TXT, it["slug"] + "_转写.txt")
        open(out, "w", encoding="utf-8").write(
            "名称：%s\n时间：%s\n链接：%s\n转写：faster-whisper small（本地，未人工校对）\n\n%s\n"
            % (it["title"], it["date"], it["link"], body))
        it["transcript"] = os.path.basename(out)
        it["status"] = "已转写"
        print("  转写 %s｜%d 段｜%.0fs" % (it["slug"][:28], len(lines), time.time() - t0))

# 2) 图片 OCR
imgs = [it for it in items if it.get("image_dir")]
for it in imgs:
    d = it["image_dir"]
    files = sorted(f for f in os.listdir(d) if f.lower().endswith((".jpg", ".png", ".jpeg")))
    parts = []
    for f in files[:12]:
        p = os.path.join(d, f)
        try:
            r = subprocess.run([sys.executable, "-X", "utf8", OCR_PY, "--image", p],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
            txt = (r.stdout or "").strip()
            txt = "\n".join(l for l in txt.splitlines() if len(l.strip()) > 2 and "RequestsDependency" not in l)
            if txt:
                parts.append("—— %s ——\n%s" % (f, txt))
        except Exception as e:
            print("  OCR 失败", f, type(e).__name__)
    if parts:
        out = os.path.join(TXT, it["slug"] + "_OCR.txt")
        open(out, "w", encoding="utf-8").write(
            "名称：%s\n时间：%s\n链接：%s\nOCR：GOT-OCR2.0（本地）\n\n%s\n"
            % (it["title"], it["date"], it["link"], "\n\n".join(parts)))
        it["ocr"] = os.path.basename(out)
        it["status"] = "已OCR"
        print("  OCR %s｜%d 张" % (it["slug"][:28], len(parts)))

json.dump(q, open(Q, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print("完成", dict(Counter(i["status"] for i in items)))
