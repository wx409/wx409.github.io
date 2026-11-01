"""把已切分的「王晰」段落切句入词句库（标记为转写来源、未校对）"""
import json
import os
import re
from collections import Counter

BASE = r"E:\wx\私有\王晰全文库\采访目录\全文"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"
SRC_TAG = "音乐流水纪专访（2025-01-29 微博视频，本地转写）"

files = [
    ("5128145411770407_转写_turbo_王晰.md", SRC_TAG),
]

bank = json.load(open(BANK, encoding="utf-8"))
exist = {it["text"] for it in bank["items"]}
added = 0

for fname, tag in files:
    p = os.path.join(BASE, fname)
    if not os.path.exists(p):
        continue
    for sec in re.split(r"^## ", open(p, encoding="utf-8").read(), flags=re.M)[1:]:
        parts = sec.split("\n")
        ts = parts[0].strip().strip("[]")
        body = "".join(parts[2:]).strip()
        for s in re.split(r"[。！？；]", body):
            s = s.strip("，、 ")
            if not (14 <= len(s) <= 60):
                continue
            if not re.search(r"[我咱]", s):
                continue
            if re.fullmatch(r"[对嗯啊好的谢谢哈\s]+", s):
                continue
            if s in exist:
                continue
            exist.add(s)
            bank["items"].append({
                "text": s, "type": "interview",
                "source": "%s｜%s" % (tag, ts),
                "curated": False, "rights": "free", "mood": "quote_talk",
                "verified": False,
            })
            added += 1

bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(it["type"] for it in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("入池", added, "条｜现共", bank["count"], bank["by_type"])
