"""把另两份长转写（东方艺享家 / 民族歌曲讲座）切句入池（标 mid，先不进骰）"""
import json
import os
import re
import subprocess
import sys
from collections import Counter

sys.path.insert(0, r"D:\wx409.github.io\project_b")

BASE = r"E:\wx\私有\王晰全文库\采访目录\全文"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"
SPLIT = r"D:\wx409.github.io\project_b\split_speakers2.py"

TARGETS = [
    ("东方艺享家_视频播客_秦屹x王晰_转写_turbo.txt", "东方艺享家（2026-06-17）"),
    ("民族歌曲讲座_范唱与问答_转写_turbo.txt", "民族歌曲讲座"),
]

bank = json.load(open(BANK, encoding="utf-8"))
exist = {re.sub(r"\s", "", i["text"]) for i in bank["items"]}
added = 0

for fname, tag in TARGETS:
    p = os.path.join(BASE, fname)
    if not os.path.exists(p):
        print("缺文件", fname)
        continue
    subprocess.call([sys.executable, "-X", "utf8", SPLIT, p])
    split_md = p.replace("_转写_turbo.txt", "_转写_turbo_王晰.md")
    if not os.path.exists(split_md):
        print("切分结果缺失", split_md)
        continue
    for sec in re.split(r"^## ", open(split_md, encoding="utf-8").read(), flags=re.M)[1:]:
        parts = sec.split("\n")
        ts = parts[0].strip().strip("[]")
        body = "".join(parts[2:]).strip()
        for s in re.split(r"[。！？；]", body):
            s = re.sub(r"\s+", "", s).strip("，、 ")
            if not (16 <= len(s) <= 44):
                continue
            if not re.search(r"[我咱]", s):
                continue
            if not re.search(r"其实|我觉得|因为|所以|但是|希望|认为|坚持|理解|低音|专辑|音乐|舞台|声音", s):
                continue
            key = s
            if key in exist:
                continue
            exist.add(key)
            bank["items"].append({
                "text": s, "type": "interview",
                "source": "转写｜%s｜%s" % (tag, ts),
                "curated": False, "rights": "free", "mood": "quote_talk",
                "verified": False, "quality": "mid",
            })
            added += 1

bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(i["type"] for i in bank["items"]))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("两份转写切句入池 %d 条（quality=mid，不进骰，待校对后可升级）" % added)
print("现共", bank["count"], bank["by_type"])
