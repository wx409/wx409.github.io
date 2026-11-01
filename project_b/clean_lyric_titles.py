"""清掉歌词里混入的「标题行」（如 最远的心跳-王晰(ElvisWang)），并加强导入规则"""
import io
import json
import random
import re
from collections import Counter

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

TITLE_LINE = re.compile(
    r"王晰|Elvis\s*Wang|ElvisWang|"
    r"^[^-—–]{1,24}[-—–][^-—–]{1,24}(?:\([^)]{1,16}\))?$|"
    r"^《.+》$|"
    r"^\d{4}[-年].{0,20}$")

bank = json.load(open(BANK, encoding="utf-8"))
before = bank["count"]
kept, removed = [], []
for it in bank["items"]:
    if it["type"] == "lyrics" and TITLE_LINE.search(it["text"].strip()):
        removed.append(it["text"])
        continue
    kept.append(it)

bank["items"] = kept
bank["count"] = len(kept)
bank["by_type"] = dict(Counter(i["type"] for i in kept))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in kept))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

pool = [i for i in kept if i["type"] == "lyrics" and 10 <= len(i["text"]) <= 26]
random.seed(20261105)
picked = random.sample(pool, min(12, len(pool)))
dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["lyrics"]["faces"] = [{"text": p["text"], "source": p["source"]} for p in picked]
dice["sets"]["lyrics"]["face_count"] = len(picked)
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("删除标题行 %d 条：%s" % (len(removed), "；".join(removed[:6])))
print("词句库 %d → %d｜歌词池 %d｜骰面 %d" % (before, bank["count"], len(pool), len(picked)))

# 同步加强导入规则，避免以后再进
p = r"D:\wx409.github.io\project_b\import_lyrics_raw.py"
s = io.open(p, encoding="utf-8").read()
if "TITLE_LINE" not in s:
    s = s.replace("bank = json.load(open(BANK, encoding=\"utf-8\"))",
                  "TITLE_LINE = re.compile(\n"
                  "    r\"王晰|Elvis\\\\s*Wang|ElvisWang|\"\n"
                  "    r\"^[^-—–]{1,24}[-—–][^-—–]{1,24}(?:\\\\([^)]{1,16}\\\\))?$|\"\n"
                  "    r\"^《.+》$\")\n\n"
                  "bank = json.load(open(BANK, encoding=\"utf-8\"))", 1)
    s = s.replace('        if not re.search(r"[\\u4e00-\\u9fff]", s):\n            continue',
                  '        if not re.search(r"[\\u4e00-\\u9fff]", s):\n            continue\n'
                  '        if TITLE_LINE.search(s):\n            continue', 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("已加强 import_lyrics_raw 规则")
