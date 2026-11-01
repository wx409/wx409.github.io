"""重建歌词骰面：只从真歌词里抽，且排除任何"节目/期"来源"""
import json
import random

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

BAD_SRC = ("期01", "睡前故事与酒", "小酒馆", "福利", "节目独白")

bank = json.load(open(BANK, encoding="utf-8"))
pool = [i for i in bank["items"]
        if i["type"] == "lyrics"
        and 10 <= len(i["text"]) <= 26
        and not any(b in (i.get("source") or "") for b in BAD_SRC)]

# 去掉含数字/量词的操作型句子（制作配方、步骤）
import re
RECIPE = re.compile(r"加入|倒入|搅拌|毫升|克|冰块|切片|准备|点缀|摇匀")
pool = [i for i in pool if not RECIPE.search(i["text"])]

random.seed(20261103)
picked = random.sample(pool, min(12, len(pool)))

dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["lyrics"]["faces"] = [{"text": p["text"], "source": p["source"]} for p in picked]
dice["sets"]["lyrics"]["face_count"] = len(picked)
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("歌词池 %d 条 → 取 %d 面" % (len(pool), len(picked)))
for p in picked:
    print("  ", p["text"], "|", p["source"])
