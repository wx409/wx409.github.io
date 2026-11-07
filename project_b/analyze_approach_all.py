#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""② 扩到全量逐帧文件：极值音的「到达方式」在 1500+ 个 F0 文件上统计。

为什么之前只有 16 首：只扫了 `音域分析\\分析结果` 一个目录。
实际磁盘上有 1500+ 个 `*_f0.csv`（场次音频/他人主导/专辑/沉响分段/QQ 对照…），
它们本来就是同一条管线产出的，不需要重跑分离。

口径（与其它模块一致）
  · 音符块：相邻帧间隔 ≤0.25s 且中位音高变化 ≤0.5 半音
  · 稳定音：块时长 ≥0.15s、≥5 帧
  · 取「中位音高最低」的块作为该文件的极值音
  · 到达方式：看该块起点前 2 秒的轨迹
        jump   前 0.4s 内下跳 ≥3 半音
        slide  前 2s 内连续下行 ≥3 半音
        direct 前 2s 已在 ±2 半音内
        head   块从文件开头就开始（无前段）

输出：data/approach_all.json
"""
from __future__ import annotations

import csv
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "approach_all.json"
ROOTS = [
    Path(r"E:\wx\论文素材_王晰作传\音域分析"),
    Path(r"E:\wx\论文素材_王晰作传\_staging_现场_分析"),
]
TOL = 0.5
MIN_DUR = 0.15

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def hz2midi(h):
    return 69 + 12 * math.log2(h / 440.0)


def mmss(t):
    return "%d:%05.2f" % (int(t // 60), t - 60 * int(t // 60))


def frames_of(path):
    out = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                t = float(r["time_s"])
                raw = (r.get("f0_hz") or "").strip()
                if not raw:
                    continue
                hz = float(raw)
                if "voiced_pyin" in r and int(float(r.get("voiced_pyin") or 0)) == 0:
                    continue
            except (KeyError, ValueError):
                continue
            if hz > 0:
                out.append((t, hz))
    return out


def blocks_of(frames):
    blocks, cur = [], []
    for t, hz in frames:
        m = hz2midi(hz)
        if cur:
            med = statistics.median(hz2midi(x[1]) for x in cur)
            if not (t - cur[-1][0] <= 0.25 and abs(m - med) <= TOL):
                blocks.append(cur); cur = []
        cur.append((t, hz))
    if cur:
        blocks.append(cur)
    return [b for b in blocks if len(b) >= 5 and b[-1][0] - b[0][0] >= MIN_DUR]


def analyse(path, frames):
    bl = blocks_of(frames)
    if not bl:
        return None
    low = min(bl, key=lambda b: statistics.median(hz2midi(x[1]) for x in b))
    t0, t1 = low[0][0], low[-1][0]
    med = statistics.median(hz2midi(x[1]) for x in low)
    ms = [hz2midi(x[1]) for x in low]
    pre = [(t, hz2midi(hz)) for t, hz in frames if t0 - 2.0 <= t < t0]
    if not pre:
        kind, drop = "head", 0.0
    else:
        drop = pre[0][1] - pre[-1][1]
        fast = [p for p in pre if p[0] >= t0 - 0.4]
        if abs(pre[-1][1] - med) <= 2:
            kind = "direct"
        elif fast and (fast[0][1] - pre[-1][1]) >= 3:
            kind = "jump"
        elif drop >= 3:
            kind = "slide"
        else:
            kind = "direct"
    return {"file": path.name, "dir": path.parent.name,
            "low_hz": round(statistics.median([x[1] for x in low]), 1),
            "low_midi": round(med, 2),
            "t0": mmss(t0), "t1": mmss(t1), "dur": round(t1 - t0, 2),
            "approach": kind, "drop": round(drop, 1),
            "swing_cents": round((max(ms) - min(ms)) * 100)}


def song_of(path):
    n = path.stem
    n = re.sub(r"_f0$", "", n)
    n = re.sub(r"^(?:\d+[\s._-]*)", "", n)
    return n.strip()


def main() -> int:
    files = []
    for root in ROOTS:
        if root.exists():
            files.extend(sorted(root.rglob("*_f0.csv")))
    print("扫描到逐帧文件 %d 个" % len(files))
    rows, skipped = [], 0
    for p in files:
        try:
            fr = frames_of(p)
        except Exception:
            skipped += 1; continue
        if len(fr) < 50:
            skipped += 1; continue
        r = analyse(p, fr)
        if r:
            r["song"] = song_of(p)
            r["path"] = str(p.relative_to(p.parents[2])) if len(p.parents) > 2 else p.name
            rows.append(r)
        else:
            skipped += 1

    dist = Counter(r["approach"] for r in rows)
    print("可用 %d｜跳过 %d｜到达方式：%s" % (len(rows), skipped, dict(dist.items())))

    # 同曲多版本：到达方式是否一致
    by_song = defaultdict(list)
    for r in rows:
        by_song[r["song"]].append(r["approach"])
    multi = {k: v for k, v in by_song.items() if len(v) >= 3}

    def mode_share(v):
        c = Counter(v)
        return round(100 * c.most_common(1)[0][1] / len(v), 0)

    consist = sorted(((k, len(v), mode_share(v)) for k, v in multi.items()),
                     key=lambda x: -x[1])[:12]
    print("同曲 ≥3 版：%d 首（例：%s...）" % (len(multi), "、".join(k for k, _, _ in consist[:4])))
    for k, n, s in consist[:6]:
        print("   %-16s %2d 版｜最常见方式占 %2d%%" % (k[:16], n, s))

    payload = {"schema": "approach-all/v1",
               "n_files": len(rows), "n_skipped": skipped,
               "distribution": dict(dist),
               "caliber": "音符块 ≥0.15s/≥5 帧；到达方式看块前 2s；取中位音高最低块",
               "consistency": [{"song": k, "n": n, "mode_share_pct": s} for k, n, s in consist],
               "rows": rows, "generated_at": date.today().isoformat()}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
