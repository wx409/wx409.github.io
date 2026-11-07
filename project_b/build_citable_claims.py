#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「可引用句」做成带出处的卡片：曲目 / 版本 / 时间戳 / 指标 / 复核状态 / 数据文件。

起因：上一轮那三句社媒文案没头没尾，而且「B1 站了 0.27 秒、抖动 10 音分」经复核不成立——
原始帧上《多听有益》录音室版的最低段是 2:32.99–2:33.60（0.61s），摆幅约 80 音分。
本脚本只输出**能从数据里逐条对上**的说法，对不上的直接标「待核」。

输出：data/citable_claims.json（供页面/文案引用）
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
F0DIR = Path(r"E:\wx\论文素材_王晰作传\音域分析\分析结果")
OUT = ROOT / "data" / "citable_claims.json"


def hz2midi(h):
    return 69 + 12 * math.log2(h / 440.0)


def mmss(t):
    return "%d:%05.2f" % (int(t // 60), t - 60 * int(t // 60))


def lowest_segment(csv_path, tol=0.8, min_dur=0.15):
    """在 ±tol 半音内取最低音的连续段，返回 (hz, t0, t1, swing_cents)。"""
    rows = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                if not int(float(r.get("voiced_pyin") or 0)):
                    continue
                t, hz = float(r["time_s"]), float(r["f0_hz"])
            except (KeyError, ValueError):
                continue
            if hz > 0:
                rows.append((t, hz))
    if not rows:
        return None
    lo = min(rows, key=lambda x: x[1])
    m0 = hz2midi(lo[1])
    keep = sorted([x for x in rows if abs(hz2midi(x[1]) - m0) <= tol])
    blocks, cur = [], []
    for x in keep:
        if cur and x[0] - cur[-1][0] > 0.12:
            blocks.append(cur); cur = []
        cur.append(x)
    if cur:
        blocks.append(cur)
    # 取包含最低点、且最长的那个连续块
    cand = [b for b in blocks if b[0][0] <= lo[0] <= b[-1][0]] or blocks
    b = max(cand, key=len)
    if b[-1][0] - b[0][0] < min_dur:
        return None
    ms = [hz2midi(x[1]) for x in b]
    return {"hz": round(statistics.median([x[1] for x in b]), 1),
            "t0": mmss(b[0][0]), "t1": mmss(b[-1][0]),
            "dur": round(b[-1][0] - b[0][0], 2),
            "swing_cents": round((max(ms) - min(ms)) * 100)}


def main() -> int:
    claims = []

    # ── 主张 1：录音室最低稳定音（站点口径值，来自专辑全量实测）──
    try:
        alb = json.loads((ROOT / "data" / "archive_vocal_albums.json").read_text(encoding="utf-8"))
        rows = alb.get("rows") or alb.get("songs") or []
        low = min((r for r in rows if r.get("low_hz")), key=lambda r: r["low_hz"])
        claims.append({
            "id": "studio-lowest",
            "sentence": "录音室作品里最低的稳定音是 %s（%.1fHz），出自《%s》。"
                        % (low.get("low"), low["low_hz"], low.get("title")),
            "song": low.get("title"),
            "version": "录音室（专辑：%s）" % (low.get("album") or "—"),
            "timestamp": "待补（该曲未生成逐帧文件，仅有全曲统计）",
            "metric": "最低稳定音（≥0.15s、HNR≥5dB、过复核门槛）",
            "review": low.get("trust") or low.get("verify") or "—",
            "source": "data/archive_vocal_albums.json",
            "caveat": "全曲统计，不含逐帧时间戳；引用时写「录音室曲目」",
        })
    except Exception as e:
        claims.append({"id": "studio-lowest", "error": str(e)[:80]})

    # ── 主张 2：有逐帧文件的极值音，带时间戳 ──
    for fn in ("多听有益_f0.csv", "多听有益_杭州站_f0.csv", "渡荆门送别_f0.csv"):
        p = F0DIR / fn
        if not p.exists():
            continue
        seg = lowest_segment(p)
        if not seg:
            continue
        claims.append({
            "id": "f0-" + fn.replace("_f0.csv", ""),
            "sentence": "《%s》这一版，最低音 %.1fHz 出现在 %s–%s，连续 %.2f 秒，段内音高摆幅约 %d 音分。"
                        % (fn.replace("_f0.csv", ""), seg["hz"], seg["t0"], seg["t1"],
                           seg["dur"], seg["swing_cents"]),
            "song": fn.replace("_f0.csv", ""),
            "version": "见文件名（含场次/版本）",
            "timestamp": "%s–%s" % (seg["t0"], seg["t1"]),
            "metric": "逐帧 F0，取 ±0.8 半音内最低连续段",
            "review": "逐帧文件（复核状态见台账）",
            "source": "音域分析/分析结果/" + fn,
            "caveat": "摆幅为段内极差，含颤音与测量噪声",
        })

    # ── 主张 3：双人场同台对照（块级）──
    try:
        ba = json.loads((ROOT / "data" / "block_analysis.json").read_text(encoding="utf-8"))
        m = (ba.get("metrics") or {}).get("f0_median_midi")
        if m:
            claims.append({
                "id": "duet-pitch",
                "sentence": "2026-10-09 北京天桥艺术中心《沉响与长歌》，同一套录音里，王晰的演唱音高中位比同台歌手低 %.1f 个半音（%.2f vs %.2f MIDI，p=%.3f）。"
                            % (abs(m["diff"]), m["median_wang"], m["median_aori"], m["p"]),
                "song": "全场块级（23 段歌单，按段归属）",
                "version": "现场 2026-10-09 北京天桥艺术中心·大剧场",
                "timestamp": "各块见 data/show_blocks/沉响与长歌_20261009.json 的 t0_hms/t1_hms",
                "metric": "演唱音高中位（MIDI），块级中位",
                "review": "who_confirmed（人耳确认块归属）",
                "source": "data/show_blocks/沉响与长歌_20261009.json + data/block_analysis.json",
                "caveat": "两人曲目不同、n=2 场；只作描述不作因果",
            })
    except Exception as e:
        claims.append({"id": "duet-pitch", "error": str(e)[:80]})

    OUT.write_text(json.dumps({"schema": "citable-claims/v1", "claims": claims},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    for c in claims:
        print("-", c.get("id"), "|", (c.get("sentence") or c.get("error"))[:110])
    print("→", OUT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
