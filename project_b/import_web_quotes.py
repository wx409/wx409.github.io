"""从抓下来的网页里抽「他本人的话」入池（只收第一人称引号段，百科类跳过）"""
import glob
import json
import os
import re
from collections import Counter

PAGES = r"E:\wx\私有\王晰全文库\采访目录\网页"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"

QUOTE = re.compile(r"[“「]([^”」]{12,90})[”」]")
FIRST = re.compile(r"[我咱]")
SKIP_TITLE = ("百科", "wiki", "词条")

bank = json.load(open(BANK, encoding="utf-8"))
exist = {re.sub(r"\s", "", i["text"]) for i in bank["items"]}
added = []

for p in sorted(glob.glob(os.path.join(PAGES, "*.txt"))):
    raw = open(p, encoding="utf-8", errors="ignore").read()
    head, _, body = raw.partition("\n\n")
    title = ""
    m = re.search(r"标题：(.+)", head)
    if m:
        title = m.group(1).strip()
    if any(s in title for s in SKIP_TITLE):
        print("跳过（百科/词条）:", title[:30])
        continue
    for q in QUOTE.findall(body):
        q = re.sub(r"\s+", "", q).strip("，、。 ")
        if not (12 <= len(q) <= 80):
            continue
        if not FIRST.search(q):
            continue
        if q in exist:
            continue
        exist.add(q)
        added.append({"text": q, "type": "interview",
                      "source": "网页｜%s" % (title[:32] or os.path.basename(p)[:20]),
                      "curated": False, "rights": "free", "mood": "quote_mag",
                      "verified": False, "quality": "mid"})

bank["items"].extend(added)
bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(i["type"] for i in bank["items"]))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("\n入池 %d 条｜现共 %d" % (len(added), bank["count"]))
for a in added:
    print("  ", a["text"][:64], "|", a["source"][:30])
