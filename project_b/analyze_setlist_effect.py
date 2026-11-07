#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""④ 曲目级「上歌单」效应：同一首歌进/不进歌单的年份，它自己的指数怎么变。

设计（within-song 双向固定效应）
    log(该曲当年指数均值) = 曲目固定效应 + 年份固定效应 + β·当年是否进歌单 + ε
  · 曲目固定效应吸收"这首歌本身火不火"
  · 年份固定效应吸收"这一年大盘怎么样"
  · β 就是"同一首歌，进歌单的年份 vs 不进的年份"的差异
  · 区间用按曲目整群自助

数据：data/setlists.json（64 场歌单）× music_index_long.csv（逐曲日频）
输出：data/setlist_effect.json
"""
from __future__ import annotations

import csv
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SETLISTS = ROOT / "data" / "setlists.json"
LONG = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
OUT = ROOT / "data" / "setlist_effect.json"


def norm(s: str) -> str:
    s = (s or "").strip().lower()
    for a, b in (("（", "("), ("）", ")"), (" ", ""), ("·", ""), ("’", "'")):
        s = s.replace(a, b)
    return s


def main() -> int:
    # 逐曲逐年均值
    sums = defaultdict(lambda: defaultdict(list))
    with open(LONG, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            d = (r.get("date") or "")[:10]
            if len(d) < 4:
                continue
            try:
                v = float(str(r.get("index", "")).replace(",", ""))
            except ValueError:
                continue
            if v <= 0:
                continue
            sums[norm(r.get("song") or "")][d[:4]].append(v)
    panel = {}
    for song, yrs in sums.items():
        for y, vals in yrs.items():
            if len(vals) >= 30 and int(y) >= 2023:
                panel[(song, y)] = math.log(statistics.mean(vals))

    # 歌单：曲目 × 年份 是否上台
    sl = json.loads(SETLISTS.read_text(encoding="utf-8")).get("setlists") or {}
    treat = set()
    for s in sl.values():
        y = (s.get("date") or "")[:4]
        if not y:
            continue
        for x in (s.get("songs") or []):
            t = norm(x.get("title") or "")
            if t:
                treat.add((t, y))

    rows = [(song, y, v, 1 if (song, y) in treat else 0)
            for (song, y), v in panel.items()]
    n_tr = sum(r[3] for r in rows)
    print("面板 %d 个「曲目×年」观测｜进歌单 %d｜未进 %d｜曲目 %d｜年份 %s"
          % (len(rows), n_tr, len(rows) - n_tr, len({r[0] for r in rows}),
             sorted({r[1] for r in rows})))

    songs = sorted({r[0] for r in rows})
    years = sorted({r[1] for r in rows})
    sidx = {s: i for i, s in enumerate(songs)}
    yidx = {y: i for i, y in enumerate(years)}

    def design(rs):
        X = np.zeros((len(rs), len(songs) + len(years) + 1))
        y = np.zeros(len(rs))
        for i, (song, yr, v, d) in enumerate(rs):
            X[i, sidx[song]] = 1.0
            X[i, len(songs) + yidx[yr]] = 1.0
            X[i, -1] = d
            y[i] = v
        return X, y

    X, yv = design(rows)
    beta, *_ = np.linalg.lstsq(X, yv, rcond=None)
    eff = (math.exp(beta[-1]) - 1) * 100

    rng = random.Random(20261107)
    boots = []
    by_song = defaultdict(list)
    for r in rows:
        by_song[r[0]].append(r)
    for _ in range(400):
        pick = []
        for _ in songs:
            pick.extend(by_song[rng.choice(songs)])
        Xb, yb = design(pick)
        try:
            bb, *_ = np.linalg.lstsq(Xb, yb, rcond=None)
            boots.append((math.exp(bb[-1]) - 1) * 100)
        except Exception:
            continue
    boots.sort()
    lo, hi = (boots[int(.025 * len(boots))], boots[int(.975 * len(boots)) - 1]) if boots else (None, None)

    print("上歌单效应：%+.1f%%（95%%CI %s ~ %s）｜n_draw=%d"
          % (eff, f"{lo:+.1f}" if lo is not None else "—",
             f"{hi:+.1f}" if hi is not None else "—", len(boots)))
    OUT.write_text(json.dumps({
        "schema": "setlist-effect/v1",
        "model": "log(该曲当年指数均值) ~ 曲目FE + 年份FE + 是否进歌单；按曲目整群自助 400 次",
        "n_obs": len(rows), "n_treated": n_tr, "n_songs": len(songs), "years": years,
        "effect_pct": round(eff, 1),
        "ci95": [round(lo, 1), round(hi, 1)] if boots else None,
        "generated_at": date.today().isoformat(),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
