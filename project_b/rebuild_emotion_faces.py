"""重建情绪骰：只用 high 的现场/节目独白，且长度适合做骰面（18–60 字）

若短句不足 12 条，放宽到 18–80 字；仍不足则保留原 32 条白名单。
"""
import json
import random

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

bank = json.load(open(BANK, encoding="utf-8"))
dice = json.load(open(DICE, encoding="utf-8"))

talks = [i for i in bank["items"] if i["type"] in ("talk", "interview") and i.get("quality") == "high"]


def pool(lo, hi):
    out = []
    for i in talks:
        t = i["text"].strip()
        if not (lo <= len(t) <= hi):
            continue
        if any(t[:10] == o["text"][:10] or t[:16] in o["text"] for o in out):
            continue
        out.append(i)
    return out


cand = pool(18, 60)
if len(cand) < 12:
    cand = pool(18, 80)
if len(cand) < 12:
    print("短句不足，保留原骰面")
    raise SystemExit(0)

# 去近似重复（前 12 字）
seen, uniq = set(), []
for it in sorted(cand, key=lambda x: -len(x["text"])):
    k = it["text"][:12]
    if k in seen:
        continue
    seen.add(k)
    uniq.append(it)

random.seed(20261108)
picked = random.sample(uniq[:120], min(24, len(uniq)))

dice["sets"]["emotion"]["faces"] = [{"text": p["text"], "source": p["source"]} for p in picked]
dice["sets"]["emotion"]["face_count"] = len(picked)
dice["sets"]["emotion"]["disclaimer"] = "现场/节目独白（人工确认 high，18–60 字）"
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("情绪骰池 %d（候选 %d）→ 取 %d 面" % (len(uniq), len(cand), len(picked)))
for p in picked[:8]:
    print("  ", p["text"][:56])
