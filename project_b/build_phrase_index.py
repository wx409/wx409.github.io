"""生成前端检索索引 data/phrase_index.json（给 qa.html 用）

格式（紧凑）：[{"t":文本,"s":出处,"y":类型,"q":质量}, ...]
只收 quality=high / 长度 8–60 的句子，控制体积。
"""
import json
import os

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
OUT = r"D:\wx409.github.io\data\phrase_index.json"

bank = json.load(open(BANK, encoding="utf-8"))
rows = []
for it in bank["items"]:
    if it.get("quality") != "high":
        continue
    t = (it.get("text") or "").strip()
    if not (8 <= len(t) <= 60):
        continue
    rows.append({"t": t, "s": (it.get("source") or "")[:60],
                 "y": it.get("type", ""), "q": 1})

# 去重
seen, uniq = set(), []
for r in rows:
    if r["t"] in seen:
        continue
    seen.add(r["t"])
    uniq.append(r)

json.dump({"n": len(uniq), "items": uniq}, open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
print("索引 %d 条｜%.0f KB" % (len(uniq), os.path.getsize(OUT) / 1024))
