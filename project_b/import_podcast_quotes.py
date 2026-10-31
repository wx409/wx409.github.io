"""小酒馆逐字稿切句 v2：按 [MM:SS.cc] 时间轴合并成句，出处=期号+标题+时间码"""
import json, os, re
from collections import Counter

ROOT = r"D:\wx409.github.io"
SRC = r"E:\wx\私有\王晰全文库\小酒馆逐字稿\深夜小酒馆_全部107期文案_含时间戳.txt"
BANK = os.path.join(ROOT, "data", "phrase_bank.json")
DICE = os.path.join(ROOT, "data", "dice_sets.json")

bank = json.load(open(BANK, encoding="utf-8"))
bank["items"] = [it for it in bank["items"] if it.get("mood") != "night"]
exist = {it["text"] for it in bank["items"]}

EP = re.compile(r"^(\d{2})[\u3000\s]+(.+)$")
TS = re.compile(r"^\[(\d{2}:\d{2}\.\d{2})\](.*)$")

lines = open(SRC, encoding="utf-8", errors="ignore").read().splitlines()
ep_no, ep_title = "", ""
cur, t0 = "", None
out = []

def flush():
    global cur, t0
    if cur and 12 <= len(cur) <= 40:
        out.append((cur, ep_no, ep_title, t0))
    cur, t0 = "", None

for ln in lines:
    s = ln.strip()
    if not s or set(s) == {"-"}:
        continue
    m = EP.match(s)
    if m and not s.startswith("["):
        flush()
        ep_no, ep_title = m.group(1), m.group(2)[:28]
        continue
    m = TS.match(s)
    if not m:
        continue
    ts, body = m.group(1), m.group(2).strip()
    if not body or "字幕由" in body:
        continue
    if not cur:
        t0 = ts
    cur += body
    if len(cur) >= 28 or re.search(r"[。！？]", body):
        flush()
flush()

added = []
for text, no, title, ts in out:
    t = text.strip().strip("，。")
    if not (12 <= len(t) <= 40):
        continue
    if not re.search(r"[我你咱]", t):
        continue
    if t in exist:
        continue
    exist.add(t)
    added.append({"text": t, "type": "interview",
                  "source": "小酒馆 %s 期「%s」%s" % (no or "?", title or "", ts or ""),
                  "curated": False, "rights": "free", "mood": "night", "verified": True})

print("小酒馆切句", len(added))
for x in added[:6]:
    print("  ", x["text"][:36], "|", x["source"])

bank["items"].extend(added)
bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(it["type"] for it in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("现共", bank["count"], bank["by_type"])
