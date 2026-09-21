# -*- coding: utf-8 -*-
"""场次认领：把现场层素材逐条归属到 64 场中的具体一场（多证据、可复算）。

四级证据（从严到宽）：
  L1 日期直配   素材自带 date 与某场日期一致（±0 天）且城市相符
  L2 BV 映射    素材 bv → 来源台账/_tour_parts_index 里的场次（BV 是唯一标识，最强机器证据）
  L3 歌单指纹   素材曲目 ∈ 该场歌单，且（城市或巡次相符），日期距该场 ≤7 天
  L4 巡次城市唯一 （巡次+城市）只对应一场，且素材日期在该场 ±60 天内
产出：data/show_assignment.json（逐素材 show_date/证据级）+ 控制台统计
用法：python -X utf8 project_b\\build_show_assignment.py
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
AUD = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")
TEMP = ROOT / "temp"
BV = re.compile(r"(BV[0-9A-Za-z]{10})")
DATE8 = re.compile(r"(20\d{2})[.\-_]?(\d{2})[.\-_]?(\d{2})")


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def dates_in(s: str) -> set:
    out = set()
    for y, m, d in DATE8.findall(str(s)):
        try:
            out.add(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    return out


def main() -> int:
    shows = jload(DATA / "setlists.json").get("setlists", {})
    shows = {k: v for k, v in shows.items() if v.get("city")}
    by_date = {d: v for d, v in shows.items()}
    by_tc = defaultdict(list)
    for d, v in shows.items():
        by_tc[(v.get("tour", ""), v.get("city", ""))].append(d)

    # ---- BV → 场次日期 ----
    bv2show = {}
    for it in jload(AUD / "来源台账.json").get("items", []):
        ds = [x.isoformat() for x in dates_in(it.get("tag", ""))]
        for ds_ in ds:
            if ds_ in by_date and it.get("bv"):
                bv2show[str(it["bv"])] = ds_
    for bv, v in (jload(TEMP / "_tour_parts_index.json") or {}).items():
        for d0 in dates_in(str(v.get("title", ""))) | dates_in(str(v.get("dir", ""))):
            if d0.isoformat() in by_date:
                bv2show[bv] = d0.isoformat()

    rows = jload(DATA / "archive_stage_tour.json").get("rows", [])
    out, stat = [], defaultdict(int)
    for r in rows:
        tag, song, city, tour = str(r.get("tag")), str(r.get("song")), str(r.get("city") or ""), str(r.get("tour") or "")
        d0 = None
        try:
            d0 = date.fromisoformat(str(r.get("date"))[:10])
        except Exception:
            pass
        assign, level, why = None, 0, ""
        # L1 日期直配
        if d0 and d0.isoformat() in by_date and (not city or by_date[d0.isoformat()].get("city") == city):
            assign, level, why = d0.isoformat(), 1, "日期直配"
        # L2 BV 映射
        if not assign:
            for bv in BV.findall(tag):
                if bv in bv2show:
                    assign, level, why = bv2show[bv], 2, f"BV映射 {bv}"
                    break
        # L3 歌单指纹
        if not assign and song:
            for ds_, v in shows.items():
                if song in [s.get("title") for s in v.get("songs", [])] and (city == v.get("city") or tour == v.get("tour")):
                    dd = date.fromisoformat(ds_)
                    if d0 and abs((dd - d0).days) <= 7:
                        assign, level, why = ds_, 3, f"歌单指纹（曲目在歌单且±7天）"
                        break
        # L4 巡次+城市唯一
        if not assign:
            cand = by_tc.get((tour, city)) or []
            if len(cand) == 1:
                dd = date.fromisoformat(cand[0])
                if (not d0) or abs((dd - d0).days) <= 60:
                    assign, level, why = cand[0], 4, "巡次城市唯一"
        # L5 同巡次同城市：取日期最近的一场（tag 日期常为视频发布日，故放宽到 ±120 天）
        if not assign and d0:
            cand = by_tc.get((tour, city)) or []
            if cand:
                near = min(cand, key=lambda ds_: abs((date.fromisoformat(ds_) - d0).days))
                if abs((date.fromisoformat(near) - d0).days) <= 120:
                    assign, level, why = near, 5, f"同巡同城最近日期（差 {abs((date.fromisoformat(near) - d0).days)} 天）"
        # L6 仅巡次相符：日期 ±2 天内唯一一场
        if not assign and d0 and tour:
            cand = [ds_ for ds_, v in shows.items() if v.get("tour") == tour
                    and abs((date.fromisoformat(ds_) - d0).days) <= 2]
            if len(cand) == 1:
                assign, level, why = cand[0], 6, "巡次+日期±2天唯一"
        stat[f"L{level}" if level else "未认领"] += 1
        out.append({**{k: r.get(k) for k in ("tag", "song", "tour", "city", "date", "review_status", "claimable")},
                    "show_date": assign, "level": level, "why": why})

    # 场次级汇总（站点层口径：有几场至少 1 条已认领素材，且该素材可主张）
    per_show = defaultdict(lambda: {"n": 0, "claimable": 0})
    for o in out:
        if o["show_date"]:
            per_show[o["show_date"]]["n"] += 1
            per_show[o["show_date"]]["claimable"] += int(bool(o["claimable"]))
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "rows": len(out), "levels": dict(stat),
        "shows_with_material": len(per_show),
        "shows_with_claimable": sum(1 for v in per_show.values() if v["claimable"]),
        "shows_total": len(shows),
    }
    (DATA / "show_assignment.json").write_text(
        json.dumps({"summary": summary, "per_show": per_show, "rows": out}, ensure_ascii=False, indent=1,
                   default=str), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("→ data/show_assignment.json")
    assert summary["rows"] == len(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
