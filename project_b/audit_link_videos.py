"""审计：所有微博链接里，哪些有视频、哪些已转写、质量如何"""
import glob, json, os, re, time, urllib.request

BASE = r"E:\wx\私有\王晰全文库\采访目录"
TXT = os.path.join(BASE, "全文")
CK = open(r"E:\wx\index_records\wb.txt", encoding="utf-8", errors="ignore").read().strip()
H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
     "Referer": "https://m.weibo.cn/", "Cookie": CK, "X-Requested-With": "XMLHttpRequest"}

links = {}
for fn in ("采访杂志根表.json", "自动候选.json", "处理队列.json"):
    p = os.path.join(BASE, fn)
    if not os.path.exists(p):
        continue
    d = json.load(open(p, encoding="utf-8"))
    items = d.get("items") or []
    for it in items:
        lk = it.get("链接") or it.get("link") or ""
        m = re.search(r"detail/(\d+)", lk) or re.search(r"weibo\.com/\d+/(\d+)", lk)
        if m:
            links.setdefault(m.group(1), {"title": (it.get("名称") or it.get("title") or "")[:36],
                                          "file": it.get("全文路径") or it.get("transcript") or "",
                                          "src": fn})

print("待审链接", len(links))
rows = []
for mid, meta in links.items():
    vurl = ""
    try:
        r = json.loads(urllib.request.urlopen(
            urllib.request.Request("https://m.weibo.cn/statuses/show?id=%s" % mid, headers=H), timeout=25
        ).read().decode("utf-8", "ignore"))
        pi = (r.get("data") or {}).get("page_info") or {}
        if pi.get("media_info"):
            vurl = pi["media_info"].get("stream_url") or pi["media_info"].get("mp4_hd_url") or "有"
    except Exception:
        pass
    trans = [f for f in glob.glob(os.path.join(TXT, "*_转写*.txt")) if mid in open(f, encoding="utf-8", errors="ignore").read(400)]
    rows.append({"mid": mid, "title": meta["title"], "video": bool(vurl),
                 "transcript": os.path.basename(trans[0]) if trans else "",
                 "chars": len(open(trans[0], encoding="utf-8", errors="ignore").read()) if trans else 0})
    time.sleep(0.5)

vids = [r for r in rows if r["video"]]
print("有视频的链接", len(vids), "｜已转写", sum(1 for r in vids if r["transcript"]))
for r in vids:
    print("  %s | %-34s | %s" % (r["mid"], r["title"], ("已转写 %d 字" % r["chars"]) if r["transcript"] else "**未转写**"))
json.dump(rows, open(os.path.join(BASE, "视频审计.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
