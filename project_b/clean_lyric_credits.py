"""清理歌词里混入的「制作名单/署名行」（词/曲/编曲/吉他/混音…），再重建骰面"""
import json
import random
import re
from collections import Counter

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

CREDIT = re.compile(
    r"作词|作曲|编曲|制作人|监制|吉他|贝斯|鼓|键盘|和声|录音|混音|母带|统筹|出品|发行|词Lyricist|曲Composer|"
    r"Lyricist|Composer|Arranger|Producer|Guitar|Bass|Drum|Piano|Vocal\s*Edit|Mixing|Mastering|Op\s|SP\s|ISRC")
BAD_SRC = ("期01", "睡前故事与酒", "小酒馆", "福利", "节目独白")
RECIPE = re.compile(r"加入|倒入|搅拌|毫升|克|冰块|切片|准备|点缀|摇匀")

bank = json.load(open(BANK, encoding="utf-8"))
before = len([i for i in bank["items"] if i["type"] == "lyrics"])

kept, removed = [], 0
for it in bank["items"]:
    if it["type"] == "lyrics":
        t, s = it["text"], it.get("source") or ""
        if CREDIT.search(t) or any(b in s for b in BAD_SRC) or RECIPE.search(t):
            removed += 1
            continue
    kept.append(it)

bank["items"] = kept
bank["count"] = len(kept)
bank["by_type"] = dict(Counter(i["type"] for i in kept))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in kept))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

pool = [i for i in kept if i["type"] == "lyrics" and 10 <= len(i["text"]) <= 26]
random.seed(20261104)
picked = random.sample(pool, min(12, len(pool)))
dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["lyrics"]["faces"] = [{"text": p["text"], "source": p["source"]} for p in picked]
dice["sets"]["lyrics"]["face_count"] = len(picked)
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("歌词 %d → %d（删 %d）｜池 %d｜骰面 %d" % (before, len(pool) + removed - removed, removed,
                                          len(pool), len(picked)))
print("词句库总数", bank["count"], bank["by_type"])
for p in picked:
    print("  ", p["text"], "|", p["source"])
