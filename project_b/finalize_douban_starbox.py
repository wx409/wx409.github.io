"""把豆瓣整理帖的主楼（一本杂志）落成：正文/图片/引语入池/更新目录"""
import json, os, re, urllib.request
from collections import Counter

BASE = r"E:\wx\私有\王晰全文库\采访目录"
IMG = os.path.join(BASE, "图片", "STARBOX_2019")
TXT = os.path.join(BASE, "全文")
os.makedirs(IMG, exist_ok=True); os.makedirs(TXT, exist_ok=True)
SRC = r"E:\wx\私有\王晰全文库\杂志\【王晰2019年杂志整理】 STARBOX 安全才是最短最近的距离.html"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"

h = open(SRC, encoding="utf-8", errors="ignore").read()
i, j = h.find("topic-richtext"), h.find("comment-item")
main = h[i:j]

def clean(s):
    s = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return "\n".join(x.strip() for x in s.replace("&nbsp;", " ").splitlines() if x.strip())

body = clean(main)
title_line = "STARBOX｜2019｜安全才是最短最近的距离"
open(os.path.join(TXT, "STARBOX_2019_豆瓣整理帖.txt"), "w", encoding="utf-8").write(
    "题目：%s\n来源：豆瓣整理帖（本地保存）\n年份：2019\n\n%s\n" % (title_line, body))

ck = open(r"E:\wx\index_records\douban.txt", encoding="utf-8", errors="ignore").read().strip()
if ck.lower().startswith("cookie:"):
    ck = ck.split(":", 1)[1].strip()
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
     "Referer": "https://www.douban.com/", "Cookie": ck}
urls = []
for u in re.findall(r'https?://img\d?\.doubanio\.com/view/[^"\'\s<>]+', main):
    u = u.split("?")[0]
    if "/icon/" in u or "avatar" in u:
        continue
    if u not in urls:
        urls.append(u)
ok = 0
for n, u in enumerate(urls, start=1):
    p = os.path.join(IMG, "img%02d.jpg" % n)
    if os.path.exists(p) and os.path.getsize(p) > 5000:
        ok += 1; continue
    try:
        d = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40).read()
        if len(d) > 5000:
            open(p, "wb").write(d); ok += 1
    except Exception:
        pass
print("正文", len(body), "字｜图片", len(urls), "张（成功", ok, "）")

# 引语入池
bank = json.load(open(BANK, encoding="utf-8"))
exist = {it["text"] for it in bank["items"]}
added = 0
for q in re.findall(r"[“\"]([^”\"]{10,90})[”\"]", body):
    q = q.strip().strip("，。、；：")
    if not (10 <= len(q) <= 90) or q in exist:
        continue
    exist.add(q)
    bank["items"].append({"text": q, "type": "interview",
                          "source": "杂志｜STARBOX 2019《安全才是最短最近的距离》",
                          "curated": False, "rights": "free", "mood": "quote_mag", "verified": True})
    added += 1
bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(it["type"] for it in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("引语入池", added, "| 词句共", bank["count"])

# 更新杂志目录
mp = os.path.join(BASE, "杂志目录.json")
cat = json.load(open(mp, encoding="utf-8"))
for c in cat["items"]:
    if c["杂志"] == "STARBOX":
        c.update({"期号": "2019", "图片数": len(urls),
                  "正文路径": "STARBOX_2019_豆瓣整理帖.txt",
                  "来源": "豆瓣整理帖（本地保存）｜主楼含封面+采访文字",
                  "状态": "已存（正文+图片）"})
cat["count"] = len(cat["items"])
json.dump(cat, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("目录已更新 STARBOX")
