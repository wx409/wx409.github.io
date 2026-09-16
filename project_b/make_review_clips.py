#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_review_clips.py —— 听辨样本切制（把待复核读数切成 6~8 秒小段送人耳）。

为什么需要（2026-09-16 实际教训）：
  这一天切了 4 批听辨样本（待复核 12 条 / 全量 41 条 / C6 待确认 6 条 / 单条定位），
  脚本都写在 temp/ 里 —— **临时目录随时会清，可复用操作必须固化**。

用法：
  python -X utf8 project_b/make_review_clips.py --list          # 列出待复核读数
  python -X utf8 project_b/make_review_clips.py --mode low      # 切低音待复核
  python -X utf8 project_b/make_review_clips.py --mode high     # 切高音 C6 区待复核
  python -X utf8 project_b/make_review_clips.py --song 友谊地久天长 --hz 1059.3 --tag <tag>
                                                                 # 单条精确定位（切前/中/后三段）

纪律（血泪）：
  ① **同名曲目必须按 tag 精确匹配**，禁止用 next() 取首条 —— 曾因此切错源，
     用户一句"这里面没有举杯"才拦下；
  ② 高音的时刻**不能**用低音的 t_s（谐波列 t_s 是低音时刻），须从 f0.csv 反查；
  ③ 音名与 Hz 在文件名里是相连的（C267.0 = C2 + 67.0），解析时不可按常规切分。
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = Path(__file__).resolve().parent.parent
AN = Path(r"E:\wx\论文素材_王晰作传\音域分析")
TOUR = ROOT / "data" / "archive_stage_tour.json"
OUTBASE = AN / "听辨样本"

MIX_ROOTS = [AN / "场次音频" / b for b in ("wav", "wav_新源现场", "wav_广州逐曲")]
VOC_ROOTS = [AN / "场次音频" / b for b in ("wav_分离", "wav_新源现场_分离", "wav_广州逐曲_分离")]
F0_ROOTS = [AN / "场次音频" / b for b in
            ("wav_分析", "wav_新源现场_分析", "wav_广州逐曲_分析", "wav_分离", "wav_新源现场_分离")]

GOOD = ("谐波列复核通过", "双引擎一致", "人耳确认", "已取证")


def load_rows():
    if not TOUR.exists():
        raise SystemExit("缺少 data/archive_stage_tour.json")
    return json.loads(TOUR.read_text(encoding="utf-8")).get("rows") or []


def find_wav(song, tag, roots):
    for b in roots:
        p = b / song / (tag + ".wav")
        if p.exists():
            return p
    return None


def find_voc(song, tag):
    for b in VOC_ROOTS:
        g = glob.glob(str(b / song / tag / "**" / "vocals.wav"), recursive=True)
        if g:
            return Path(g[0])
    return None


def time_of(song, tag, hz, tol=0.03):
    """从 f0.csv 反查该音出现的中位时刻（高音/低音通用）。"""
    for b in F0_ROOTS:
        for f in glob.glob(str(b / song / (tag + "*_f0.csv"))):
            try:
                rr = list(csv.DictReader(io.open(f, encoding="utf-8", errors="replace")))
            except Exception:
                continue
            if not rr:
                continue
            cols = list(rr[0].keys())
            tc = cols[0]
            fc = next((c for c in cols if "f0" in c.lower() or "hz" in c.lower()), cols[1])
            hits = []
            for x in rr:
                try:
                    v = float(x[fc])
                except Exception:
                    continue
                if v and abs(v - hz) <= hz * tol:
                    hits.append(float(x[tc]))
            if hits:
                return hits[len(hits) // 2], (hits[0], hits[-1], len(hits))
    return None, None


def cut(src, t, dur, dst, pre=2.5):
    subprocess.run([FF, "-v", "error", "-ss", str(max(0, t - pre)), "-t", str(dur),
                    "-i", str(src), "-ac", "1", "-ar", "44100", str(dst), "-y"],
                   capture_output=True)
    return Path(dst).exists()


def pending(rows, mode):
    out = []
    for r in rows:
        if r.get("performer"):            # 已判非本人/触达音
            continue
        song, tag = str(r.get("song")), str(r.get("tag"))
        if mode in ("low", "all") and r.get("low_hz") \
                and not any(g in str(r.get("a3_final_note") or "") for g in GOOD):
            out.append(("低", song, tag, r.get("low_note"), r.get("low_hz")))
        if mode in ("high", "all") and (r.get("high_hz") or 0) > 1000 \
                and not r.get("high_listen_verified") \
                and "人耳确认" not in str(r.get("a3_final_note") or ""):
            out.append(("高", song, tag, r.get("high_note"), r.get("high_hz")))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--mode", choices=["low", "high", "all"], default="low")
    ap.add_argument("--song")
    ap.add_argument("--hz", type=float)
    ap.add_argument("--tag")
    ap.add_argument("--dur", type=float, default=7.0)
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = load_rows()

    if a.list or (not a.song and not a.tag):
        tgt = pending(rows, a.mode)
        print("待复核 %d 条（mode=%s）" % (len(tgt), a.mode))
        for k, s, tg, n, hz in tgt:
            print("  [%s] %-24s %-5s %7.1f  %s" % (k, s[:24], n, hz, tg[:44]))
        return 0

    # 单条精确定位
    out = Path(a.out) if a.out else OUTBASE / ("定位复核_" + str(a.song)[:16])
    out.mkdir(parents=True, exist_ok=True)
    targets = [r for r in rows if str(r.get("song")) == a.song]
    if a.tag:
        targets = [r for r in targets if str(r.get("tag")) == a.tag]
    if a.hz:
        targets = [r for r in targets
                   if abs((r.get("high_hz") or r.get("high_hz_original") or 0) - a.hz) < 0.6
                   or abs((r.get("low_hz") or 0) - a.hz) < 0.6]
    if not targets:
        print("未匹配到行（注意：同名曲目请用 --tag 精确指定）")
        return 1
    r = targets[0]
    song, tag = str(r["song"]), str(r["tag"])
    hz = a.hz or r.get("high_hz") or r.get("low_hz")
    t, info = time_of(song, tag, hz)
    mix, voc = find_wav(song, tag, MIX_ROOTS), find_voc(song, tag)
    print("曲目 %s ｜ tag %s ｜ 目标 %.1fHz" % (song, tag, hz))
    print("  时刻 t=%s ｜ 命中 %s" % (t, info))
    print("  混音 %s ｜ 人声 %s" % (bool(mix), bool(voc)))
    made = []
    for src, lab in ((voc, "人声轨"), (mix, "混音")):
        if src and t:
            dst = out / ("%s_%.1fHz_t%.1f_%s.wav" % (song[:20], hz, t, lab))
            if cut(src, t, a.dur, dst):
                made.append(dst.name)
    print("  生成 %d 个 → %s" % (len(made), out))
    for m in made:
        print("    ", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
