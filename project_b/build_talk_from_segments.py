"""从 segments.json 重建现场 talk 句库（合并相邻片段到 12–34 字）"""
import glob, json, os, re

ROOT = r"D:\wx409.github.io"
TALK_DIR = r"E:\wx\论文素材_王晰作传\现场talk"
BANK = os.path.join(ROOT, "data", "phrase_bank.json")
DICE = os.path.join(ROOT, "data", "dice_sets.json")

SMELL = re.compile(r"你们我|我这个我|我在我|我我们|是是|也也|就是就是")
BAD_END = set("的但在我你他就也还 把被让给对和跟从到一是在那这说有着了过非常特别真会要想能做有年对好")
EMO = ["谢谢", "感谢", "开心", "希望", "温暖", "幸福", "喜欢", "珍惜", "记得", "陪伴", "勇敢", "相信", "感动", "努力", "你们"]

def chunks(segs, lo=12, hi=34):
    out, buf, t0 = [], "", None
    prev_end = None
    for s in segs:
        txt = (s.get("text") or "").strip()
        if not txt:
            continue
        st, en = s.get("start", 0), s.get("end", 0)
        if prev_end is not None and st - prev_end > 2.0 and len(buf) >= lo:
            out.append(buf); buf, t0 = "", None
        if not buf:
            t0 = st
        buf += txt
        prev_end = en
        if len(buf) >= lo:
            out.append(buf); buf = ""
    if len(buf) >= lo:
        out.append(buf)
    return out

talks, seen = [], set()
for f in sorted(glob.glob(os.path.join(TALK_DIR, "**", "*.segments.json"), recursive=True)):
    rel = os.path.relpath(f, TALK_DIR)
    city = rel.split(os.sep)[0] if os.sep in rel else ""
    raw = json.load(open(f, encoding="utf-8"))
    segs = raw.get("segments", []) if isinstance(raw, dict) else raw
    if segs and isinstance(segs[0], str):
        segs = [{"start": i, "end": i + 1, "text": t} for i, t in enumerate(segs)]
    for c in chunks(segs):
        c = re.sub(r"[\s\dA-Za-z，。！？、；：\"'（）()…—\-]+", "", c)
        if not (12 <= len(c) <= 34):
            continue
        if c[-1] in BAD_END or SMELL.search(c):
            continue
        if not re.search(r"[我你咱]", c):
            continue
        if c in seen:
            continue
        seen.add(c)
        talks.append({"text": c, "type": "talk",
                      "source": "%s｜%s" % (city, os.path.basename(f).split(".")[0][:40]),
                      "curated": False, "rights": "free", "mood": "talk", "verified": False})

bank = json.load(open(BANK, encoding="utf-8"))
items = [it for it in bank["items"] if it["type"] != "talk"] + talks
from collections import Counter
bank["items"] = items
bank["count"] = len(items)
bank["by_type"] = dict(Counter(it["type"] for it in items))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("talk 句库:", len(talks), "| 全库", bank["count"], bank["by_type"])

faces = sorted([t["text"] for t in talks],
               key=lambda t: (sum(2 for k in EMO if k in t), 1 if 16 <= len(t) <= 28 else 0),
               reverse=True)[:6]
dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["emotion"]["faces"] = faces
dice["sets"]["emotion"]["face_count"] = len(faces)
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for f in faces:
    print("  ", f)
