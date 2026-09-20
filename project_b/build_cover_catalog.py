# -*- coding: utf-8 -*-
"""曲目谱系（翻唱档案）：把他唱过的每一首变成可分析的结构化资产。

为什么做这个：QQ 指数只覆盖他的发行曲（~72 首自有），而现场翻唱（~221 首）没有任何市场数据。
但恰恰因为"没有发行、没有推广、没有算法"，这些曲目是他**主动选择**的纯样本——市场数据永远回答不了
"他选择成为谁"，翻唱库是唯一证据源。本脚本把选曲行为变成可量化对象。

数据源：setlists.json（64 场歌单）＋ albums.json（自有发行）＋ archive_stage_tour.json（现场实测）
        ＋ songs_meta.json（指数覆盖）＋ timeline.json（巡次时间）
产出：data/cover_catalog.json ＋ temp/曲目谱系.md
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load(name, default=None):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def norm(t: str) -> str:
    t = str(t or "").strip().lower()
    t = re.sub(r"[（(].*?[)）]", "", t)
    return re.sub(r"[\s·・,，、'’\"“”!！?？.。\-—_]+", "", t)


def main() -> int:
    sl = load("setlists.json").get("setlists", {})
    own = {norm(s.get("title")): a.get("name") for a in load("albums.json").get("albums", [])
           for s in a.get("songs", []) if s.get("title")}
    idx_songs = {norm(x.get("name")) for x in load("songs_meta.json").get("songs", {}).values()
                 if isinstance(x, dict) and x.get("name")}
    # 「有实际指数记录」以指数长表为准（songs_meta 只代表 QQ 有条目，不等于有数据）
    try:
        import pandas as pd
        long_csv = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
        _d = pd.read_csv(long_csv, encoding="utf-8-sig")
        _scol = [c for c in _d.columns if "song" in c.lower() or "name" in c.lower()][0]
        index_real = {norm(x) for x in _d[_scol].dropna().astype(str)}
    except Exception:
        index_real = set()
    live = load("archive_stage_tour.json").get("by_song", [])

    catalog = defaultdict(lambda: {"times": 0, "shows": [], "tours": set()})
    for date, v in sorted(sl.items()):
        tour, city = v.get("tour", ""), v.get("city", "")
        for s in v.get("songs", []):
            t = (s.get("title") or "").strip()
            if not t:
                continue
            c = catalog[t]
            c["times"] += 1
            c["shows"].append(date)
            c["tours"].add(tour)
            c.setdefault("cities", set()).add(city)

    rows = []
    for t, c in catalog.items():
        n = norm(t)
        rows.append({
            "title": t,
            "times": c["times"],
            "first": min(c["shows"]), "last": max(c["shows"]),
            "tours": sorted(x for x in c["tours"] if x),
            "cities": len(c.get("cities", ())),
            "own": n in own, "own_album": own.get(n, ""),
            "indexed": n in idx_songs, "has_index_data": n in index_real,
            "kind": "串烧" if ("+" in t or "＋" in t) else ("点歌/即兴" if "点歌" in t else "单曲"),
        })
    rows.sort(key=lambda r: (-r["times"], r["title"]))

    own_rows = [r for r in rows if r["own"]]
    cover_rows = [r for r in rows if not r["own"]]
    tiers = {
        "看家曲（≥10 场）": [r for r in rows if r["times"] >= 10],
        "常演（5–9 场）": [r for r in rows if 5 <= r["times"] < 10],
        "偶演（2–4 场）": [r for r in rows if 2 <= r["times"] < 5],
        "一次性（1 场）": [r for r in rows if r["times"] == 1],
    }
    span_years = sorted({r["first"][:4] for r in rows})

    stat = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "songs_total": len(rows),
        "own_released": len(own_rows),
        "covers": len(cover_rows),
        "covers_with_index": sum(1 for r in cover_rows if r["indexed"]),
        "covers_with_index_data": sum(1 for r in cover_rows if r["has_index_data"]),
        "own_with_index_data": sum(1 for r in own_rows if r["has_index_data"]),
        "no_index_data": sum(1 for r in rows if not r["has_index_data"]),
        "shows": len(sl),
        "years": f"{span_years[0]}–{span_years[-1]}",
        "tiers": {k: len(v) for k, v in tiers.items()},
        "medley": sum(1 for r in rows if r["kind"] == "串烧"),
        "request": sum(1 for r in rows if r["kind"] == "点歌/即兴"),
        "covers_zero_repeat": sum(1 for r in cover_rows if r["times"] == 1),
    }

    lines = [f"# 曲目谱系 · 翻唱档案（自动生成 {datetime.now():%Y-%m-%d %H:%M}）", "",
             f"- 64 场共唱过 **{stat['songs_total']}** 首不同曲目｜自有发行 **{stat['own_released']}** 首｜"
             f"翻唱/非自有 **{stat['covers']}** 首（QQ 有条目 {stat['covers_with_index']} 首，"
             f"但**真正有指数数据的只有 {stat['covers_with_index_data']} 首**）",
             f"- 时间跨度 {stat['years']}｜串烧 {stat['medley']} 首｜点歌/即兴 {stat['request']} 首",
             f"- 分档：" + "｜".join(f"{k} {v} 首" for k, v in stat["tiers"].items()), "",
             "## 看家曲（演唱 ≥10 场）—— 他的自我定义", "",
             "| 曲目 | 场次 | 首唱 | 末唱 | 巡次 | 城市 | 自有 | 在指数池 |", "|---|---|---|---|---|---|---|---|"]
    for r in tiers["看家曲（≥10 场）"]:
        lines.append(f"| {r['title']} | {r['times']} | {r['first']} | {r['last']} | {len(r['tours'])} | "
                     f"{r['cities']} | {'✅' if r['own'] else '—'} | {'✅' if r['indexed'] else '—'} |")
    lines += ["", "## 一次性曲目（只唱过 1 场）—— 实验区", "",
              f"共 {len(tiers['一次性（1 场）'])} 首。只唱过一次＝没有第二次的选择，是审美边界最干净的读数。", "",
              "　" + "、".join(r["title"] for r in tiers["一次性（1 场）"][:60]), "",
              "## 点歌 / 即兴", ""]
    lines += [f"- {r['title']}（{r['last']}）" for r in rows if r["kind"] == "点歌/即兴"]
    lines += ["", "## 全量（按场次降序，前 80）", "",
              "| 曲目 | 场次 | 首唱 | 自有 | 指数池 | 类型 |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['title']} | {r['times']} | {r['first']} | {'✅' if r['own'] else '—'} | "
              f"{'✅' if r['indexed'] else '—'} | {r['kind']} |" for r in rows[:80]]

    (DATA / "cover_catalog.json").write_text(
        json.dumps({"stat": stat, "songs": [{**r, "tours": r["tours"]} for r in rows]},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "temp" / "曲目谱系.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    print("→ data/cover_catalog.json\n→ temp/曲目谱系.md")
    assert stat["songs_total"] > 200 and stat["covers"] > 100
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
