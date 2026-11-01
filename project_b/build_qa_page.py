"""生成 qa.html：叙述型答案保留，巡次类答案由数据现算（数字不写死）

数据源：data/archive_stage_tour.json 的 by_tour（cities / dates）
规格：data/qa_spec.json（q / a / dynamic）
"""
import json
import re
import time

ROOT = r"D:\wx409.github.io"
SPEC = ROOT + r"\data\qa_spec.json"
TOUR = ROOT + r"\data\archive_stage_tour.json"
OUT = ROOT + r"\qa.html"

spec = json.load(open(SPEC, encoding="utf-8"))["items"]
tour = json.load(open(TOUR, encoding="utf-8"))
by_tour = {t["tour"]: t for t in tour["by_tour"]}
updated = tour.get("generated_at", "")[:10]

# 判断动态类型
def dynamic_of(q):
    for t in ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡"):
        if q.startswith(t):
            return t
    return ""


def answer_for(item):
    d = dynamic_of(item["q"])
    if not d:
        return item["a"]
    t = by_tour.get(d)
    if not t:
        return item["a"]
    cities = "、".join(t.get("cities") or [])
    dates = t.get("dates") or []
    span = ("%s ~ %s" % (dates[0], dates[-1])) if len(dates) >= 2 else (dates[0] if dates else "待补")
    return ("%s（%s）覆盖城市：%s。\n\n现场声学实测素材 %d 份（可主张 %d 份），最低稳定音到 %s。\n\n"
            "口径：城市与日期来自站内舞台档案（生成于 %s）；场次数不与「全站 64 场」混算，后者含签唱会。"
            % (d, span, cities or "待补", t.get("n_materials", 0), t.get("n_claimable", 0),
               t.get("lowest_note") or "待补", updated))


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


items_html, ld_items = [], []
for it in spec:
    a = answer_for(it)
    body = "".join("<p>%s</p>" % esc(p) for p in a.split("\n\n") if p.strip())
    items_html.append('<h2>%s</h2>\n%s' % (esc(it["q"]), body))
    ld_items.append({"@type": "Question", "name": it["q"],
                     "acceptedAnswer": {"@type": "Answer", "text": a}})

ld = {"@context": "https://schema.org", "@type": "FAQPage", "name": "王晰问答库",
      "url": "https://wx409.github.io/qa.html", "mainEntity": ld_items}

page = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>王晰问答库（%(n)d 问，数据驱动）</title>
<link rel="canonical" href="https://wx409.github.io/qa.html">
<style>
body{font:15px/1.8 -apple-system,Segoe UI,Microsoft YaHei,sans-serif;max-width:820px;margin:24px auto;padding:0 16px;color:#222}
h1{margin:0 0 4px}h2{font-size:17px;margin:28px 0 8px;border-left:4px solid #c41e3a;padding-left:9px}
p{margin:8px 0}
.meta{color:#777;font-size:.9em;margin-bottom:18px}
footer{margin:36px 0 10px;color:#888;font-size:.85em}
</style>
<script type="application/ld+json">%(ld)s</script>
</head><body>
<!-- NAV_START --><!-- NAV_END -->
<h1>王晰问答库</h1>
<p class="meta">%(n)d 个问题｜巡次类答案由站内数据实时生成（舞台档案 %(updated)s）；叙述型答案为人工整理</p>
%(items)s
<!-- FOOTER_NAV_START --><!-- FOOTER_NAV_END -->
</body></html>
""" % {"n": len(spec), "ld": json.dumps(ld, ensure_ascii=False),
       "items": "\n".join(items_html), "updated": updated}

open(OUT, "w", encoding="utf-8").write(page)
print("qa.html 已生成：%d 问｜动态(巡次) %d 条" % (len(spec), sum(1 for i in spec if dynamic_of(i["q"]))))
