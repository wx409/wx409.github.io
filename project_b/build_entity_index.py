#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成跨站关系索引 entity_index.json —— 歌曲 ↔ 城市 ↔ 场馆 ↔ 逐字稿(EP) 的聚合图谱。

单一数据源原则：
- 歌曲基础数据   <- dashboard/dashboard_data.json（唯一数据出口：latest/mean30/peak/lifecycle/attr/release）
- 歌曲↔场次关系  <- 巡演歌单长表（单一事实源：日期/场次/城市/曲目/数据层归一名）
- 场次↔场馆关系  <- data/cities.json（由 generate_cities_json.py 从长表+live页生成）
- 歌曲↔逐字稿    <- tavern/tavern_transcripts.json（songmid 关联）+ lyrics_fragments.json（歌词片段）
- 歌曲↔专辑      <- dashboard_data.json 的 release_events / discography 侧

输出：
- entity_index.json（根目录，小酒馆搜索 findEntities 直接消费）

用法：
  python project_b/build_entity_index.py
  python project_b/build_entity_index.py --setlist <长表.xlsx>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "dashboard" / "dashboard_data.json"
CITIES = ROOT / "data" / "cities.json"
TRANSCRIPTS = ROOT / "tavern" / "tavern_transcripts.json"
LYRICS = ROOT / "tavern" / "lyrics_fragments.json"
OUT = ROOT / "entity_index.json"
DEFAULT_SETLIST = r"E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx"

# 组合曲目拆分：数据层归一名含 '+' 的视为组合（女人花+水中花），拆分后分别关联
COMBO_SPLIT = "+"


def norm(name: str) -> str:
    """归一化歌曲名：全半角 NFKC + 去空白 + 去书名号"""
    if name is None:
        return ""
    s = str(name).strip()
    s = s.replace("《", "").replace("》", "")
    try:
        import unicodedata
        s = unicodedata.normalize("NFKC", s)
    except Exception:
        pass
    return re.sub(r"\s+", "", s)


def load_dashboard() -> dict:
    """读取大屏数据：歌曲元信息 + 发行事件"""
    d = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    info = {}
    # detail_songs 为歌曲信息主源（name/attr/release/latest/mean30/peak）
    for s in d.get("detail_songs", []) or []:
        name = s.get("name")
        if not name:
            continue
        info[norm(name)] = {
            "latest": s.get("latest", 0),
            "mean30": s.get("mean30", 0),
            "peak": s.get("peak", 0),
            "lifecycle": s.get("lifecycle"),
            "attr": s.get("attr"),
            "release": s.get("release") or "-",
        }
    # top_songs 补充（含 trend 的活跃歌曲，无则跳过——已有 detail 则保留 detail）
    for s in d.get("top_songs", []) or []:
        name = s.get("name")
        if not name or norm(name) in info:
            continue
        info[norm(name)] = {
            "latest": s.get("trend", 0),
            "mean30": 0,
            "peak": 0,
            "lifecycle": None,
            "attr": s.get("tag"),
            "release": "-",
        }
    # release_events：[月份, "YYYY-MM-DD 《歌名》发行（类型）"] 二元组 → 歌曲↔专辑/发行关系
    releases = {}
    for ev in d.get("release_events", []) or []:
        if not isinstance(ev, (list, tuple)) or len(ev) < 2:
            continue
        desc = str(ev[1])
        m = re.search(r"《([^》]+)》", desc)
        if m:
            releases[norm(m.group(1))] = ev[0]
    return {"songs": info, "releases": releases}


def load_setlist_songs(path: str) -> list[dict]:
    """读取长表 → 歌曲×场次明细（歌曲↔城市↔日期 关系核心）"""
    df = pd.read_excel(path, sheet_name="合并长表")
    df = df[df["曲目"].notna() & (df["曲目"].astype(str).str.strip() != "")]
    rows = []
    for _, r in df.iterrows():
        name_raw = r.get("数据层归一名") or r.get("曲目")
        if not name_raw or not str(name_raw).strip():
            continue
        date = str(r["日期"])[:10]
        scene = str(r["场次"]).strip()
        city = re.split(r"[（(]", scene)[0].strip()
        lun = str(r["巡次"]).strip()
        m = re.match(r"^(一巡|二巡|三巡|四巡|五巡|六巡)", lun)
        rows.append(
            {
                "name_raw": str(name_raw).strip(),
                "date": date,
                "scene": scene,
                "city": city,
                "lun": m.group(1) if m else lun[:2],
            }
        )
    return rows


def load_city_venues() -> dict:
    """读取 cities.json → {date: venue}（场次↔场馆）"""
    d = json.loads(CITIES.read_text(encoding="utf-8"))
    venues = {}
    for node in d.get("cities", {}).values():
        for s in node.get("shows", []):
            if s.get("venue"):
                venues[s["date"]] = s["venue"]
    return venues


