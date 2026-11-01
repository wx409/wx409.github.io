"""词句库检索（链式召回）：给一句/一个词，找库里最相关的句子

用法：
  python -X utf8 project_b/phrase_search.py --q "低音 大海"
  python -X utf8 project_b/phrase_search.py --similar "我一想到你们在的话我会非常非常的温暖" --top 8
  python -X utf8 project_b/phrase_search.py --stats
  python -X utf8 project_b/phrase_search.py --type lyrics --q "月亮"

原理：字符 bigram + 词频倒排（无外部依赖），相似度 = 加权 Jaccard。
"""
import argparse
import json
import math
import re
from collections import Counter, defaultdict

BANK = r"D:\wx409.github.io\data\phrase_bank.json"


def grams(s):
    s = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", s or "")
    if len(s) < 2:
        return set(s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", default="")
    ap.add_argument("--similar", default="")
    ap.add_argument("--type", default="")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()

    bank = json.load(open(BANK, encoding="utf-8"))
    items = bank["items"]

    if a.stats:
        by_type = Counter(i["type"] for i in items)
        by_q = Counter(i.get("quality", "high") for i in items)
        print("总 %d 条" % len(items))
        print("按类型:", dict(by_type))
        print("按质量:", dict(by_q))
        return 0

    query = a.similar or a.q
    if not query:
        print("需要 --q 或 --similar")
        return 2

    pool = [i for i in items if not a.type or i["type"] == a.type]
    qg = grams(query)
    df = defaultdict(int)
    for it in pool:
        for g in grams(it["text"]) | grams(it.get("source", "")):
            df[g] += 1
    n = max(len(pool), 1)

    def score(it):
        tg = grams(it["text"]) | grams(it.get("source", ""))
        if not tg:
            return 0.0
        inter = qg & tg
        if not inter:
            return 0.0
        w = sum(math.log(1 + n / (1 + df.get(g, 0))) for g in inter)
        return w / math.sqrt(len(tg) + 1) * (2 if it.get("quality") == "high" else 1)

    ranked = sorted(((score(it), it) for it in pool), key=lambda x: -x[0])
    shown = 0
    for s, it in ranked:
        if s <= 0:
            break
        print("%.2f [%s/%s] %s\n      ← %s" % (s, it["type"], it.get("quality", "?"),
                                              it["text"], it.get("source", "")))
        shown += 1
        if shown >= a.top:
            break
    if not shown:
        print("没有相关句（换个关键词试试）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
