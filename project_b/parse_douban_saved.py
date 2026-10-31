"""解析「浏览器另存的豆瓣页面」→ 杂志正文/图片/目录（不联网抓页面，只下载图片）

用法：
  python -X utf8 project_b/parse_douban_saved.py "E:\wx\私有\王晰全文库\采访目录\豆瓣_杂志整理.html"
说明：在浏览器里打开豆瓣整理帖 → Ctrl+S 保存「网页，仅 HTML」→ 跑本脚本。
图片仍用 cookie 下载（图床一般不过验证码）。
"""
import json, os, re, sys, time, urllib.request

BASE = r"E:\wx\私有\王晰全文库\采访目录"
IMG_DIR = os.path.join(BASE, "图片")
TXT_DIR = os.path.join(BASE, "全文")
os.makedirs(IMG_DIR, exist_ok=True); os.makedirs(TXT_DIR, exist_ok=True)

src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "豆瓣_杂志整理.html")
html = open(src, encoding="utf-8", errors="ignore").read()
print("读到", len(html), "字符")

ck = open(r"E:\wx\index_records\douban.txt", encoding="utf-8", errors="ignore").read().strip()
if ck.lower().startswith("cookie:"):
    ck = ck.split(":", 1)[1].strip()
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
     "Referer": "https://www.douban.com/", "Cookie": ck}

BRANDS = ["时尚芭莎", "芭莎", "ELLE", "男人装", "新周刊", "瑞丽", "嘉人", "红秀", "OK!", "风度",
          "时装", "乐活", "南都", "三联", "人物", "VOGUE", "GQ", "Figaro", "STARBOX", "NYLON",
          "优家", "Pioneer", "BROWN", "MOMENT", "小资", "视界", "先生", "格调", "画报", "周末画报",
          "SHIMO", "1626", "MODE", "CeCi", "ICON", "ELLEMEN", "睿士", "时尚先生", "健康之友", "名汇"]

def clean(h):
    h = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = h.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    return "\n".join(x.strip() for x in h.splitlines() if x.strip())

def imgs_of(h):
    out = []
    for pat in (r'data-original="([^"]+)"', r'data-src="([^"]+)"',
                r'src="(https?://[^"]*doubanio[^"]+)"', r'src="(https?://img\d[^"]+)"'):
        for u in re.findall(pat, h):
            u = u.split("?")[0]
            if "/icon/" in u or "avatar" in u:
                continue
            if u not in out:
                out.append(u)
    return out

blocks = re.findall(r'(?is)<div[^>]*class="[^"]*topic-richtext[^"]*"[^>]*>(.*?)</div>', html)
reps = re.findall(r'(?is)<div[^>]*class="[^"]*comment-item[^"]*"[^>]*>(.*?)(?=<div[^>]*class="[^"]*comment-item|</body>)', html)
items = [{"text": clean(b), "imgs": imgs_of(b)} for b in blocks + reps]
items = [x for x in items if x["text"] or x["imgs"]]
print("段落/楼层", len(items), "| 主楼", len(blocks), "| 回复", len(reps))

agg = {}
for e in items:
    b = next((k for k in BRANDS if k.lower() in e["text"].lower()), "未识别")
    a = agg.setdefault(b, {"texts": [], "imgs": []})
    if e["text"]:
        a["texts"].append(e["text"])
    for u in e["imgs"]:
        if u not in a["imgs"]:
            a["imgs"].append(u)

n_all = n_ok = 0
for b, a in agg.items():
    safe = re.sub(r"[\\/:*?\"<>|\s]+", "_", b)[:30]
    d = os.path.join(IMG_DIR, safe); os.makedirs(d, exist_ok=True)
    for i, u in enumerate(a["imgs"], start=1):
        n_all += 1
        p = os.path.join(d, "img%02d.jpg" % i)
        if os.path.exists(p) and os.path.getsize(p) > 5000:
            n_ok += 1; continue
        try:
            data = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40).read()
            if len(data) > 5000:
                open(p, "wb").write(data); n_ok += 1
            time.sleep(1.0)
        except Exception:
            pass
    if a["texts"]:
        open(os.path.join(TXT_DIR, "%s_豆瓣整理帖.txt" % safe), "w", encoding="utf-8").write("\n\n".join(a["texts"]))

mp = os.path.join(BASE, "杂志目录.json")
cat = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {"items": []}
have = {c["杂志"] for c in cat["items"]}
add = 0
for b, a in agg.items():
    if b == "未识别" or b in have:
        continue
    cat["items"].append({"杂志": b, "年份": "2019", "期号": "", "采访者": "",
                         "来源": "豆瓣整理帖（本地保存）", "微博": "",
                         "图片数": len(a["imgs"]),
                         "正文路径": "%s_豆瓣整理帖.txt" % re.sub(r"[\\/:*?\"<>|\s]+", "_", b)[:30],
                         "状态": "已存（豆瓣整理帖）"})
    add += 1
cat["count"] = len(cat["items"])
cat["items"].sort(key=lambda x: (x.get("年份") or "9999", x.get("杂志", "")))
json.dump(cat, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("图片", n_all, "张（成功", n_ok, "）｜新增杂志", add, "｜目录共", cat["count"])
for b in list(agg)[:12]:
    print("  ", b, "| 图", len(agg[b]["imgs"]))
