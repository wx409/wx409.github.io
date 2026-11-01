"""把 89 条播客 mid 与现有小酒馆音频池比对，补进 tavern_audio.json"""
import json

POD = json.load(open(r"D:\wx409.github.io\data\podcast_mids.json", encoding="utf-8"))
AUDIO = r"D:\wx409.github.io\data\tavern_audio.json"

d = json.load(open(AUDIO, encoding="utf-8"))
items = d["items"]
have = {str(x.get("mid")) for x in items}
print("现有小酒馆音频 %d 条" % len(items))

new = [p for p in POD if p["mid"] not in have]
print("未收录的播客 %d 条" % len(new))

# 只在「日木斤深夜小酒馆」专辑里补（城市漫行等先不动）
tavern_new = [p for p in new if "小酒馆" in p["album"]]
print("其中小酒馆专辑 %d 条" % len(tavern_new))

for p in tavern_new:
    items.append({
        "name": p["name"],
        "mid": p["mid"],
        "album": p["album"],
        "duration_sec": None,
        "episode": (p["name"] or "")[:8],
        "category": "小酒馆",
        "theme": "",
    })

d["count"] = len(items)
json.dump(d, open(AUDIO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("tavern_audio 现 %d 条" % len(items))
