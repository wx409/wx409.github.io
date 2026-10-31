"""骰面终版挑选：剔除占位句/截断句，重挑五套"""
import json, os, random

ROOT = r"D:\wx409.github.io"
BANK = os.path.join(ROOT, "data", "phrase_bank.json")
DICE = os.path.join(ROOT, "data", "dice_sets.json")

bank = json.load(open(BANK, encoding="utf-8"))
items = bank["items"]

BAD = ("未详细记录", "未记录", "暂无", "无内容", "待补", "不详")
BAD_END = set("的但在我你他就也还 把被让给对和跟从到一是在那这说有着了过非常特别真会要想能做有年啊对好")
EMO = ["谢谢", "感谢", "开心", "希望", "温暖", "幸福", "喜欢", "珍惜", "记得", "陪伴", "勇敢", "相信", "感动", "努力"]

items = [it for it in items if not any(b in it["text"] for b in BAD)]
items = [it for it in items if it["text"][-1] not in BAD_END or it["type"] in ("song", "lyrics", "mystic")]
bank["items"] = items
bank["count"] = len(items)
from collections import Counter
bank["by_type"] = dict(Counter(it["type"] for it in items))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("清理后:", bank["count"], bank["by_type"])

random.seed(20261031)
def pick(types, n=6, maxlen=48, mood=None):
    pool = [x["text"] for x in items
            if x["type"] in types and 10 <= len(x["text"]) <= maxlen
            and (mood is None or x.get("mood") == mood)]
    random.shuffle(pool)
    return pool[:n]

talks = sorted([x["text"] for x in items if x["type"] == "talk"],
               key=lambda t: (sum(2 for k in EMO if k in t), 1 if 18 <= len(t) <= 28 else 0), reverse=True)
talks = [t for t in talks if len(t) >= 14 and t[-1] not in BAD_END][:6]

dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["emotion"]["faces"] = talks
dice["sets"]["interview"]["faces"] = pick(("interview",), maxlen=60, mood="note")
for k in dice["sets"]:
    dice["sets"][k]["face_count"] = len(dice["sets"][k]["faces"])
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in dice["sets"].items():
    print("==", v["name"])
    for f in v["faces"]:
        print("   ", f)
