"""删除「狗刨式」那句，并把「声卦库·访谈」来源的条目降级为 mid（无原文链接，待核）"""
import json
import re
from collections import Counter

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

bank = json.load(open(BANK, encoding="utf-8"))
before = bank["count"]

kept, deleted = [], []
for it in bank["items"]:
    t = it.get("text") or ""
    if "狗刨" in t:
        deleted.append(t)
        continue
    if "声卦库·访谈" in (it.get("source") or ""):
        it["quality"] = "mid"
        it["verified"] = False
        it["note"] = "来源为整理稿（无原文链接），措辞可能经改写，引用前须核原文"
    kept.append(it)

bank["items"] = kept
bank["count"] = len(kept)
bank["by_type"] = dict(Counter(i["type"] for i in kept))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in kept))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("删除：", deleted)
print("声卦库·访谈 降级 %d 条 → mid" % sum(1 for i in kept if "声卦库·访谈" in (i.get("source") or "")))
print("词句库 %d → %d｜high %d" % (before, bank["count"], bank["quality_stats"].get("high", 0)))

# 骰面里若含已删条目，重挑
dice = json.load(open(DICE, encoding="utf-8"))
texts = {i["text"] for i in kept}
for k, v in dice["sets"].items():
    faces = [f for f in (v.get("faces") or []) if f["text"] in texts]
    if len(faces) != len(v.get("faces") or []):
        v["faces"] = faces
        v["face_count"] = len(faces)
        print("  %s 骰面清理后 %d" % (k, len(faces)))
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
