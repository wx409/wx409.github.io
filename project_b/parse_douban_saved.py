"""解析豆瓣整理帖（浏览器另存）→ 杂志正文/图片/目录 v2：按字符串切分，避免嵌套 div 截断"""
import json, os, re, sys, time, urllib.request

BASE = r"E:\wx\私有\王晰全文库\采访目录"
IMG_DIR = os.path.join(BASE, "图片")
TXT_DIR = os.path.join(BASE, "全文")
os.makedirs(IMG_DIR, exist_ok=True); os.makedirs(TXT_DIR, exist_ok=True)

src = sys.argv[1]
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
          "SHIMO", "1626", "MODE", "CeCi", "ICON", "ELLEMEN", "睿士", "时尚先生", "健康之友", "名汇",
          "新京报", "Size", "潮流", "Milk", "YOHO"]

def clean(h):
    h = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = h.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    return "\n".join(x.strip() for x in h.splitlines() if x.strip())

IMGURL = re.compile(r'https?://img\d?\.doubanio\.com/view/(?:group_topic|status|note|subject)/[^"\')\s<>]+')

def seg_images(seg):
    out = []
    for u in IMGURL.findall(seg):
        u = u.split("?")[0].replace("/l/public/", "/l/public/").replace("/raw/", "/raw/")
        if u not in out:
            out.append(u)
    return out

# 主楼：topic-richtext 起，到第一个 comment-item 之前
i = html.find('topic-richtext')
j = html.find('comment-item')
main = html[i:j] if i >= 0 and j > i else html[max(0, i):i + 400000]

# 回复：按 comment-item 切
parts = html.split('comment-item')
reps = ['comment-item' + p[:120000] for p in parts[1:]]

items = [{"text": clean(main), "imgs": seg_images(main), "kind": "主楼"}]
for p in reps:
    items.append({"text": clean(p), "imgs": seg_images(p), "kind": "回复"})

n_img_total = sum(len(x["imgs"]) for x in items)
print("段落", len(items), "| 主楼图", len(items[0]["imgs"]), "| 回复", len(reps), "| 图 URL 总", n_img_total)

# 按杂志聚合：回复里出现杂志名就归属该杂志，否则归主楼
agg = {}
for it in items:
    txt = it["text"]
    hits = [b for b in BRANDS if b.lower() in txt.lower()]
    keys = hits or ["主楼"]
    for k in keys:
        a = agg.setdefault(k, {"texts": [], "imgs": []})
        if txt:
            a["texts"].append(txt)
        for u in it["imgs"]:
            if u not in a["imgs"]:
                a["imgs"].append(u)

n_all = n_ok = 0
for b, a in agg.items():
    safe = re.sub(r"[\\/:*?\"<>|\s]+", "_", b)[:30]
    d = os.path.join(IMG_DIR, safe); os.makedirs(d, exist_ok=True)
    for i2, u in enumerate(a["imgs"], start=1):
        n_all += 1
        p = os.path.join(d, "img%02d.jpg" % i2)
        if os.path.exists(p) and os.path.getsize(p) > 5000:
            n_ok += 1; continue
        try:
            data = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40).read()
            if len(data) > 5000:
                open(p, "wb").write(data); n_ok += 1
            time.sleep(0.8)
        except Exception:
            pass
    if a["texts"]:
        open(os.path.join(TXT_DIR, "%s_豆瓣整理帖.txt" % safe), "w", encoding="utf-8").write("\n\n".join(a["texts"]))

mp = os.path.join(BASE, "杂志目录.json")
cat = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {"items": []}
have = {c["杂志"] for c in cat["items"]}
add = 0
for b, a in agg.items():
    if b in ("主楼", "未识别") or b in have:
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
for b, a in list(agg.items())[:14]:
    print("  ", b, "| 图", len(a["imgs"]), "| 文", sum(len(t) for t in a["texts"]))
