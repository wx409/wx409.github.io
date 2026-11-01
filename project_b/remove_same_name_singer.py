"""剔除「同名歌手」的曲目：按 singer mid 判定，不是我们的王晰（0039pU5Y2PA9OW）

本次：两首《等候》（00188VN20hWZlE / 0026ugdY35BiTU）实属同名歌手 000MQGf60P0Kmn
"""
import json

POOL = r"D:\wx409.github.io\tavern\songs_compact.json"
EXCL = r"D:\wx409.github.io\data\excluded_songs.json"

OURS = "0039pU5Y2PA9OW"
WRONG_MIDS = {"00188VN20hWZlE", "0026ugdY35BiTU"}

d = json.load(open(POOL, encoding="utf-8"))
items = d["songs"] if isinstance(d, dict) and "songs" in d else d
before = len(items)

kept, removed = [], []
for x in items:
    uid = str(x.get("uid", ""))
    mid = uid[2:] if uid.startswith("L:") else ""
    if mid in WRONG_MIDS:
        removed.append({"mid": mid, "name": x.get("name"), "reason": "同名歌手（singer mid 000MQGf60P0Kmn）"})
        continue
    kept.append(x)

if isinstance(d, dict):
    d["songs"] = kept
    d["count"] = len(kept)
json.dump(d, open(POOL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 记录排除清单，供后续枚举/同步脚本引用
try:
    ex = json.load(open(EXCL, encoding="utf-8"))
except Exception:
    ex = {"note": "同名歌手或其他非本人条目，禁止再入曲库/收听人数表", "items": []}
have = {x["mid"] for x in ex["items"]}
for r in removed:
    if r["mid"] not in have:
        ex["items"].append(r)
json.dump(ex, open(EXCL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("删除 %d 条 → 曲库 %d → %d" % (len(removed), before, len(kept)))
for r in removed:
    print("   ", r["mid"], "|", str(r["name"])[:20], "|", r["reason"])
print("排除清单:", EXCL, "共", len(ex["items"]), "条")
