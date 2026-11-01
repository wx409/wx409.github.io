"""从抓下来的网页里抽「他本人的话」：Q&A 行（王晰：）＋ 第一人称引号段

用法：python -X utf8 project_b/import_page_interviews.py [--dry]
"""
import argparse
import glob
import json
import os
import re
from collections import Counter

PAGES = r"E:\wx\私有\王晰全文库\采访目录\网页"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"

QA = re.compile(r"王晰[：:]\s*(.+?)(?=(?:记者|主持人|问[：:]|【|——|$))", re.S)
QUOTE = re.compile(r"[“「]([^”」]{12,90})[”」]")
FIRST = re.compile(r"[我咱]")
SKIP_TITLE = ("百科", "wiki", "词条")
BAD = ("点击", "扫描", "关注", "来源", "编辑", "责任编辑", "原标题", "举报", "版权")


def sentences(text):
    for seg in re.split(r"[。！？；\n]", text):
        s = re.sub(r"\s+", "", seg).strip("，、 ")
        if 12 <= len(s) <= 60:
            yield s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    bank = json.load(open(BANK, encoding="utf-8"))
    exist = {re.sub(r"\s", "", i["text"]) for i in bank["items"]}
    added = []

    for p in sorted(glob.glob(os.path.join(PAGES, "*.txt"))):
        raw = open(p, encoding="utf-8", errors="ignore").read()
        head, _, body = raw.partition("\n\n")
        title = (re.search(r"标题：(.+)", head).group(1).strip() if "标题：" in head else "")
        if any(s in title for s in SKIP_TITLE):
            continue
        src = "网页访谈｜%s" % (title[:34] or os.path.basename(p)[:24])

        cands = []
        for m in QA.finditer(body):
            cands += list(sentences(m.group(1)))
        for q in QUOTE.findall(body):
            if FIRST.search(q):
                cands += list(sentences(q))

        n0 = len(added)
        for s in cands:
            if any(b in s for b in BAD):
                continue
            if not FIRST.search(s):
                continue
            if s in exist:
                continue
            exist.add(s)
            added.append({"text": s, "type": "interview", "source": src,
                          "curated": False, "rights": "free", "mood": "quote_mag",
                          "verified": False, "quality": "mid"})
        print("%-42s +%d" % (os.path.basename(p)[:40], len(added) - n0))

    print("\n合计新增 %d 条" % len(added))
    if a.dry:
        for x in added[:15]:
            print("  ", x["text"][:56], "|", x["source"][:26])
        return 0

    bank["items"].extend(added)
    bank["count"] = len(bank["items"])
    bank["by_type"] = dict(Counter(i["type"] for i in bank["items"]))
    bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
    json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("现共 %d" % bank["count"])
    for x in added[:12]:
        print("  ", x["text"][:56], "|", x["source"][:26])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
