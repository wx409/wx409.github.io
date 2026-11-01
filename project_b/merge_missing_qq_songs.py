"""把平台枚举出、本地缺的歌曲并入曲库（uid=L:mid），再由同步器写进收听人数表"""
import json
import re

QQ = json.load(open(r"D:\wx409.github.io\data\qq_singer_songs.json", encoding="utf-8"))
COMPACT = r"D:\wx409.github.io\tavern\songs_compact.json"

try:
    _ex = json.load(open(r"D:\wx409.github.io\data\excluded_songs.json", encoding="utf-8"))
    EXCLUDED = {x["mid"] for x in (_ex.get("items") or [])}
except Exception:
    EXCLUDED = set()

songs = QQ["songs"]
missing = QQ["missing_in_local"]
print("平台去重 %d 首｜本地缺 %d 首" % (len(songs), len(missing)))

comp = json.load(open(COMPACT, encoding="utf-8"))
items = comp["songs"] if isinstance(comp, dict) and "songs" in comp else comp
have = {str(x.get("uid"))[2:] for x in items if str(x.get("uid", "")).startswith("L:")}

added = 0
for s in missing:
    mid = s.get("mid")
    if not mid or mid in have or mid in EXCLUDED:
        continue
    items.append({"uid": "L:" + mid, "name": s.get("name"), "attr": None,
                  "release": None, "latest": None, "mean30": None, "peak": None})
    have.add(mid)
    added += 1

comp["count"] = len(items)
json.dump(comp, open(COMPACT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("曲库补入 %d 首 → 现共 %d 首" % (added, len(items)))
