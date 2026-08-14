#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成城市攻略数据 data/city_guides.json —— 22 城演出历史 / 常唱歌曲 / 酒馆声音 / 网络贴士。

单一数据源原则：
- 演出历史   <- data/cities.json（22 城 59 场，含场馆/日期/巡次）
- 常唱歌曲   <- entity_index.json 反查（该城市演出过的歌曲，按场次降序取前 5）
- 酒馆声音   <- entity_index.json 反查（该城唱过的歌 → 有 tavern 关系的 EP，取主题）
- 网络贴士   <- web_search 结果（标题/摘要/来源链接，只放摘要不复制正文），可离线重跑

用法：
  python project_b/generate_city_guides.py            # 生成（web_tips 用缓存/空）
  python project_b/generate_city_guides.py --tips     # 生成并联网补充 web_tips（需网络）
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CITIES = ROOT / "data" / "cities.json"
ENTITY = ROOT / "entity_index.json"
TRANSCRIPTS = ROOT / "tavern" / "tavern_transcripts.json"
OUT = ROOT / "data" / "city_guides.json"


def norm(s: str) -> str:
    return re.sub(r"\s+", "", str(s or ""))


def load_cities() -> dict:
    return json.loads(CITIES.read_text(encoding="utf-8"))["cities"]


def load_entity() -> dict:
    return json.loads(ENTITY.read_text(encoding="utf-8"))["songs"]


def load_ep_themes() -> dict:
    """EP key -> theme（酒馆声音的文案来源）"""
    d = json.loads(TRANSCRIPTS.read_text(encoding="utf-8"))
    return {k: v.get("theme", "") for k, v in d.get("episodes", {}).items()}


def build_guides() -> dict:
    cities = load_cities()
    songs = load_entity()
    ep_themes = load_ep_themes()
    guides = {}

    for city, node in cities.items():
        shows = node.get("shows", [])
        # 演出历史
        performances = [
            {
                "date": s["date"],
                "scene": s.get("scene", city),
                "venue": s.get("venue"),
                "tour": s.get("tour", ""),
                "theme": s.get("theme", ""),
                "live_url": s.get("live_url"),
                "cancelled": s.get("cancelled", False),
                "has_data": s.get("has_data", False),
            }
            for s in shows
        ]
        # 常唱歌曲：entity_index 反查该城演出过的歌，按场次降序
        song_count = {}
        for name, en in songs.items():
            n = sum(1 for lv in en.get("live", []) if lv.get("city") == city)
            if n:
                song_count[name] = n
        top_songs = [
            {"name": name, "count": n}
            for name, n in sorted(song_count.items(), key=lambda kv: -kv[1])[:5]
        ]
        # 酒馆声音：该城唱过的歌 → tavern 关系（非歌词）→ EP 主题
        tavern_quotes = []
        seen_eps = set()
        for name, en in songs.items():
            played_here = any(lv.get("city") == city for lv in en.get("live", []))
            if not played_here:
                continue
            for ep in en.get("tavern", []):
                if ep == "歌词" or ep in seen_eps:
                    continue
                seen_eps.add(ep)
                theme = ep_themes.get(ep, "")
                tavern_quotes.append({"ep": ep, "theme": theme, "song": name})
                if len(tavern_quotes) >= 2:
                    break
            if len(tavern_quotes) >= 2:
                break
        guides[city] = {
            "performances": performances,
            "top_songs": top_songs,
            "tavern_quotes": tavern_quotes,
            "web_tips": [],
        }
    return guides


def main() -> None:
    parser = argparse.ArgumentParser(description="生成城市攻略数据")
    parser.add_argument("--tips", action="store_true", help="联网补充 web_tips（需要网络）")
    parser.add_argument("--output", default=str(OUT))
    args = parser.parse_args()

    guides = build_guides()
    # 保留已有 web_tips（搜索成果不因重新生成丢失）
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
            for city, g in guides.items():
                old_tips = old.get(city, {}).get("web_tips", [])
                if old_tips:
                    g["web_tips"] = old_tips
        except Exception:
            pass
    if args.tips:
        try:
            from city_tips_fetcher import fetch_tips_for_city  # noqa: F401
            print("[!] --tips 需要在脚本内集成 web_search，当前版本生成不含 tips 的版本")
        except ImportError:
            print("[!] 提示：web_tips 由维护流程补充（web_search 逐城查询后写入）")
    out = Path(args.output)
    out.write_text(json.dumps(guides, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 已生成 {len(guides)} 城攻略 -> {out}")
    for city, g in guides.items():
        print(f"  {city}: {len(g['performances'])}场演出 / {len(g['top_songs'])}首常唱 / {len(g['tavern_quotes'])}条酒馆 / {len(g['web_tips'])}条贴士")


if __name__ == "__main__":
    main()
