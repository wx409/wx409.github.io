#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""状态 vs 特质：把现场层的指标拆成「歌手特质 / 场次状态 / 素材残差」。

模型（每个指标一条）
    y ~ 1 + hnr_db + C(tour) + (1|show) + (1|song)
    · show  = 日期+城市（同一场的多条素材共享）
    · song  = 曲目（同一首歌跨场共享）
    · hnr_db = 素材质量代理（测量误差的主要来源）
    · C(tour) = 巡次固定效应（仅敏感性模型里加，见 --with-tour）

输出：data/variance_components.json
用法：python -X utf8 project_b\\variance_components.py [--with-tour]

为什么不用城市做随机效应：22 个城市大多只有 1–4 场，且城市与录音条件（场馆/饭拍/官方）
高度共线，会把"测量误差"错记成"城市差异"。城市信息留在 strata 里，不做模型项。
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "archive_stage_tour.json"
OUT = ROOT / "data" / "variance_components.json"

METRICS = {
    "vibrato_hz": "颤音速率 Hz",
    "vibrato_cents": "颤音幅度 音分",
    "stability_cents": "音符内稳定性 音分",
    "intonation_cents": "音准偏差 音分",
}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load() -> pd.DataFrame:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    rows = []
    for r in d.get("rows") or []:
        song = (r.get("song") or "").strip()
        show = "%s|%s" % (r.get("date") or "", r.get("city") or "")
        if not song or len(show) < 10:
            continue
        rows.append({
            "song": song, "show": show, "tour": r.get("tour") or "未标注",
            "date": r.get("date"), "city": r.get("city") or "",
            "hnr": r.get("hnr_db"),
            "vibrato_hz": r.get("vibrato_hz"), "vibrato_cents": r.get("vibrato_cents"),
            "stability_cents": r.get("stability_cents"), "intonation_cents": r.get("intonation_cents"),
            "review": r.get("review_status") or "",
        })
    return pd.DataFrame(rows)


def _fit_one(d: pd.DataFrame, col: str, group: str, rhs: str):
    """单随机效应模型：y ~ rhs + (1|group)，返回 (组方差, 残差, n)。"""
    m = smf.mixedlm(f"{col} ~ {rhs}", d, groups=d[group]).fit(reml=True, method="lbfgs")
    return float(m.cov_re.iloc[0, 0]), float(m.scale), int(len(d))


def fit(df: pd.DataFrame, col: str, with_tour: bool):
    """分别估计「场次」与「曲目」各自能解释多少方差（不做交叉模型，避免不收敛）。"""
    d = df.dropna(subset=[col]).copy()
    d = d[d[col] > 0]
    if len(d) < 60:
        return None
    rhs = "1"
    if d["hnr"].notna().sum() >= len(d) * 0.6:
        d["hnr"] = d["hnr"].fillna(d["hnr"].median())
        rhs = "hnr"
    if with_tour:
        rhs += " + C(tour)"
    try:
        v_show, r_show, n1 = _fit_one(d, col, "show", rhs)
    except Exception as e:
        v_show, r_show, n1 = None, None, len(d)
    try:
        v_song, r_song, n2 = _fit_one(d, col, "song", rhs)
    except Exception as e:
        v_song, r_song, n2 = None, None, len(d)
    tot_show = (v_show + r_show) if v_show is not None else None
    tot_song = (v_song + r_song) if v_song is not None else None
    return {
        "n": int(len(d)), "n_shows": int(d["show"].nunique()), "n_songs": int(d["song"].nunique()),
        "mean": round(float(d[col].mean()), 3),
        "sd_total": round(float(d[col].std()), 3),
        "icc_show_pct": round(100 * v_show / tot_show, 1) if tot_show else None,
        "icc_song_pct": round(100 * v_song / tot_song, 1) if tot_song else None,
        "resid_show_pct": round(100 * r_show / tot_show, 1) if tot_show else None,
        "resid_song_pct": round(100 * r_song / tot_song, 1) if tot_song else None,
        "with_tour": with_tour,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-tour", action="store_true")
    args = ap.parse_args()

    df = load()
    print("可用素材 %d 条｜场次 %d｜曲目 %d" % (len(df), df["show"].nunique(), df["song"].nunique()))
    out = {}
    for col, label in METRICS.items():
        res = fit(df, col, args.with_tour)
        out[col] = {"label": label, **(res or {"error": "样本不足"})}
        if res and res.get("icc_show_pct") is not None:
            print("  %-16s n=%3d 场次=%d 曲目=%d｜场次解释 %4.1f%%｜曲目解释 %4.1f%%｜SD=%.3f"
                  % (label, res["n"], res["n_shows"], res["n_songs"],
                     res["icc_show_pct"], res["icc_song_pct"] or 0, res["sd_total"]))
        else:
            print("  %-14s %s" % (label, res))

    payload = {
        "schema": "variance-components/v1",
        "model": ("y ~ 1 + hnr_db + %s(1|show) + (1|song)" % ("C(tour) + " if args.with_tour else "")),
        "note": ("方差成分（REML）：show=同场多条素材，song=同曲跨场；hnr_db 作测量质量代理；"
                 "城市不进模型（与录音条件共线）"),
        "data": out,
        "generated_at": date.today().isoformat(),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
