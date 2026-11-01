"""B 站字幕获取（支持 wbi 签名接口）"""
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request

BV = "BV1GJFYeuEpb"
CID = "28136506646"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"


def cookie():
    p = r"E:\wx\index_records\bilibili_cookies.txt"
    raw = open(p, encoding="utf-8", errors="ignore").read().strip()
    if raw.lower().startswith("cookie:"):
        raw = raw.split(":", 1)[1].strip()
    return raw


CK = cookie()
H = {"User-Agent": UA, "Referer": "https://www.bilibili.com/video/%s/" % BV, "Cookie": CK}


def get(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30)
                      .read().decode("utf-8", "ignore"))


# wbi 签名
nav = get("https://api.bilibili.com/x/web-interface/nav")
img = (nav.get("data") or {}).get("wbi_img") or {}
if not img:
    print("未登录或取不到 wbi_img：", nav.get("code"), nav.get("message"))
    raise SystemExit(2)
ik = img["img_url"].rsplit("/", 1)[-1].split(".")[0]
sk = img["sub_url"].rsplit("/", 1)[-1].split(".")[0]
MIXIN = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
         33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61,
         26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36,
         20, 34, 44, 52]
raw = ik + sk
mixin_key = "".join(raw[i] for i in MIXIN)[:32]

params = {"bvid": BV, "cid": CID, "wts": int(time.time())}
q = urllib.parse.urlencode(sorted(params.items()))
w_rid = hashlib.md5((q + mixin_key).encode()).hexdigest()
url = "https://api.bilibili.com/x/player/wbi/v2?%s&w_rid=%s" % (q, w_rid)
r = get(url)
print("code", r.get("code"), r.get("message"))
sub = ((r.get("data") or {}).get("subtitle") or {}).get("subtitles") or []
print("字幕轨", len(sub))
for s in sub:
    print("  ", s.get("lan"), s.get("lan_doc"), (s.get("subtitle_url") or "")[:100])
if sub:
    su = sub[0]["subtitle_url"]
    if su.startswith("//"):
        su = "https:" + su
    body = json.loads(urllib.request.urlopen(urllib.request.Request(su, headers={"User-Agent": UA}), timeout=30)
                      .read().decode("utf-8", "ignore"))
    items = body.get("body") or []
    print("字幕条数", len(items))
    out = r"E:\wx\私有\王晰全文库\采访目录\全文\bili_BV1GJFYeuEpb_字幕.json"
    json.dump(body, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("已存", out)