def load_tavern_links() -> dict:
    """读取逐字稿 → 歌曲↔EP 关系（songmid 关联 + 主题匹配）+ 歌词片段"""
    links = {}
    data = json.loads(TRANSCRIPTS.read_text(encoding="utf-8"))
    for key, ep in data.get("episodes", {}).items():
        songmid = ep.get("songmid")
        theme = (ep.get("theme") or "").strip()
        # songmid 存在 → 本期主题即歌曲名（精确）
        if songmid and theme:
            links.setdefault(norm(theme), []).append(key)
    return {"ep_links": links, "lyric_songs": _load_lyric_songs(), "raw_themes": [
        (key, ep.get("theme", "")) for key, ep in data.get("episodes", {}).items()
    ]}


def _load_lyric_songs() -> set:
    """歌词片段歌曲名集合"""
    lyric_songs = set()
    if LYRICS.exists():
        try:
            ldata = json.loads(LYRICS.read_text(encoding="utf-8"))
            if isinstance(ldata, dict):
                for name in ldata:
                    if name and name != "_meta":
                        lyric_songs.add(norm(name))
            elif isinstance(ldata, list):
                for item in ldata:
                    name = item.get("song") or item.get("title") or item.get("name")
                    if name:
                        lyric_songs.add(norm(name))
        except Exception:
            pass
    return lyric_songs


def build_index(setlist_path: str) -> dict:
    dash = load_dashboard()
    song_info = dash["songs"]
    releases = dash["releases"]
    venues = load_city_venues()
    tavern = load_tavern_links()

    # 聚合歌曲×场次
    song_rows = load_setlist_songs(setlist_path)
    per_song: dict[str, dict] = {}
    for r in song_rows:
        for piece in r["name_raw"].split(COMBO_SPLIT):
            n = norm(piece)
            if not n:
                continue
            node = per_song.setdefault(n, {"live": [], "cities": set(), "tours": set()})
            node["live"].append(
                {
                    "date": r["date"],
                    "city": r["city"],
                    "scene": r["scene"],
                    "venue": venues.get(r["date"]),
                    "tour": r["lun"],
                }
            )
            node["cities"].add(r["city"])
            node["tours"].add(r["lun"])

    songs_out = {}
    all_names = set(song_info) | set(per_song) | set(tavern["ep_links"]) | tavern["lyric_songs"]
    for name in sorted(all_names):
        n = norm(name)
        entry: dict = {}
        info = song_info.get(n)
        if info:
            entry["dashboard"] = info
        lv = per_song.get(n)
        if lv:
            # 去重场次（同场组合曲目只留一次），按日期排序
            seen = set()
            live_rows = []
            for x in sorted(lv["live"], key=lambda k: k["date"]):
                k = (x["date"], x["scene"])
                if k in seen:
                    continue
                seen.add(k)
                live_rows.append(
                    {
                        "date": x["date"],
                        "city": x["city"],
                        "venue": x["venue"],
                        "tour": x["tour"],
                        "name": x["scene"],
                        "url": None,  # live 页 url 由 generate_live_page 维护，此处不写死
                    }
                )
            entry["live"] = live_rows
            if len(lv["cities"]) > 1:
                entry["cities"] = sorted(lv["cities"])
        tavern_eps = tavern["ep_links"].get(n)
        tavern_tags = []
        if tavern_eps:
            tavern_tags = sorted(set(tavern_eps))
        # 包含匹配：歌曲名出现在 EP 主题中（如「历久弥新，便是一生中最爱」含「一生中最爱」）
        if not tavern_tags and len(n) >= 3:
            for key, theme in tavern["raw_themes"]:
                if theme and n in norm(theme):
                    tavern_tags.append(key)
            tavern_tags = sorted(set(tavern_tags))
        if n in tavern["lyric_songs"] and "歌词" not in tavern_tags:
            tavern_tags.append("歌词")
        if tavern_tags:
            entry["tavern"] = tavern_tags
        # discography：release_events 匹配（专辑名=歌曲名）
        if n in releases:
            entry["discography"] = {"album": name, "release": releases[n]}
        elif info and info.get("attr") in ("专辑",) and info.get("release") and info["release"] != "-":
            entry["discography"] = {"album": name, "release": info["release"]}
        if entry:
            songs_out[name] = entry

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "song_count": len(songs_out),
        "songs": songs_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="生成跨站关系索引 entity_index.json")
    parser.add_argument("--setlist", default=DEFAULT_SETLIST, help="巡演歌单长表 xlsx 路径")
    parser.add_argument("--output", default=str(OUT))
    args = parser.parse_args()

    idx = build_index(args.setlist)
    out = Path(args.output)
    out.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")

    songs = idx["songs"]
    with_live = sum(1 for s in songs.values() if s.get("live"))
    with_tavern = sum(1 for s in songs.values() if s.get("tavern"))
    with_disco = sum(1 for s in songs.values() if s.get("discography"))
    live_links = sum(len(s["live"]) for s in songs.values() if s.get("live"))
    print(f"[OK] 已生成 {len(songs)} 首歌曲关系 -> {out}")
    print(f"  有现场关系: {with_live} 首（{live_links} 条场次链接）")
    print(f"  有小酒馆关系: {with_tavern} 首")
    print(f"  有专辑关系: {with_disco} 首")


if __name__ == "__main__":
    main()
