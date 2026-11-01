"""把平台全量歌曲与本地对账，分别处理：真歌补进曲库、播客补进音频池"""
import json
import re

QQ = json.load(open(r"D:\wx409.github.io\data\qq_singer_songs.json", encoding="utf-8"))
COMPACT = r"D:\wx409.github.io\tavern\songs_compact.json"
AUDIO = r"D:\wx409.github.io\data\tavern_audio.json"

POD_ALBUM = ("小酒馆", "城市漫行", "哄你入睡")


def norm(s):
    return re.sub(r"[\s《》()（）\-—·]", "", str(s or "")).lower()


songs = QQ["songs"]
miss = QQ["missing_in_local"]

pod = [s for s in miss if any(k in (s["album"] or "") for k in POD_ALBUM)]
real = [s for s in miss if s not in pod]
print("平台 %d 首｜本地缺 %d 首（播客 %d / 真歌 %d）" % (len(songs), len(miss), len(pod), len(real)))

# 1) 真歌补进曲库
comp = json.load(open(COMPACT, encoding="utf-8"))
items = comp["songs"] if isinstance(comp, dict) and "songs" in comp else comp
have = {norm(x.get("name")) for x in items}
added = 0
for s in real:
    if norm(s["name"]) in have or not s["mid"]:
        continue
    items.append({"uid": "L:" + s["mid"], "name": s["name"], "attr": None,
                  "release": None, "latest": None, "mean30": None, "peak": None})
    have.add(norm(s["name"]))
    added += 1
if isinstance(comp, dict):
    comp["count"] = len(items)
json.dump(comp, open(COMPACT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("曲库补入真歌 %d 首（现 %d）" % (added, len(items)))

# 2) 播客补进音频池
a = json.load(open(AUDIO, encoding="utf-8"))
aitems = a["items"]
amids = {str(x.get("mid")) for x in aitems}
padd = 0
for s in pod:
    if not s["mid"] or s["mid"] in amids:
        continue
    cat = "城市漫行" if "城市漫行" in (s["album"] or "") else "小酒馆"
    aitems.append({"name": s["name"], "mid": s["mid"], "album": s["album"],
                   "duration_sec": None, "episode": (s["name"] or "")[:10],
                   "category": cat, "theme": ""})
    amids.add(s["mid"])
    padd += 1
a["count"] = len(aitems)
json.dump(a, open(AUDIO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("音频池补入播客 %d 期（现 %d）" % (padd, len(aitems)))

print("\n真歌缺口中前 8 首：")
for s in real[:8]:
    print("   ", (s["name"] or "")[:34], "|", (s["album"] or "")[:20])
