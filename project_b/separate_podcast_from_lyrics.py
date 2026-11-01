"""清理伪歌词（可重复运行）：播客字幕文件在 小酒馆字幕/，歌词在 lyrics_raw/"""
import glob
import json
import os
import re
import shutil
from collections import Counter

RAW = r"D:\wx409.github.io\data\lyrics_raw"
POD_DIR = r"E:\wx\私有\王晰全文库\采访目录\小酒馆字幕"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"

POD_MARK = ("本字幕由TME", "深夜小酒馆", "小酒馆", "王熙")
FIX = [("王熙", "王晰")]


def read(p):
    return open(p, encoding="utf-8", errors="ignore").read()


def name_of(txt, fallback):
    m = re.search(r"歌名：(.+)", txt)
    return (m.group(1).strip() if m else fallback)[:40]


os.makedirs(POD_DIR, exist_ok=True)

# 1) RAW 里还残留的播客文件 → 移走
moved = 0
for p in glob.glob(os.path.join(RAW, "*.txt")):
    body = read(p).split("\n\n", 1)[-1]
    if any(k in body for k in POD_MARK):
        dst = os.path.join(POD_DIR, os.path.basename(p))
        if not os.path.exists(dst):
            shutil.move(p, dst)
            moved += 1
if moved:
    print("新移走播客字幕 %d" % moved)

# 2) 播客曲目名集合（来自 小酒馆字幕 目录）
pod_paths = glob.glob(os.path.join(POD_DIR, "*.txt"))
pod_names = {name_of(read(p), os.path.basename(p)[:-4]) for p in pod_paths}
print("播客字幕文件 %d｜曲目名 %d｜真歌词文件 %d"
      % (len(pod_paths), len(pod_names), len(glob.glob(os.path.join(RAW, "*.txt")))))

# 3) 删伪歌词
bank = json.load(open(BANK, encoding="utf-8"))
before = bank["count"]
kept, removed = [], 0
for it in bank["items"]:
    if it.get("type") == "lyrics":
        m = re.search(r"歌词《(.+)》", it.get("source") or "")
        if m and m.group(1).strip() in pod_names:
            removed += 1
            continue
    kept.append(it)
bank["items"] = kept
print("删除伪歌词 %d 条（%d → %d）" % (removed, before, len(kept)))

# 4) 节目独白入池
exist = {re.sub(r"\s", "", i["text"]) for i in bank["items"]}
added = 0
for p in pod_paths:
    t = read(p)
    title = name_of(t, os.path.basename(p)[:-4])
    body = t.split("\n\n", 1)[-1]
    for a, b in FIX:
        body = body.replace(a, b)
    for line in re.split(r"[\n。！？]", body):
        s = re.sub(r"\s+", "", line).strip("，、 ")
        s = re.sub(r"^(首先|然后|之后|最后|这个时候|接下来|嗯|啊|哦|呃)+", "", s)
        if not (12 <= len(s) <= 40):
            continue
        if not re.search(r"[我你咱]", s):
            continue
        if s in exist:
            continue
        exist.add(s)
        bank["items"].append({
            "text": s, "type": "talk",
            "source": "深夜小酒馆·节目独白（AI 字幕，对应曲目《%s》）" % title,
            "curated": False, "rights": "free", "mood": "talk",
            "verified": False, "quality": "mid",
        })
        added += 1
print("节目独白入池 %d 条" % added)

bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(i["type"] for i in bank["items"]))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("词句库 %d → %d" % (before, bank["count"]), bank["by_type"])
