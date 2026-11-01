"""再清一轮：歌词里以「标签：」开头的署名行（曲：/弦乐：/和声：…）"""
import io
import json
import random
import re
from collections import Counter

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

LABEL_LINE = re.compile(r"^[\u4e00-\u9fffA-Za-z]{1,8}[:：]")

bank = json.load(open(BANK, encoding="utf-8"))
before = bank["count"]
kept, removed = [], []
for it in bank["items"]:
    if it["type"] == "lyrics" and LABEL_LINE.match(it["text"].strip()):
        removed.append(it["text"])
        continue
    kept.append(it)

bank["items"] = kept
bank["count"] = len(kept)
bank["by_type"] = dict(Counter(i["type"] for i in kept))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in kept))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

pool = [i for i in kept if i["type"] == "lyrics" and 10 <= len(i["text"]) <= 26]
random.seed(20261106)
picked = random.sample(pool, min(12, len(pool)))
dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["lyrics"]["faces"] = [{"text": p["text"], "source": p["source"]} for p in picked]
dice["sets"]["lyrics"]["face_count"] = len(picked)
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("删除「标签：」行 %d：%s" % (len(removed), "；".join(removed[:6])))
print("词句库 %d → %d｜歌词池 %d｜骰面 %d" % (before, bank["count"], len(pool), len(picked)))

# 同步到导入器
p = r"D:\wx409.github.io\project_b\import_lyrics_raw.py"
s = io.open(p, encoding="utf-8").read()
if "LABEL_LINE" not in s:
    s = s.replace("TITLE_LINE = re.compile(", "LABEL_LINE = re.compile(r\"^[\\u4e00-\\u9fffA-Za-z]{1,8}[:：]\")\n\nTITLE_LINE = re.compile(", 1)
    s = s.replace("        if TITLE_LINE.search(s):\n            continue",
                  "        if TITLE_LINE.search(s) or LABEL_LINE.match(s):\n            continue", 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("已同步导入器")
