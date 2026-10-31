"""豆瓣整理帖 → 杂志目录（正文 + 图片 + 回填表）

用法：python -X utf8 project_b/crawl_douban_magazines.py [topic_url]
默认抓 https://www.douban.com/group/topic/169052056/ （王晰2019年杂志整理）
"""
import json, os, re, sys, time, urllib.request, urllib.parse

CK_PATH = r"E:\wx\index_records\douban.txt"
BASE = r"E:\wx\私有\王晰全文库\采访目录"
IMG_DIR = os.path.join(BASE, "图片")
TXT_DIR = os.path.join(BASE, "全文")
TOPIC = sys.argv[1] if len(sys.argv) > 1 else "https://www.douban.com/group/topic/169052056/"
os.makedirs(IMG_DIR, exist_ok=True); os.makedirs(TXT_DIR, exist_ok=True)

ck = open(CK_PATH, encoding="utf-8", errors="ignore").read().strip()
if ck.lower().startswith("cookie:"):
    ck = ck.split(":", 1)[1].strip()
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
     "Referer": "https://www.douban.com/group/", "Cookie": ck,
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
     "Accept-Language": "zh-CN,zh;q=0.9", "Connection": "keep-alive"}

def fetch(url, binary=False):
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=H)
            data = urllib.request.urlopen(req, timeout=40).read()
            if not binary and len(data) < 20000:
                last = data
                time.sleep(6)
                continue
            return data if binary else data.decode("utf-8", "ignore")
        except Exception as e:
            last = None
            time.sleep(6)
    if last:
        return last.decode("utf-8", "ignore")
    raise RuntimeError("fetch failed")

def clean(h):
    h = re.sub(r"(?is)<br\s*/?>|</p>|</div>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = h.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    return "\n".join(x.strip() for x in h.splitlines() if x.strip())

BRANDS = ["时尚芭莎", "芭莎", "ELLE", "男人装", "新周刊", "瑞丽", "嘉人", "红秀", "OK!", "风度",
          "时装", "乐活", "南都", "三联", "人物", "VOGUE", "GQ", "Figaro", "STARBOX", "NYLON",
          "优家", "Pioneer", "BROWN", "MOMENT", "小资", "视界", "先生", "格调", "画报", "周末画报",
          "SHIMO", "1626", "MODE", "CeCi", "ICON", "ELLEMEN", "睿士", "时尚先生", "健康之友"]

def brand_of(t):
    low = t.lower()
    for b in BRANDS:
        if b.lower() in low:
            return b
    return ""

html = fetch(TOPIC)
title = re.search(r"<title>(.*?)</title>", html, re.S)
title = clean(title.group(1))[0] if title else "豆瓣整理帖"

# 楼层：正文块与回复块
blocks = re.findall(r'(?is)<div[^>]*class="[^"]*topic-richtext[^"]*"[^>]*>(.*?)</div>', html)
replies = re.findall(r'(?is)<div[^>]*class="[^"]*comment-item[^"]*"[^>]*>(.*?)(?=<div[^>]*class="[^"]*comment-item|<div id="comments|</body>)', html)

# 图片：优先 data-original / data-src / src（豆瓣图床）
def imgs_of(h):
    urls = []
    for pat in (r'data-original="([^"]+)"', r'data-src="([^"]+)"', r'src="(https://img\d*\.doubanio\.com[^"]+)"',
                r'src="(https://[^"]*doubanio[^"]+)"'):
        urls += re.findall(pat, h)
    out = []
    for u in urls:
        u = u.split("?")[0]
        if "/icon/" in u or "avatar" in u:
            continue
        if u not in out:
            out.append(u)
    return out

entries = []
for b in blocks + replies:
    txt = clean(b)
    if not txt or len(txt) < 4:
        continue
    entries.append({"text": txt, "imgs": imgs_of(b)})

print("解析到楼层/回复", len(entries), "｜标题", title[:40])
if not entries:
    print("页面无内容，可能被反爬或 cookie 失效：", html[:180].replace("\n", " "))
    raise SystemExit(2)

# 按杂志聚合
agg = {}
for e in entries:
    b = brand_of(e["text"]) or "未识别"
    a = agg.setdefault(b, {"texts": [], "imgs": []})
    a["texts"].append(e["text"])
    for u in e["imgs"]:
        if u not in a["imgs"]:
            a["imgs"].append(u)

n_img = n_ok = 0
for b, a in agg.items():
    safe = re.sub(r"[\\/:*?\"<>|\s]+", "_", b)[:30]
    d = os.path.join(IMG_DIR, safe)
    os.makedirs(d, exist_ok=True)
    for i, u in enumerate(a["imgs"], start=1):
        n_img += 1
        p = os.path.join(d, "img%02d.jpg" % i)
        if os.path.exists(p) and os.path.getsize(p) > 5000:
            n_ok += 1; continue
        try:
            data = fetch(u, binary=True)
            if len(data) > 5000:
                open(p, "wb").write(data); n_ok += 1
            time.sleep(1.2)
        except Exception:
            pass
    if a["texts"]:
        with open(os.path.join(TXT_DIR, "%s_豆瓣整理帖.txt" % safe), "w", encoding="utf-8") as f:
            f.write("\n\n".join(a["texts"]))

# 回填杂志目录
mp = os.path.join(BASE, "杂志目录.json")
cat = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {"items": []}
have = {c["杂志"] for c in cat["items"]}
add = 0
for b, a in agg.items():
    if b == "未识别" or b in have:
        continue
    cat["items"].append({"杂志": b, "年份": "2019", "期号": "", "采访者": "",
                         "来源": "豆瓣整理帖｜%s" % TOPIC, "微博": "",
                         "图片数": len(a["imgs"]),
                         "正文路径": "%s_豆瓣整理帖.txt" % re.sub(r"[\\/:*?\"<>|\s]+", "_", b)[:30],
                         "状态": "已存（豆瓣整理帖）"})
    add += 1
cat["count"] = len(cat["items"])
cat["items"].sort(key=lambda x: (x.get("年份") or "9999", x.get("杂志", "")))
json.dump(cat, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("图片", n_img, "张（成功", n_ok, "）｜新增杂志条目", add, "｜目录共", cat["count"])
