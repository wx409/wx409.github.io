"""按体检结果删除「应删」的伪歌词（署名/制作名单），并重建骰面"""
import json
import random
import re
from collections import Counter

import importlib.util

spec = importlib.util.spec_from_file_location("audit_lyrics", r"D:\wx409.github.io\project_b\audit_lyrics.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

bank = json.load(open(BANK, encoding="utf-8"))
before = bank["count"]

kept, removed = [], []
for it in bank["items"]:
    if it["type"] == "lyrics":
        lvl, rs = mod.check(it["text"], mod.lyric_name(it))
        if lvl == "drop":
            removed.append((it["text"], "；".join(rs)))
            continue
    kept.append(it)

bank["items"] = kept
bank["count"] = len(kept)
bank["by_type"] = dict(Counter(i["type"] for i in kept))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in kept))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

pool = [i for i in kept if i["type"] == "lyrics" and 10 <= len(i["text"]) <= 26]
random.seed(20261107)
picked = random.sample(pool, min(12, len(pool)))
dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["lyrics"]["faces"] = [{"text": p["text"], "source": p["source"]} for p in picked]
dice["sets"]["lyrics"]["face_count"] = len(picked)
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("删除 %d 条：" % len(removed))
for t, r in removed:
    print("  -", t[:46], "|", r[:24])
print("词句库 %d → %d｜歌词池 %d" % (before, bank["count"], len(pool)))
