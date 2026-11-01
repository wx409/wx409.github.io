"""重建全部骰面：直接使用「完整合格池」，不再只取 6/10/12/24 个

这样每次抽取都在几十到几百条里随机，不会感觉"就那么几句在循环"。
"""
import json
import random
import re
from collections import Counter

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

RE_THIRD = re.compile(r"坦言|表示|透露|声称|提到|认为他|他说|他称|他笑言|据介绍|据悉")

BANK_D = json.load(open(BANK, encoding="utf-8"))
items = BANK_D["items"]


def pick(types, lo, hi, quality=("high",), mood=None, cap=400):
    out, seen = [], set()
    for it in items:
        if it["type"] not in types:
            continue
        if quality and it.get("quality") not in quality:
            continue
        if mood and it.get("mood") not in mood:
            continue
        t = (it.get("text") or "").strip()
        if not (lo <= len(t) <= hi):
            continue
        # 排除第三人称转述（不是他本人的话）
        if RE_THIRD.search(t) and not re.search(r"[我咱]", t):
            continue
        # 排除"标题式"描述（没有主谓）
        if t.endswith("。") and len(t) < 22 and "，" not in t:
            continue
        k = t[:12]
        if k in seen:
            continue
        seen.add(k)
        out.append({"text": t, "source": it.get("source", "")})
        if len(out) >= cap:
            break
    return out


emo = pick(("talk", "interview"), 16, 60, cap=400)
lyr = pick(("lyrics",), 10, 30, cap=600)
itr = pick(("interview",), 14, 60, cap=400)
mys = pick(("mystic",), 8, 120, cap=64)

dice = json.load(open(DICE, encoding="utf-8"))
for key, faces, note in (
    ("emotion", emo, "现场/节目独白与采访原话（人工确认 high）"),
    ("lyrics", lyr, "歌词短句（人工确认或已清洗）"),
    ("interview", itr, "他本人的原话（采访/播客）"),
    ("mystic", mys, "易经六十四卦（每卦一句释义，娱乐向）"),
):
    dice["sets"][key]["faces"] = faces
    dice["sets"][key]["face_count"] = len(faces)
    dice["sets"][key]["disclaimer"] = note

json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

for k in ("emotion", "lyrics", "interview", "mystic"):
    print("%-10s %d 面" % (k, dice["sets"][k]["face_count"]))
print("样例：")
for k in ("emotion", "lyrics", "interview", "mystic"):
    f = dice["sets"][k]["faces"]
    if f:
        print("  [%s] %s" % (k, f[0]["text"][:46]))
