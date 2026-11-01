"""应用 talk 修订表：改写/丢弃句子，扩充情绪骰池

读 data/talk_fixes.json，把 phrase_bank 里的 talk 句改写为修订版（空串=丢弃），
然后把全部修订成功的句子放进情绪骰（池子越大，抽到不同句的概率越高）。
"""
import json
from collections import Counter

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"
FIX = r"D:\wx409.github.io\data\talk_fixes.json"

fx = json.load(open(FIX, encoding="utf-8"))["fixes"]
bank = json.load(open(BANK, encoding="utf-8"))

kept, pool = [], []
rewritten = dropped = 0
used = set()

for it in bank["items"]:
    if it["type"] != "talk":
        kept.append(it)
        continue
    raw = it["text"]
    if raw in fx:
        new = fx[raw].strip()
        used.add(raw)
        if not new:
            dropped += 1
            continue
        if new != raw:
            rewritten += 1
        it["text"] = new
        it["quality"] = "high"
        it["curated"] = True
        it["rights"] = "free"
        kept.append(it)
        pool.append({"text": new, "source": it["source"]})
    else:
        kept.append(it)

# 修订表里出现但库里没有原文的（格式差异），按文本再匹配一次
texts = {i["text"] for i in kept if i["type"] == "talk"}
missing = [k for k in fx if k not in used and k not in texts]
if missing:
    print("修订表未匹配到原文", len(missing), "条（可忽略）")

bank["items"] = kept
bank["count"] = len(kept)
bank["by_type"] = dict(Counter(i["type"] for i in kept))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in kept))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

dice = json.load(open(DICE, encoding="utf-8"))
# 去重后入骰
seen, faces = set(), []
for p in pool:
    if p["text"] in seen:
        continue
    seen.add(p["text"])
    faces.append(p)
dice["sets"]["emotion"]["faces"] = faces
dice["sets"]["emotion"]["face_count"] = len(faces)
dice["sets"]["emotion"]["disclaimer"] = "现场说话（已轻修：补全语气、断句；仍非逐字引语）"
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("改写 %d｜丢弃 %d｜情绪骰池 %d 条" % (rewritten, dropped, len(faces)))
for f in faces[:10]:
    print("  ", f["text"])
