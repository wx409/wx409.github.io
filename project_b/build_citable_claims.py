#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建「可引用句」卡片：覆盖全部录音室逐帧文件 + 现场逐帧文件 + 双人场块级。

第一性原理：一句话能不能被引用，取决于它能不能被**复算**。
所以每条都给出：曲目 / 版本 / 时间戳 / 取窗 / 指标 / 出处文件；时间戳从逐帧 CSV 现算。

数据
  E:\\wx\\论文素材_王晰作传\\音域分析\\专辑音频_分析\\**\\*_f0.csv   录音室（72 曲）
  E:\\wx\\论文素材_王晰作传\\音域分析\\分析结果\\*_f0.csv            现场/精测（16 曲）
输出：data/citable_claims.json
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALBUM_F0 = Path(r"E:\wx\论文素材_王晰作传\音域分析\专辑音频_分析")
STAGE_F0 = Path(r"E:\wx\论文素材_王晰作传\音域分析\分析结果")
OUT = ROOT / "data" / "citable_claims.json"

TOL = 0.5
MIN_DUR = 0.15


def hz2midi(h):
    return 69 + 12 * math.log2(h / 440.0)


def mmss(t):
    return "%d:%05.2f" % (int(t // 60), t - 60 * int(t // 60))


def lowest_segment(path):
    """切音符块 → 过滤时长 → 取中位音高最低的块。返回 hz/t0/t1/dur/swing。"""
    frames = []
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
                frames.append((t, hz))
    if len(frames) < 50:
        return None

    blocks, cur = [], []
    for t, hz in frames:
        m = hz2midi(hz)
        if cur:
            ok_gap = t - cur[-1][0] <= 0.25
            med = statistics.median(hz2midi(x[1]) for x in cur)
            ok_pitch = abs(m - med) <= TOL
            if not (ok_gap and ok_pitch):
                blocks.append(cur); cur = []
        cur.append((t, hz))
    if cur:
        blocks.append(cur)

    notes = []
    for b in blocks:
        if len(b) < 5:
            continue
        dur = b[-1][0] - b[0][0]
        if dur < MIN_DUR:
            continue
        ms = [hz2midi(x[1]) for x in b]
        notes.append({"hz": statistics.median([x[1] for x in b]),
                      "midi": statistics.median(ms),
                      "t0": b[0][0], "t1": b[-1][0], "dur": dur,
                      "swing": (max(ms) - min(ms)) * 100})
    if not notes:
        return None
    low = min(notes, key=lambda n: n["midi"])
    return {"hz": round(low["hz"], 1),
            "t0": mmss(low["t0"]), "t1": mmss(low["t1"]),
            "dur": round(low["dur"], 2),
            "swing_cents": round(low["swing"])}




def block_near(path, target_hz, tol=TOL):
    """在逐帧文件里找中位音高最接近 target_hz、且时长达标的块，返回时间戳。"""
    frames = []
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
                frames.append((t, hz))
    blocks, cur = [], []
    for t, hz in frames:
        m = hz2midi(hz)
        if cur:
            med = statistics.median(hz2midi(x[1]) for x in cur)
            if not (t - cur[-1][0] <= 0.25 and abs(m - med) <= tol):
                blocks.append(cur); cur = []
        cur.append((t, hz))
    if cur:
        blocks.append(cur)
    tgt = hz2midi(target_hz)
    best = None
    for b in blocks:
        if len(b) < 5 or b[-1][0] - b[0][0] < MIN_DUR:
            continue
        med = statistics.median(hz2midi(x[1]) for x in b)
        if abs(med - tgt) > tol:
            continue
        if best is None or (b[-1][0] - b[0][0]) > (best[-1][0] - best[0][0]):
            best = b
    if not best:
        return None
    ms = [hz2midi(x[1]) for x in best]
    return {"hz": round(statistics.median([x[1] for x in best]), 1),
            "t0": mmss(best[0][0]), "t1": mmss(best[-1][0]),
            "dur": round(best[-1][0] - best[0][0], 2),
            "swing_cents": round((max(ms) - min(ms)) * 100)}

def scan(base, kind):
    out = []
    for p in sorted(base.rglob("*_f0.csv")):
        seg = lowest_segment(p)
        if seg:
            out.append({"file": p, "rel": p.relative_to(base).as_posix(), "kind": kind, **seg})
    return out


def main() -> int:
    album = scan(ALBUM_F0, "录音室")
    stage = scan(STAGE_F0, "现场/精测")
    print("录音室逐帧文件 %d｜现场逐帧 %d" % (len(album), len(stage)))

    claims = []
    # 录音室：以 stats.json 的 low_stable 为权威音高，逐帧文件只用来定位时间戳
    studio = []
    for x in album:
        st = x["file"].with_name(x["file"].name.replace("_f0.csv", "_stats.json"))
        low_hz, note = None, None
        if st.exists():
            try:
                j = json.loads(st.read_text(encoding="utf-8"))
                ls = j.get("low_stable") or {}
                low_hz, note = ls.get("hz"), ls.get("note")
            except Exception:
                pass
        seg = block_near(x["file"], low_hz) if low_hz else None
        studio.append({"rel": x["rel"], "file": x["file"], "hz": low_hz or x["hz"],
                       "note": note, "seg": seg})
    for r in sorted([r for r in studio if r["hz"]], key=lambda r: r["hz"])[:10]:
        song = r["file"].stem.replace("_f0", "")
        alb = r["rel"].split("/")[0]
        seg = r["seg"]
        ts = ("%s–%s" % (seg["t0"], seg["t1"])) if seg else "该曲逐帧文件中未定位到稳定段"
        claims.append({
            "id": "studio-" + song,
            "song": song,
            "version": "录音室（专辑：%s）" % alb,
            "timestamp": ts,
            "metric": "最低稳定音（stats.json low_stable，过 ≥0.15s/HNR 门槛）",
            "sentence": ("《%s》（%s）最低稳定音 %s（%.1fHz）%s。"
                         % (song, alb, r["note"] or "—", r["hz"],
                            ("，出现在 %s–%s，持续 %.2f 秒" % (seg["t0"], seg["t1"], seg["dur"])) if seg else "")),
            "source": "音域分析/专辑音频_分析/" + r["rel"].replace("_f0.csv", "_stats.json"),
            "caveat": "音高来自 stats.json 的 low_stable；时间戳由逐帧文件按同一音高定位",
        })

    for x in sorted(stage, key=lambda r: r["hz"])[:8]:
        song = x["file"].stem.replace("_f0.csv", "")
        claims.append({
            "id": "stage-" + song,
            "song": song,
            "version": "现场/精测（见文件名）",
            "timestamp": "%s–%s" % (x["t0"], x["t1"]),
            "metric": "逐帧 F0，±%.1f 半音窗口，连续 ≥%.2fs" % (TOL, MIN_DUR),
            "sentence": "现场版《%s》最低音 %.1fHz，出现在 %s–%s，连续 %.2f 秒。"
                        % (song, x["hz"], x["t0"], x["t1"], x["dur"]),
            "source": "音域分析/分析结果/" + x["file"].name,
            "caveat": "现场音轨受混音与伴奏影响；极值音以台账复核状态为准",
        })

    try:
        ba = json.loads((ROOT / "data" / "block_analysis.json").read_text(encoding="utf-8"))
        m = (ba.get("metrics") or {}).get("f0_median_midi")
        if m:
            claims.append({
                "id": "duet-pitch",
                "song": "全场块级（23 段歌单按段归属）",
                "version": "现场 2026-10-09 北京天桥艺术中心·大剧场《沉响与长歌》",
                "timestamp": "各块见 data/show_blocks/沉响与长歌_20261009.json 的 t0_hms/t1_hms",
                "metric": "演唱音高中位（MIDI），块级中位",
                "sentence": "同一套录音里，王晰的演唱音高中位比同台歌手低 %.1f 个半音（%.2f vs %.2f MIDI，p=%.3f）。"
                            % (abs(m["diff"]), m["median_wang"], m["median_aori"], m["p"]),
                "source": "data/block_analysis.json + data/show_blocks/",
                "caveat": "两人曲目不同、n=2 场；只作描述，不作因果",
            })
    except Exception:
        pass

    payload = {
        "schema": "citable-claims/v2",
        "caliber": "逐帧 F0；最低连续段窗口 ±%.1f 半音、时长 ≥%.2fs；摆幅=段内极差" % (TOL, MIN_DUR),
        "n_album_files": len(album), "n_stage_files": len(stage),
        "global_studio_min": (min([r["hz"] for r in studio if r["hz"]], default=None)),
        "claims": claims,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("全局最低（录音室逐帧）: %.1f Hz" % (payload["global_studio_min"] or 0))
    for c in claims[:5]:
        print("  -", c["sentence"][:96])
    print("→", OUT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
