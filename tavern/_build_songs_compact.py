# -*- coding: utf-8 -*-
"""生成 tavern 页面的轻量歌曲表 songs_compact.json（从 dashboard_data.json 提取，保持与数据源同步）。"""
import json, os

base = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(base, "..", "dashboard", "dashboard_data.json")
dst = os.path.join(base, "songs_compact.json")

with open(src, "r", encoding="utf-8") as f:
    data = json.load(f)

songs = []
for s in data.get("song_index", []):
    try:
        songs.append({
            "uid": s.get("uid", ""),
            "name": s.get("name", ""),
            "attr": s.get("attr", ""),
            "release": s.get("release", ""),
            "latest": s.get("latest", None),
            "mean30": s.get("mean30", None),
            "peak": s.get("peak", None),
        })
    except Exception:
        pass

out = {
    "generated_from": "dashboard_data.json",
    "generated_at": data.get("timestamp", ""),
    "count": len(songs),
    "songs": songs,
}
with open(dst, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

print("songs_compact.json ->", len(songs), "songs")
