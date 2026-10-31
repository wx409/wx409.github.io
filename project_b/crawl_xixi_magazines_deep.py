"""深挖「王晰Elvis-晰息相关」杂志帖：按刊名关键词过滤，抽刊名/年份/图片"""
import json, re, time, urllib.request, email.utils

UID = "7215995153"
CK = open(r"E:\wx\index_records\wb.txt", encoding="utf-8").read().strip()
H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
     "Referer": "https://m.weibo.cn/", "Cookie": CK, "X-Requested-With": "XMLHttpRequest"}
OUT = r"E:\wx\私有\王晰全文库\采访目录\杂志预告帖.json"

MAGWORD = re.compile(r"杂志|封面|内页|预售|开售|上线|发售|写真|芭莎|ELLE|男人装|新周刊|瑞丽|嘉人|红秀|OK!|风度|时装|乐活|南都|三联|人物|VOGUE|GQ|Esquire|Figaro|STARBOX|Pioneer|NYLON|BROWN|MOMENT|优家|小资|视界|时尚|先生|格调|周刊|画报|刊")
ISSUE = re.compile(r"(20\d{2})\s*年?\s*(\d{1,2})\s*月|第?\s*(\d{1,2})\s*期|(\d{4})\s*年(\d{1,2})月")
BRANDS = ["时尚芭莎", "芭莎", "ELLE", "男人装", "新周刊", "瑞丽", "嘉人", "红秀", "OK!", "风度",
          "时装", "乐活", "南都", "三联", "人物", "VOGUE", "GQ", "Figaro", "STARBOX", "NYLON",
          "优家", "Pioneer", "BROWN", "MOMENT", "小资", "视界", "先生", "格调", "画报", "周末画报"]

posts = {}
since, empty = None, 0
for page in range(0, 120):
    u = "https://m.weibo.cn/api/container/getIndex?containerid=107603%s" % UID
    if since:
        u += "&since_id=%s" % since
    try:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=25).read().decode("utf-8", "ignore"))
    except Exception:
        time.sleep(3); continue
    cards = r.get("data", {}).get("cards", [])
    if not cards:
        break
    n = 0
    for c in cards:
        m = c.get("mblog")
        if not m:
            continue
        n += 1
        txt = re.sub(r"<[^>]+>", "", m.get("text") or "")
        if not MAGWORD.search(txt):
            continue
        try:
            dt = email.utils.parsedate_to_datetime(m.get("created_at", "")).strftime("%Y-%m-%d")
        except Exception:
            dt = ""
        brand = next((b for b in BRANDS if b.lower() in txt.lower()), "")
        iss = ISSUE.search(txt + " " + (m.get("page_info", {}) or {}).get("page_title", ""))
        posts[m.get("id")] = {"date": dt, "brand": brand,
                              "issue": iss.group(0) if iss else "",
                              "text": txt[:260],
                              "pics": [p.get("large", {}).get("url") or p.get("url") for p in (m.get("pics") or [])],
                              "link": "https://m.weibo.cn/detail/%s" % m.get("id")}
    if n == 0:
        break
    since = r.get("data", {}).get("cardlistInfo", {}).get("since_id")
    if not since:
        break
    time.sleep(0.7)

items = sorted(posts.values(), key=lambda x: x["date"], reverse=True)
json.dump({"generated": "2026-10-31", "account": "王晰Elvis-晰息相关", "uid": UID,
           "count": len(items), "items": items},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

from collections import Counter
c = Counter(i["brand"] or "未识别" for i in items)
print("杂志类帖", len(items), "| 刊名分布", dict(c.most_common(10)))
for i in items[:12]:
    print("  %s %-8s %s | 图%d | %s" % (i["date"], i["brand"] or "?", i["issue"][:10],
                                        len(i["pics"]), i["text"][:40].replace("\n", " ")))
