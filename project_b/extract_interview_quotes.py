"""从采访正文抽取王晰本人的引语（“…”），并入 phrase_bank 的 interview 类"""
import json, os, re
import openpyxl

ROOT = r"D:\wx409.github.io"
XLSX = r"E:\wx\骰子周边20260608\GEO\GEO\王晰采访记录汇编.xlsx"
BANK = os.path.join(ROOT, "data", "phrase_bank.json")

ws = openpyxl.load_workbook(XLSX, read_only=True, data_only=True).active
rows = [(i, r) for i, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2)
        if r and len(r) > 5 and r[5] and str(r[5]).strip()]

QUOTE = re.compile(r"[“\"]([^”\"]{8,80})[”\"]")
BAD = ("记者", "报道", "采访", "编辑", "来源", "版权", "转载", "王晰表示", "他坦言")

cands = []
for i, r in rows:
    title = str(r[1] or "").strip()
    date = ""
    m = re.match(r"(\d{4})年", title)
    if m:
        date = m.group(1)
    body = str(r[5])
    for q in QUOTE.findall(body):
        q = q.strip().strip("，。、；：")
        if not (8 <= len(q) <= 60):
            continue
        if any(b in q for b in BAD):
            continue
        if re.search(r"[\u4e00-\u9fff]{30,}", q) is False and len(q) < 10:
            continue
        cands.append({"text": q, "type": "interview",
                      "source": "采访正文｜%s" % title[:40],
                      "curated": False, "rights": "free", "mood": "quote", "verified": True})

seen, uniq = set(), []
for c in cands:
    if c["text"] in seen:
        continue
    seen.add(c["text"]); uniq.append(c)
print("抽取到引语", len(uniq))
for c in uniq[:30]:
    print("  ", len(c["text"]), c["text"])

bank = json.load(open(BANK, encoding="utf-8"))
exist = {it["text"] for it in bank["items"]}
add = [c for c in uniq if c["text"] not in exist]
bank["items"].extend(add)
from collections import Counter
bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(it["type"] for it in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("新增", len(add), "| 现共", bank["count"], bank["by_type"])
