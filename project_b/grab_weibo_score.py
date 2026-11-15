# -*- coding: utf-8 -*-
"""走本地微博通道（weibo_proxy 自带签名/headers + wb.txt cookie），抓某条微博的图片到本地。"""
import sys, json
from pathlib import Path

sys.path.insert(0, r"E:\wx\私有工具\weibo_proxy")
import weibo_proxy as wp

MID = "5079953865179303"
OUT = Path(r"E:\wx\论文素材_王晰作传\曲谱_网友扒谱") / MID
OUT.mkdir(parents=True, exist_ok=True)

ck = wp.load_cookie()
print("cookie 长度:", len(ck))
m = wp._fetch_detail(MID)
if not m:
    print("取详情失败")
    raise SystemExit(2)

print("作者:", (m.get("user") or {}).get("screen_name"))
text = wp._extract_text(m)
print("正文前 200 字:", text[:200].replace("\n", " "))
pics = wp._extract_pics(m)
print("图片数:", len(pics))
saved = 0
for i, u in enumerate(pics, 1):
    dest = OUT / ("%02d.jpg" % i)
    try:
        wp._download(u, dest)
        saved += 1
    except Exception as e:
        print("  下载失败", i, str(e)[:60])
print("已下载:", saved, "→", OUT)

(OUT / "meta.json").write_text(json.dumps({
    "mid": MID,
    "url": "https://weibo.com/7087121910/%s" % MID,
    "author": (m.get("user") or {}).get("screen_name"),
    "text": text,
    "n_pics": len(pics),
    "note": "网友扒谱合集；已获作者授权；仅本地留存，不上网",
}, ensure_ascii=False, indent=1), encoding="utf-8")
