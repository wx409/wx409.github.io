"""探测曲库哪些 mid 能取到直链（VIP/版权受限的会返回空），产出 data/song_playable.json

之后前端只从可播列表里挑歌，避免「点了没声 / 提示要登录」。
"""
import json
import time
import urllib.parse
import urllib.request

POOL = r"D:\wx409.github.io\tavern\songs_compact.json"
OUT = r"D:\wx409.github.io\data\song_playable.json"

d = json.load(open(POOL, encoding="utf-8"))
items = d["songs"] if isinstance(d, dict) and "songs" in d else d
print("池内", len(items))


def mid_of(x):
    u = str(x.get("uid") or "")
    if u.startswith("L:"):
        return u[2:]
    if u.startswith("N:") or len(u) < 10:
        return ""
    return u


ok, fail, skip = [], [], 0
t0 = time.time()
for i, x in enumerate(items, 1):
    mid = mid_of(x)
    if not mid:
        skip += 1
        continue
    try:
        r = json.loads(urllib.request.urlopen(
            "http://127.0.0.1:8787/vkey?mid=" + urllib.parse.quote(mid), timeout=15).read().decode())
        u = (r.get("urls") or [""])[0]
    except Exception:
        u = ""
    if u:
        ok.append({"name": x.get("name"), "mid": mid})
    else:
        fail.append({"name": x.get("name"), "mid": mid})
    if i % 60 == 0:
        print("  %d/%d｜可播 %d｜不可 %d｜%.0fs" % (i, len(items), len(ok), len(fail), time.time() - t0), flush=True)
    time.sleep(0.12)

json.dump({"generated_at": time.strftime("%Y-%m-%d %H:%M"),
           "playable": ok, "unplayable": fail, "no_mid": skip},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("完成：可播 %d｜不可播 %d｜无 mid %d｜→ %s" % (len(ok), len(fail), skip, OUT))
