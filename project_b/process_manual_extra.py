"""补充 4 条（用户提供链接）→ 下载视频/图片 → 排队转写"""
import json, os, re, time, urllib.request

BASE = r"E:\wx\私有\王晰全文库\采访目录"
TXT = os.path.join(BASE, "全文"); VID = os.path.join(BASE, "视频"); IMG = os.path.join(BASE, "图片")
Q = os.path.join(BASE, "处理队列.json")
for d in (TXT, VID, IMG):
    os.makedirs(d, exist_ok=True)

CK = open(r"E:\wx\index_records\wb.txt", encoding="utf-8", errors="ignore").read().strip()
H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
     "Referer": "https://m.weibo.cn/", "Cookie": CK, "X-Requested-With": "XMLHttpRequest"}

EXTRA = [
    {"slug": "东方艺享家_视频播客_秦屹x王晰", "title": "《东方艺享家》视频播客（主持人秦屹 × 王晰）",
     "date": "2026-06-17", "mid": "5310912452100760",
     "note": "视频播客，官方摘要：年少苦练声乐、乐感与热忱"},
    {"slug": "民族歌曲讲座_范唱与问答", "title": "中国各地民族歌曲讲座（含 14 首清唱 + Bonus 2 首）",
     "date": "", "mid": "5211769532582362",
     "note": "讲座 0:00-05:54｜范唱 05:54-16:06｜问答 16:06-16:40｜Bonus 16:41-19:31；"
             "清唱：花儿为什么这样红/燕子/青藏高原/嘎达梅林/鸿雁/乌苏里船歌/大姑娘美大姑娘浪/阿里郎/"
             "小河淌水/洪湖水浪打浪/茉莉花v1/茉莉花v2/山歌好比春江水；Bonus：梨花颂/喀秋莎"},
    {"slug": "草原之夜发布会_后台采访", "title": "《草原之夜》发布会后台采访（新疆题材/草原题材）",
     "date": "2025-12-22", "mid": "5246634113106550", "note": "东方演艺集团歌舞剧《草原之夜》"},
    {"slug": "沉响与长歌_报道_身兼制作人", "title": "《沉响与长歌》报道：既要有艺术性也要有娱乐性（身兼制作人）",
     "date": "2026-10-18", "mid": "5355452393327048", "note": "北京天桥艺术中心上演"},
]

q = json.load(open(Q, encoding="utf-8")) if os.path.exists(Q) else {"items": []}
have = {it.get("slug") for it in q["items"]}

for e in EXTRA:
    if e["slug"] in have:
        continue
    try:
        r = json.loads(urllib.request.urlopen(
            urllib.request.Request("https://m.weibo.cn/statuses/show?id=%s" % e["mid"], headers=H), timeout=30
        ).read().decode("utf-8", "ignore"))
    except Exception as ex:
        print("拉取失败", e["slug"], type(ex).__name__); continue
    d = r.get("data") or {}
    text = re.sub(r"<[^>]+>", "", d.get("text") or "")
    pics = [p.get("large", {}).get("url") or p.get("url") for p in (d.get("pics") or [])]
    pi = d.get("page_info") or {}
    vurl = ""
    if pi.get("media_info"):
        mi = pi["media_info"]
        vurl = mi.get("stream_url") or mi.get("mp4_720p_mp4") or mi.get("mp4_hd_url") or ""
    body = "名称：%s\n时间：%s\n链接：https://weibo.com/%s/%s\n备注：%s\n\n%s\n" % (
        e["title"], e["date"], "", e["mid"], e["note"], text)
    open(os.path.join(TXT, e["slug"] + ".txt"), "w", encoding="utf-8").write(
        "名称：%s\n时间：%s\n链接：https://weibo.com/%s/%s\n备注：%s\n\n%s\n"
        % (e["title"], e["date"], "", e["mid"], e["note"], text))

    vpath = ""
    if vurl:
        p = os.path.join(VID, e["slug"] + ".mp4")
        if not (os.path.exists(p) and os.path.getsize(p) > 100000):
            try:
                data = urllib.request.urlopen(urllib.request.Request(vurl, headers=H), timeout=300).read()
                if len(data) > 100000:
                    open(p, "wb").write(data)
            except Exception as ex:
                print("视频失败", e["slug"], type(ex).__name__)
        if os.path.exists(p):
            vpath = e["slug"] + ".mp4"

    idir = ""
    if pics:
        d0 = os.path.join(IMG, e["slug"]); os.makedirs(d0, exist_ok=True)
        for i, u in enumerate(pics, start=1):
            pp = os.path.join(d0, "img%02d.jpg" % i)
            if os.path.exists(pp):
                continue
            try:
                b = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60).read()
                if len(b) > 5000:
                    open(pp, "wb").write(b)
            except Exception:
                pass
        if os.listdir(d0):
            idir = d0

    q["items"].append({"slug": e["slug"], "title": e["title"], "date": e["date"],
                       "link": "https://weibo.com/%s/%s" % ("", e["mid"]),
                       "text_path": e["slug"] + ".txt", "text_len": len(text),
                       "pics": pics, "video": vurl, "video_path": vpath, "image_dir": idir,
                       "transcript": "", "ocr": "",
                       "status": "待转写" if vpath else ("待OCR" if idir else "原文已存")})
    print("新增 %-34s 视频%s 图%d 文字%d" % (e["slug"][:34], "有" if vpath else "无", len(pics), len(text)))
    time.sleep(0.8)

json.dump(q, open(Q, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print("队列", len(q["items"]), dict(Counter(i["status"] for i in q["items"])))
