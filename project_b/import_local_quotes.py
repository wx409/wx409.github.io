"""把本地已成型的语录库 + 小酒馆 107 期逐字稿切句，并入 interview 类"""
import json, os, re
from collections import Counter

ROOT = r"D:\wx409.github.io"
LIB = r"E:\wx\私有\王晰全文库\小酒馆逐字稿"
BANK = os.path.join(ROOT, "data", "phrase_bank.json")
DICE = os.path.join(ROOT, "data", "dice_sets.json")

bank = json.load(open(BANK, encoding="utf-8"))
exist = {it["text"] for it in bank["items"]}
added = []

def push(text, source, mood="quote", typ="interview", verified=True):
    t = (text or "").strip().strip("“”")
    if not (8 <= len(t) <= 80):
        return
    if t in exist:
        return
    exist.add(t)
    added.append({"text": t, "type": typ, "source": source, "curated": False,
                  "rights": "free", "mood": mood, "verified": verified})

# 1) 采访语录库（自带 context）
d = json.load(open(os.path.join(LIB, "interview_quotes.json"), encoding="utf-8"))
for k, v in d.items():
    if k == "_meta" or not isinstance(v, list):
        continue
    for it in v:
        push(it.get("text"), it.get("context") or "采访语录库", mood="quote")

# 2) 金句库（无 context，标“金句库”）
g = json.load(open(os.path.join(LIB, "golden_quotes.json"), encoding="utf-8"))
for k, v in g.items():
    if k == "_meta" or not isinstance(v, list):
        continue
    for it in v:
        push(it.get("text"), "金句库｜%s" % k, mood="quote")

print("语录库导入", len(added))

# 3) 小酒馆 107 期逐字稿切句（带时间戳的行）
p = os.path.join(LIB, "深夜小酒馆_全部107期文案_含时间戳.txt")
raw = open(p, encoding="utf-8", errors="ignore").read()
lines = raw.splitlines()
ep = ""
talk_added = 0
for ln in lines:
    s = ln.strip()
    m = re.match(r"^(第?\s*\d+\s*期|EP\s*\d+|ep\s*\d+)", s)
    if m:
        ep = m.group(1)
        continue
    m2 = re.match(r"^\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*(.+)$", s)
    if not m2:
        continue
    ts, body = m2.group(1), m2.group(2)
    for seg in re.split(r"[。！？；]", body):
        seg = seg.strip().strip("，")
        if not (12 <= len(seg) <= 34):
            continue
        if not re.search(r"[我你咱]", seg):
            continue
        if re.search(r"[\u4e00-\u9fff]", seg) is None:
            continue
        before = len(added)
        push(seg, "小酒馆｜%s %s" % (ep or "?", ts), mood="night")
        if len(added) > before:
            talk_added += 1
        if talk_added >= 240:
            break
    if talk_added >= 240:
        break

print("小酒馆切句新增", talk_added)

bank["items"].extend(added)
bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(it["type"] for it in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("现共", bank["count"], bank["by_type"])
