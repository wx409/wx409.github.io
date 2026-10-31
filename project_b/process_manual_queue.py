"""处理「待人工清单」里由人工核对过的 8 条：抓微博原文/视频/图片 → 转写/OCR → 入库根表

用法：
  python -X utf8 project_b/process_manual_queue.py            # 抓原文+落媒体，并生成本地任务清单
  python -X utf8 project_b/process_manual_queue.py --media     # 追加：下载视频/图片
输出：
  采访目录\\全文\\<slug>.txt          微博原文
  采访目录\\视频\\<slug>.mp4          视频（待转写）
  采访目录\\图片\\<slug>\\imgNN.jpg   图片（待 OCR）
  采访目录\\处理队列.json             给转写/OCR 用的任务表
"""
import json, os, re, sys, time, urllib.request
from datetime import date

BASE = r"E:\wx\私有\王晰全文库\采访目录"
MD = os.path.join(BASE, "待人工清单.md")
TXT = os.path.join(BASE, "全文")
VID = os.path.join(BASE, "视频")
IMG = os.path.join(BASE, "图片")
QUEUE = os.path.join(BASE, "处理队列.json")
for d in (TXT, VID, IMG):
    os.makedirs(d, exist_ok=True)

CK = open(r"E:\wx\index_records\wb.txt", encoding="utf-8", errors="ignore").read().strip()
H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
     "Referer": "https://m.weibo.cn/", "Cookie": CK, "X-Requested-With": "XMLHttpRequest"}

def get(url, timeout=30):
    return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=timeout).read()

def slug(s):
    return re.sub(r"[\\/:*?\"<>|\s]+", "_", s)[:46]

# 解析清单
lines = open(MD, encoding="utf-8").read().splitlines()
entries = []
for l in lines:
    if "m.weibo.cn/detail/" not in l:
        continue
    m = re.search(r"m\.weibo\.cn/detail/(\d+)", l)
    if not m:
        continue
    d = re.search(r"\[(\d{4}-\d{2}-\d{2})\]", l) or re.search(r"(\d{4}-\d{2}-\d{2})", l)
    title = re.sub(r"^[*\s\\]*(?:\[[^\]]+\])?\s*", "", l).split("（")[0].strip()
    title = re.sub(r"→.*$", "", title).strip()[:70]
    entries.append({"date": d.group(1) if d else "", "title": title, "mid": m.group(1),
                    "link": "https://m.weibo.cn/detail/%s" % m.group(1)})

print("清单条目", len(entries))
queue = []
for e in entries:
    s = slug(e["title"] or e["mid"])
    try:
        r = json.loads(get("https://m.weibo.cn/statuses/show?id=%s" % e["mid"]).decode("utf-8", "ignore"))
    except Exception as ex:
        print("  拉取失败", e["mid"], type(ex).__name__)
        continue
    data = r.get("data") or {}
    text = re.sub(r"<[^>]+>", "", data.get("text") or "")
    pics = [p.get("large", {}).get("url") or p.get("url") for p in (data.get("pics") or [])]
    pi = data.get("page_info") or {}
    vurl = ""
    if pi.get("type") == "video" and pi.get("media_info"):
        mi = pi["media_info"]
        vurl = mi.get("stream_url") or mi.get("mp4_720p_mp4") or mi.get("mp4_hd_url") or mi.get("mp4_sd_url") or ""
    with open(os.path.join(TXT, s + ".txt"), "w", encoding="utf-8") as f:
        f.write("名称：%s\n时间：%s\n链接：%s\n\n%s\n" % (e["title"], e["date"], e["link"], text))
    rec = {"slug": s, "title": e["title"], "date": e["date"], "link": e["link"],
           "text_path": s + ".txt", "text_len": len(text),
           "pics": pics, "video": vurl, "transcript": "", "ocr": "", "status": "原文已存"}
    if vurl:
        rec["status"] = "待转写"
    elif pics:
        rec["status"] = "待OCR"
    queue.append(rec)
    print("  %-40s 文字%4d 图%2d 视频%s" % (s[:40], len(text), len(pics), "有" if vurl else "无"))
    time.sleep(0.6)

# 下载媒体
if "--media" in sys.argv:
    ok_v = ok_i = 0
    for rec in queue:
        if rec["video"]:
            p = os.path.join(VID, rec["slug"] + ".mp4")
            if not (os.path.exists(p) and os.path.getsize(p) > 100000):
                try:
                    d = urllib.request.urlopen(urllib.request.Request(rec["video"], headers=H), timeout=180).read()
                    if len(d) > 100000:
                        open(p, "wb").write(d); ok_v += 1
                except Exception as ex:
                    print("  视频失败", rec["slug"][:24], type(ex).__name__)
            rec["video_path"] = rec["slug"] + ".mp4" if os.path.exists(p) else ""
        if rec["pics"]:
            d0 = os.path.join(IMG, rec["slug"])
            os.makedirs(d0, exist_ok=True)
            paths = []
            for i, u in enumerate(rec["pics"], start=1):
                pp = os.path.join(d0, "img%02d.jpg" % i)
                if not (os.path.exists(pp) and os.path.getsize(pp) > 5000):
                    try:
                        d = get(u, timeout=60)
                        if len(d) > 5000:
                            open(pp, "wb").write(d); ok_i += 1
                    except Exception:
                        pass
                if os.path.exists(pp):
                    paths.append(pp)
            rec["image_dir"] = d0 if paths else ""
    print("媒体下载：视频 %d 个、图片 %d 张" % (ok_v, ok_i))

json.dump({"generated": date.today().isoformat(), "count": len(queue), "items": queue},
          open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print("队列", len(queue), dict(Counter(r["status"] for r in queue)))
