"""批量拉取 QQ 音乐歌词 → data/lyrics_raw/<歌名>.txt

数据源：data/songs_meta.json 的 songs[].mid（形如 "L:000eHsPh3BiKVr"，需去前缀）
Cookie：E:\\wx\\index_records\\qqmusic.txt（与电台代理同一份）
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

META = r"D:\wx409.github.io\data\songs_meta.json"
OUT = r"D:\wx409.github.io\data\lyrics_raw"
CK = r"E:\wx\index_records\qqmusic.txt"
os.makedirs(OUT, exist_ok=True)

ck = open(CK, encoding="utf-8", errors="ignore").read().strip()
if ck.lower().startswith("cookie:"):
    ck = ck.split(":", 1)[1].strip()
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
     "Referer": "https://y.qq.com/", "Cookie": ck}

_raw = json.load(open(META, encoding="utf-8"))["songs"]
songs = list(_raw.values()) if isinstance(_raw, dict) else _raw
print("曲目", len(songs))


def safe(n):
    return re.sub(r"[\\/:*?\"<>|\s]+", "_", (n or "unknown"))[:60]


def fetch(mid, tries=2):
    u = ("https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?songmid=%s"
         "&format=json&nobase64=1&g_tk=5381" % mid)
    for _ in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=20).read()
            txt = raw.decode("utf-8", "ignore")
            j = json.loads(txt) if txt.strip().startswith("{") else json.loads(txt[txt.find("{"):])
            return j.get("lyric") or ""
        except Exception:
            time.sleep(1.2)
    return ""


def strip_lrc(lyric):
    lines = []
    for l in lyric.splitlines():
        l = re.sub(r"^\[[^\]]*\]", "", l).strip()
        if not l or l in ("//",):
            continue
        lines.append(l)
    return "\n".join(lines)


ok = skip = fail = 0
t0 = time.time()
for i, s in enumerate(songs, 1):
    mid = (s.get("mid") or "").split(":")[-1]
    name = s.get("name") or ""
    if not mid:
        fail += 1
        continue
    path = os.path.join(OUT, safe(name) + ".txt")
    if os.path.exists(path) and os.path.getsize(path) > 80:
        skip += 1
        continue
    lyric = strip_lrc(fetch(mid))
    if len(lyric) < 20:
        fail += 1
        continue
    with open(path, "w", encoding="utf-8") as f:
        f.write("歌名：%s\n专辑：%s\nmid：%s\n\n%s\n" % (name, s.get("album") or "", mid, lyric))
    ok += 1
    if i % 50 == 0:
        print("  %d/%d｜成功 %d 跳过 %d 失败 %d｜%.0fs"
              % (i, len(songs), ok, skip, fail, time.time() - t0), flush=True)
    time.sleep(0.35)

print("完成：成功 %d｜跳过已存在 %d｜无歌词 %d｜总 %.0fs" % (ok, skip, fail, time.time() - t0))
