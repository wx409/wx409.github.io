"""读取 docs/小酒馆独白_待标记.md 的「答：」并执行

答：好      → quality=high, curated=true（进骰池）
答：删      → 删除
答：改 XXX  → 用 XXX 替换原文（并升 high）
答：不改    → 保持 mid
"""
import json
import re
from collections import Counter

MD = r"D:\wx409.github.io\docs\小酒馆独白_待标记.md"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"

lines = open(MD, encoding="utf-8").read().splitlines()

blocks = []          # [(原文, 出处, 答案)]
cur_text = cur_src = None
for ln in lines:
    s = ln.strip()
    if s.startswith("**") and s.endswith("**"):
        cur_text = s.strip("*").strip()
        cur_src = ""
        continue
    if s.startswith("<sub>") and cur_text:
        cur_src = s.replace("<sub>", "").replace("</sub>", "").strip()
        continue
    m = re.match(r"^答\s*[:：]\s*(.*)$", s)
    if m and cur_text:
        blocks.append((cur_text, cur_src or "", m.group(1).strip()))
        cur_text = None

print("解析到 %d 条结论" % len(blocks))

bank = json.load(open(BANK, encoding="utf-8"))
index = {}
for i, it in enumerate(bank["items"]):
    index.setdefault(re.sub(r"\s", "", it["text"]), []).append(i)

good = deleted = fixed = 0
keep = []
del_idx = set()
repl = {}
for orig, src, ans in blocks:
    key = re.sub(r"\s", "", orig)
    hits = index.get(key) or index.get(re.sub(r"\s", "", orig.strip("*")))
    if not hits:
        continue
    a = ans.strip()
    if a.startswith("好"):
        for i in hits:
            bank["items"][i]["quality"] = "high"
            bank["items"][i]["curated"] = True
        good += 1
    elif a.startswith("删"):
        del_idx.update(hits)
        deleted += 1
    elif a.startswith("改"):
        new = re.sub(r"^改[:：]?\s*", "", a).strip()
        if len(new) >= 8:
            repl[hits[0]] = new
            fixed += 1

for i, new in repl.items():
    bank["items"][i]["text"] = new
    bank["items"][i]["quality"] = "high"
    bank["items"][i]["curated"] = True

bank["items"] = [it for i, it in enumerate(bank["items"]) if i not in del_idx]
bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(i["type"] for i in bank["items"]))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("标好 %d｜删 %d｜改写 %d｜词句库 %d（high %d）"
      % (good, deleted, fixed, bank["count"], bank["quality_stats"].get("high", 0)))
