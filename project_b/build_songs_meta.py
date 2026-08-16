#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成歌曲元数据增强 data/songs_meta.json —— 歌词片段 / 专辑 / 发行 / 类型 / 试听链接。

数据源（全部合法元数据，不包含音频文件）：
- dashboard/dashboard_data.json  detail_songs: name/attr/release/latest/mean30/peak
- tavern/lyrics_fragments.json  歌曲名 -> {fragments:[{text,moods,source}]}
- entity_index.json             discography（专辑关联）
- 巡演歌单长表（经 setlists.json） 每首歌演唱场次数

用法：python project_b/build_songs_meta.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "dashboard" / "dashboard_data.json"
LYRICS = ROOT / "tavern" / "lyrics_fragments.json"
ENTITY = ROOT / "entity_index.json"
SETLISTS = ROOT / "data" / "setlists.json"
OUT = ROOT / "data" / "songs_meta.json"


def norm(s: str) -> str:
    import unicodedata
    import re
    s = str(s or "").replace("《", "").replace("》", "")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", "", s)


def main() -> None:
    dash = json.loads(DASH.read_text(encoding="utf-8"))
    lyrics = json.loads(LYRICS.read_text(encoding="utf-8"))
    entity = json.loads(ENTITY.read_text(encoding="utf-8"))["songs"]
    setlists = json.loads(SETLISTS.read_text(encoding="utf-8"))["setlists"]

    # 1. 主源：entity_index（433 首全量，含 dashboard 指标）
    meta = {}
    # uid 映射：dashboard detail_songs 的 uid（L:mid 格式）→ 歌曲名
    mid_by_name = {}
    for s in dash.get("detail_songs", []) or []:
        if s.get("name") and s.get("uid"):
            mid_by_name[norm(s["name"])] = s["uid"]
    for name, en in entity.items():
        dash_info = en.get("dashboard") or {}
        meta[norm(name)] = {
            "name": name,
            "attr": dash_info.get("attr"),
            "release": dash_info.get("release") or "-",
            "latest": dash_info.get("latest"),
            "mean30": dash_info.get("mean30"),
            "peak": dash_info.get("peak"),
            "lyrics": [],
            "album": (en.get("discography") or {}).get("album"),
            "show_count": len(en.get("live", [])),
            "cities": sorted({lv.get("city") for lv in en.get("live", []) if lv.get("city")}),
            "mid": mid_by_name.get(norm(name)),   # 试听用 songmid（可能为 null）
        }
        # live 场次精确化：用 entity 的 live 列表（含场馆）
        meta[norm(name)]["live"] = [
            {"date": lv.get("date"), "city": lv.get("city"), "venue": lv.get("venue")}
            for lv in en.get("live", [])
        ]

    # 2. 歌词片段补充
    for name, node in lyrics.items():
        if name == "_meta":
            continue
        n = norm(name)
        if n not in meta:
            meta[n] = {"name": name, "attr": None, "release": "-", "latest": None,
                       "mean30": None, "peak": None, "lyrics": [], "album": None,
                       "show_count": 0, "cities": [], "live": [], "mid": None}
        for f in node.get("fragments", []):
            meta[n]["lyrics"].append({"text": f.get("text", ""), "moods": f.get("moods", [])})

    # 3. 输出：剔除无任何信息的空壳（仅歌词条目也可能有价值，保留全部）
    out = {k: v for k, v in meta.items() if v["name"]}
    out = dict(sorted(out.items(), key=lambda kv: kv[1]["name"]))

    import datetime
    result = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "song_count": len(out),
        "songs": out,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    with_lyrics = sum(1 for v in out.values() if v["lyrics"])
    with_album = sum(1 for v in out.values() if v["album"])
    with_shows = sum(1 for v in out.values() if v.get("live"))
    print(f"[OK] 已生成 -> {OUT}")
    print(f"  歌曲: {len(out)} | 有歌词: {with_lyrics} | 有专辑: {with_album} | 有演唱记录: {with_shows}")


if __name__ == "__main__":
    main()
