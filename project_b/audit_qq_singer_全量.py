"""用搜索分页枚举「王晰」名下歌曲（翻页有效），与本地曲库/音频池对账"""
import json
import re
import time
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
CK = open(r"E:\wx\index_records\qqmusic.txt", encoding="utf-8", errors="ignore").read().strip()
H = {"User-Agent": UA, "Referer": "https://y.qq.com/", "Cookie": CK, "Content-Type": "application/json"}
OUT = r"D:\wx409.github.io\data\qq_singer_songs.json"


def search(page, num=60):
    payload = {"comm": {"ct": 19, "cv": 1859, "uin": "0"},
               "req": {"module": "music.search.SearchCgiService",
                       "method": "DoSearchForQQMusicDesktop",
                       "param": {"num_per_page": num, "page_num": page,
                                 "query": "王晰", "search_type": 0}}}
    req = urllib.request.Request("https://u.y.qq.com/cgi-bin/musicu.fcg",
                                 data=json.dumps(payload).encode(), headers=H)
    r = json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore"))
    body = (((r.get("req") or {}).get("data") or {}).get("body") or {})
    return ((body.get("song") or {}).get("list") or [])


songs, seen = [], set()
for page in range(1, 13):
    lst = search(page)
    if not lst:
        break
    new = 0
    for s in lst:
        mid = s.get("mid")
        singers = "/".join(x.get("name", "") for x in (s.get("singer") or []))
        if not mid or mid in seen:
            continue
        if "王晰" not in singers:
            continue
        seen.add(mid)
        new += 1
        songs.append({"mid": mid, "name": s.get("name"),
                      "album": ((s.get("album") or {}).get("name") or ""),
                      "singers": singers})
    print("page %d：新增 %d（累计 %d）" % (page, new, len(songs)))
    if new == 0:
        break
    time.sleep(0.3)

print("\n平台「王晰」相关歌曲（去重）:", len(songs))

def norm(x):
    return re.sub(r"[\s《》()（）\-—·]", "", str(x or "")).lower()


comp = json.load(open(r"D:\wx409.github.io\tavern\songs_compact.json", encoding="utf-8"))
items = comp["songs"] if isinstance(comp, dict) and "songs" in comp else comp
local_mids = {str(x.get("uid"))[2:] for x in items if str(x.get("uid", "")).startswith("L:")}
audio = json.load(open(r"D:\wx409.github.io\data\tavern_audio.json", encoding="utf-8"))["items"]
audio_mids = {str(x.get("mid")) for x in audio}

missing = [s for s in songs if s["mid"] not in local_mids and s["mid"] not in audio_mids]
pod = [s for s in missing if any(k in (s["album"] or "") for k in ("小酒馆", "城市漫行", "哄你入睡"))]
real = [s for s in missing if s not in pod]

print("本地都没有：%d 首（播客 %d / 歌 %d）" % (len(missing), len(pod), len(real)))
for s in real[:15]:
    print("   ", (s["name"] or "")[:38], "|", (s["album"] or "")[:18], s["mid"])

json.dump({"query": "王晰", "count": len(songs), "songs": songs,
           "missing_in_local": missing},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n→", OUT)
