"""统一采访目录：xlsx 16 条 + 已抓网页 + 新发现；按媒体+年份排序；标全文状态"""
import json, os, re, ssl, urllib.request
import openpyxl

ROOT = r"D:\wx409.github.io"
OUT = r"E:\wx\私有\王晰全文库\采访目录"
BANK = os.path.join(ROOT, "data", "phrase_bank.json")
XLSX = r"E:\wx\骰子周边20260608\GEO\GEO\王晰采访记录汇编.xlsx"
os.makedirs(OUT, exist_ok=True)

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def get(url, timeout=30):
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=timeout, context=ctx).read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "ignore")

def text_of(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = h.replace("&nbsp;", " ").replace("&quot;", '"').replace("&amp;", "&")
    h = re.sub(r"[ \t]+", " ", h)
    return "\n".join(x.strip() for x in h.splitlines() if len(x.strip()) >= 8)

catalog = []

def add(题目, 媒体, 年份, url="", 备注="", 类型="文字采访"):
    catalog.append({"题目": 题目.strip(), "媒体": 媒体, "年份": str(年份), "类型": 类型,
                    "url": url, "采访者": "", "全文路径": "", "字数": 0, "状态": "待抓", "备注": 备注})

# 1) xlsx
ws = openpyxl.load_workbook(XLSX, read_only=True, data_only=True).active
for i, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
    if not r or not r[0]:
        continue
    name = str(r[1] or "").strip()
    who = str(r[2] or "").strip()
    note = str(r[4] or "").strip()
    body = str(r[5] or "").strip() if len(r) > 5 and r[5] else ""
    y = re.search(r"(20\d{2}|19\d{2})", name + note)
    add(name or "（未命名）", "汇编：" + (who or "未标"), y.group(1) if y else "",
        备注=("正文已在汇编内（%d 字）" % len(body)) if body else note[:40], 类型="汇编条目")
    if body:
        catalog[-1]["字数"] = len(body)
        catalog[-1]["状态"] = "全文（汇编内）"

# 2) 已抓网页全文
p = os.path.join(OUT, "采访目录.json")
if os.path.exists(p):
    for it in json.load(open(p, encoding="utf-8")).get("items", []):
        add(it.get("题目", ""), it.get("来源", ""), (it.get("日期") or "")[:4],
            url=it.get("url", ""), 备注=it.get("备注", ""))
        catalog[-1]["全文路径"] = it.get("全文路径", "")
        catalog[-1]["字数"] = it.get("字数", 0)
        catalog[-1]["状态"] = "全文已存" if it.get("全文路径") else "需人工补"

# 3) 新增线索（含杂志）
NEW = [
    ("大牌档｜行走的大提琴王晰：34岁男人成熟的魅力", "南方+", "2019", "https://static.nfapp.southcn.com/content/201906/28/c2369010.html", "文字采访"),
    ("《背后》走进王晰：用音乐创造自己的安全区", "360快传（转载）", "2025", "https://www.360kuai.com/pc/detail?url=http%3A%2F%2Fzm.news.so.com%2F293a8e1a1e2e49d19df871db4e3918c5", "节目转载"),
    ("【王晰2019年杂志整理】STARBOX 等", "豆瓣（粉丝整理）", "2019", "https://www.douban.com/group/topic/169052056/", "杂志目录（可枚举）"),
    ("ELLE世界时装之苑 2021 年 4 期（含王晰）", "ELLE", "2021", "https://m.fx361.com/bk/ellesjszzy/20214.html", "杂志"),
    ("星月对话｜王晰：就要跟音乐谈恋爱", "微信公众号", "", "https://mp.weixin.qq.com/s?__biz=MzA3MDgzMzEwNQ==&mid=2652058593&idx=1&sn=44e246d0a38478c653b993e5f8ff1e67", "公众号"),
]
for t, m, y, u, k in NEW:
    add(t, m, y, url=u, 类型=k)

# 4) 抓全文（新线索里能抓的）
QUOTE = re.compile(r"[“\"]([^”\"]{10,70})[”\"]")
added_q = 0
for c in catalog:
    if c["状态"] in ("全文已存", "全文（汇编内）") or not c["url"]:
        continue
    try:
        body = text_of(get(c["url"]))
        if len(body) >= 800:
            fn = re.sub(r"[\\/:*?\"<>|\s]+", "_", c["题目"])[:56] + ".txt"
            with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
                f.write("题目：%s\n媒体：%s\n年份：%s\nURL：%s\n\n%s\n" % (c["题目"], c["媒体"], c["年份"], c["url"], body))
            c["全文路径"], c["字数"], c["状态"] = fn, len(body), "全文已存"
        else:
            c["状态"] = "需人工补"
            c["备注"] = (c["备注"] + "｜抓取过短").strip("｜")
    except Exception as e:
        c["状态"] = "需人工补"
        c["备注"] = (c["备注"] + "｜抓取失败:" + type(e).__name__).strip("｜")

# 去重 + 排序（媒体 → 年份）
uniq, seen = [], set()
for c in catalog:
    k = (c["题目"], c["媒体"])
    if k in seen:
        continue
    seen.add(k); uniq.append(c)
uniq.sort(key=lambda c: (c["媒体"], c["年份"] or "9999", c["题目"]))

json.dump({"updated": "2026-10-31", "count": len(uniq),
           "fields": ["题目", "媒体", "年份", "类型", "url", "采访者", "全文路径", "字数", "状态", "备注"],
           "note": "全文落本地私有库（不入 git、不上站）；此表按 媒体→年份 排序",
           "items": uniq},
          open(os.path.join(OUT, "采访目录.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

md = ["# 王晰采访目录（按媒体→年份）", "", "| 媒体 | 年份 | 题目 | 状态 |", "|---|---|---|---|"]
for c in uniq:
    md.append("| %s | %s | %s | %s |" % (c["媒体"], c["年份"] or "—", c["题目"][:40], c["状态"]))
open(os.path.join(OUT, "采访目录.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

from collections import Counter
st = Counter(c["状态"] for c in uniq)
print("目录", len(uniq), dict(st))
for c in uniq:
    print("  %-12s %-5s %-30s %s" % (c["媒体"][:12], c["年份"] or "—", c["题目"][:30], c["状态"]))
