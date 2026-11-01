"""把 data/lyrics_raw 下的歌词切句入池（仅内部、短句）"""
import glob
import json
import os
import re
from collections import Counter

RAW = r"D:\wx409.github.io\data\lyrics_raw"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

bank = json.load(open(BANK, encoding="utf-8"))
exist = {re.sub(r"\s", "", i["text"]) for i in bank["items"]}

files = sorted(glob.glob(os.path.join(RAW, "*.txt")))
print("歌词文件", len(files))

added, songs = [], set()
for p in files:
    txt = open(p, encoding="utf-8", errors="ignore").read()
    head, _, body = txt.partition("\n\n")
    m = re.search(r"歌名：(.+)", head)
    name = (m.group(1).strip() if m else os.path.basename(p).replace(".txt", ""))[:40]
    songs.add(name)
    for line in body.splitlines():
        s = re.sub(r"\s+", "", line).strip("，、。！？；：\"“”")
        if not (8 <= len(s) <= 34):
            continue
        if re.fullmatch(r"[啊哦嗯吧呢啦呀]+", s):
            continue
        if not re.search(r"[\u4e00-\u9fff]", s):
            continue
        if s in exist:
            continue
        exist.add(s)
        added.append({"text": s, "type": "lyrics", "source": "歌词《%s》" % name,
                      "curated": False, "rights": "仅内部", "mood": "lyric",
                      "verified": True, "quality": "high"})

bank["items"].extend(added)
bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(i["type"] for i in bank["items"]))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

import random
random.seed(20261102)
pool = [i for i in bank["items"] if i["type"] == "lyrics" and 10 <= len(i["text"]) <= 26]
lyr_songs = {i["source"] for i in bank["items"] if i["type"] == "lyrics"}
picked = random.sample(pool, min(12, len(pool)))
dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["lyrics"]["faces"] = [{"text": p["text"], "source": p["source"]} for p in picked]
dice["sets"]["lyrics"]["face_count"] = len(picked)
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("新增歌词句 %d｜歌词曲目数 %d｜歌词池 %d" % (len(added), len(lyr_songs), len(pool)))
