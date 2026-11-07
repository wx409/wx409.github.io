# -*- coding: utf-8 -*-
"""把大屏的聚合 JSON 还原成可做统计的明细表。

输入（只读）：
  dashboard/dashboard_view.json      曲目 × 日指数、91 场事件、每场每曲涨幅
  dashboard/event_study.json         每场事件的对齐曲线与微博量
  data/vocal_measurements.json       1006 行声学长表（曲目 × 版本）
输出：
  analysis/out/panel_song_day.parquet   曲目 × 日（23 首，含缺口）
  analysis/out/event_song.parquet       事件 × 曲目（91 × ~25，含 on_setlist）
  analysis/out/events.parquet           事件级元数据
  analysis/out/vocal.parquet            声学测量长表（展开 metrics）
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)


def load(name):
    return pd.read_json(ROOT / "dashboard" / name, typ="frame")


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def panel_song_day(d):
    rows = []
    for s in d.get("detail_songs") or []:
        for date, val in s.get("points") or []:
            rows.append({"song": s.get("name"), "uid": s.get("uid"), "date": date, "value": float(val)})
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["song", "date"]).reset_index(drop=True)
    return df


def event_song(d):
    rows = []
    for e in d.get("tour_song_effects") or []:
        base = {
            "event_date": e.get("date"),
            "city": e.get("city"),
            "city_tier": e.get("city_tier"),
            "venue_type": e.get("venue_type"),
            "content_type": e.get("content_type"),
            "tour": e.get("tour"),
            "scene": e.get("scene"),
            "event_uplift": e.get("total_uplift"),
            "event_uplift_wk": e.get("total_uplift_wk"),
            "setlist_share": e.get("setlist_uplift"),
            "radiance_uplift": e.get("radiance_uplift"),
            "pattern": e.get("pattern"),
        }
        for s in e.get("songs") or []:
            rows.append({**base, "song": s.get("name"),
                         "uplift": s.get("uplift"),
                         "on_setlist": bool(s.get("on_setlist"))})
    df = pd.DataFrame(rows)
    df["event_date"] = pd.to_datetime(df["event_date"])
    df["uplift"] = pd.to_numeric(df["uplift"], errors="coerce")
    return df


def events(d):
    rows = []
    for e in d.get("tour_song_effects") or []:
        rows.append({
            "event_date": e.get("date"), "city": e.get("city"),
            "city_tier": e.get("city_tier"), "venue_type": e.get("venue_type"),
            "content_type": e.get("content_type"), "tour": e.get("tour"),
            "scene": e.get("scene"), "uplift": e.get("total_uplift"),
            "uplift_wk": e.get("total_uplift_wk"), "radiance": e.get("radiance_uplift"),
            "pattern": e.get("pattern"), "n_songs": len(e.get("songs") or []),
            "n_setlist": sum(1 for s in (e.get("songs") or []) if s.get("on_setlist")),
            "daily": json.dumps(e.get("daily_series") or {}, ensure_ascii=False),
            "base_polluted": json.dumps(e.get("base_polluted"), ensure_ascii=False),
        })
    df = pd.DataFrame(rows)
    df["event_date"] = pd.to_datetime(df["event_date"])
    for c in ("uplift", "uplift_wk", "radiance"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def vocal():
    d = read_json(ROOT / "data" / "vocal_measurements.json")
    rows = []
    for r in d["rows"]:
        m = r.get("metrics") or {}
        v = r.get("verify") or {}
        p = r.get("provenance") or {}
        rows.append({
            "id": r.get("id"), "song": r.get("song"), "version": r.get("version"),
            "layer": r.get("layer"), "album": r.get("album"),
            "tour": r.get("tour"), "city": r.get("city"), "date": r.get("date"),
            "low_note": m.get("low_note"), "low_hz": m.get("low_hz"),
            "high_note": m.get("high_note"), "high_hz": m.get("high_hz"),
            "span_octaves": m.get("span_octaves"),
            "verify_state": v.get("state"),
            "measured_by": p.get("measured_by"),
            "extra_metrics": json.dumps({k: x for k, x in m.items()
                                        if k not in ("low_note", "low_hz", "high_note", "high_hz", "span_octaves")},
                                       ensure_ascii=False),
        })
    df = pd.DataFrame(rows)
    for c in ("low_hz", "high_hz", "span_octaves"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def main():
    d = read_json(ROOT / "dashboard" / "dashboard_view.json")
    frames = {
        "panel_song_day": panel_song_day(d),
        "event_song": event_song(d),
        "events": events(d),
        "vocal": vocal(),
    }
    for name, df in frames.items():
        path = OUT / f"{name}.parquet"
        df.to_parquet(path, index=False)
        print(f"{name}: rows={len(df)} cols={len(df.columns)} -> {path.name}")
    es = frames["event_song"]
    print("事件数:", es["event_date"].nunique(),
          "| 曲目-事件行:", len(es),
          "| setlist 行:", int(es["on_setlist"].sum()),
          "| 含 setlist 的事件:", es[es["on_setlist"]]["event_date"].nunique())
    v = frames["vocal"]
    print("声学行:", len(v), "| 层:", v["layer"].value_counts().to_dict())
    print("复核状态 top5:", v["verify_state"].value_counts().head(5).to_dict())


if __name__ == "__main__":
    main()
