"""导入「王晰声卦_六爻v4.3/data」里的整理稿：金句 + 访谈问答

- quotes.txt：他的金句（一行一句，含小诗，按行收）
- interview.txt：Q&A 格式，抽「王晰：」后的回答再切句
- lyrics.txt：暂不入（整首歌词，版权更敏感；如需要单独处理）
"""
import json
import os
import re
from collections import Counter

SRC = r"E:\wx\骰子周边20260608\王晰声卦_六爻v4.3\data"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"

bank = json.load(open(BANK, encoding="utf-8"))
exist = {re.sub(r"\s", "", it["text"]) for it in bank["items"]}
added = []


def push(t, source, mood):
    t = re.sub(r"\s+", "", (t or "").strip())
    t = t.strip("，、。；：\"“”")
    if not (10 <= len(t) <= 70):
        return
    key = t
    if key in exist:
        return
    exist.add(key)
    added.append({"text": t, "type": "interview", "source": source, "curated": True,
                  "rights": "free", "mood": mood, "verified": True, "quality": "high"})


# 1) 金句
qpath = os.path.join(SRC, "quotes.txt")
if os.path.exists(qpath):
    lines = [l.strip() for l in open(qpath, encoding="utf-8", errors="ignore").read().splitlines() if l.strip()]
    for l in lines:
        if re.match(r"^王晰的金句|^小诗|^第.{1,3}首|^[（(]", l):
            continue
        for seg in re.split(r"[。！？]", l):
            push(seg, "声卦库·金句", "quote")

# 2) 访谈问答：抽王晰的回答
ipath = os.path.join(SRC, "interview.txt")
if os.path.exists(ipath):
    txt = open(ipath, encoding="utf-8", errors="ignore").read()
    year = ""
    for line in txt.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^(20\d{2})\s*年", s)
        if m:
            year = m.group(1)
            continue
        m = re.match(r"^[一二三四五六七八九十]+、\s*(.+)$", s)
        if m:
            year_tag = m.group(1)[:34]
            continue
        if s.startswith("王晰："):
            body = s.split("：", 1)[1]
            for seg in re.split(r"[。！？]", body):
                push(seg, "声卦库·访谈%s" % (("·" + year) if year else ""), "quote_mag")

bank["items"].extend(added)
bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(i["type"] for i in bank["items"]))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("导入 %d 条｜现共 %d" % (len(added), bank["count"]))
for a in added[:8]:
    print("  ", a["text"][:42], "|", a["source"])
