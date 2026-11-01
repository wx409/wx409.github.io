"""执行 docs/小酒馆独白_待抽看.md 的人工标注

答：好   → high（进骰池）
答：好（可去掉嗯） → high 且清掉「嗯/啊/哦」等填充词
答：删   → 删除
答：改 XXX → 用 XXX 替换（并升 high）
"""
import json
import re
from collections import Counter

MD = r"D:\wx409.github.io\docs\小酒馆独白_待抽看.md"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"

lines = open(MD, encoding="utf-8").read().splitlines()

entries, cur = [], None
for ln in lines:
    s = ln.strip()
    if s.startswith("- "):
        cur = {"text": s[2:].strip(), "src": "", "ans": ""}
        continue
    if cur is not None and s.startswith("<sub>"):
        cur["src"] = s.replace("<sub>", "").replace("</sub>", "").strip()
        continue
    m = re.match(r"^答\s*[:：]\s*(.*)$", s)
    if m and cur is not None:
        cur["ans"] = m.group(1).strip()
        entries.append(cur)
        cur = None

print("解析 %d 条" % len(entries))

bank = json.load(open(BANK, encoding="utf-8"))
index = {}
for i, it in enumerate(bank["items"]):
    index.setdefault(re.sub(r"\s", "", it["text"]), []).append(i)

FILLER = re.compile(r"(嗯|啊|哦|呃|额)+")
good = deleted = fixed = 0
del_idx = set()
for e in entries:
    key = re.sub(r"\s", "", e["text"])
    hits = index.get(key)
    if not hits:
        print("  ! 未匹配:", e["text"][:24])
        continue
    a = e["ans"]
    if a.startswith("删"):
        del_idx.update(hits)
        deleted += 1
    elif a.startswith("改"):
        new = re.sub(r"^改[:：]?\s*", "", a).strip()
        if len(new) >= 8:
            for i in hits[:1]:
                bank["items"][i]["text"] = new
                bank["items"][i]["quality"] = "high"
                bank["items"][i]["curated"] = True
            fixed += 1
    elif a.startswith("好"):
        for i in hits:
            it = bank["items"][i]
            if "去掉" in a:
                it["text"] = FILLER.sub("", it["text"])
            it["quality"] = "high"
            it["curated"] = True
        good += 1

bank["items"] = [it for i, it in enumerate(bank["items"]) if i not in del_idx]
bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(i["type"] for i in bank["items"]))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("标好 %d｜删 %d｜改写 %d" % (good, deleted, fixed))
print("词句库 %d｜talk(high) %d"
      % (bank["count"],
         sum(1 for i in bank["items"] if i["type"] == "talk" and i.get("quality") == "high")))
