# -*- coding: utf-8 -*-
"""横向对比框架生成器（瘦身 2.0 · 7.2）

目标：在**同一标准**下比较王晰与赵鹏及其他常被宣传「低音」的流行歌手。

纪律（本模块的全部价值都在这里）：
  · 只呈现数据与测量条件，不写主观结论。
  · 条件不匹配的样本必须标注，不得混入。
  · 未测的歌手一律写 null + status=pending，**不填估计值、不填二手说法**。

产出：
  data/comparison_schema.json        控制变量 + 对比维度 + 每维度记录要求
  data/comparison/<歌手>.json         与 archive_vocal.json 同构的逐歌手结构

用法：python -X utf8 project_b/build_comparison.py [--check]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_OUT = os.path.join(ROOT, "data", "comparison_schema.json")
DIR = os.path.join(ROOT, "data", "comparison")

DIMENSIONS = [
    {"key": "lowest_stable_note", "label": "最低稳定音", "unit": "音名 + Hz",
     "must": "过复核门槛（该音符本身 ≥0.2s、HNR ≥5dB），并做谐波列/CREPE 交叉校验"},
    {"key": "lowest_reach_note", "label": "触达音", "unit": "音名 + Hz + 时长",
     "must": "须标时长与引擎；不作能力依据，与稳定音分列"},
    {"key": "dynamic_range_db", "label": "低音区动态范围", "unit": "dB（mf − pp）",
     "must": "同音级聚合，P5/P95 稳健分位；n<3 标 insufficient_sample"},
    {"key": "vibrato_rate_hz", "label": "颤音速率", "unit": "Hz",
     "must": "中位数；须同管线（同一音符切分与估计器）"},
    {"key": "vibrato_extent_cents", "label": "颤音幅度", "unit": "音分", "must": "中位数"},
    {"key": "stability_cents", "label": "音符内稳定性", "unit": "音分", "must": "中位数（越低越稳）"},
    {"key": "span_octaves", "label": "音域跨度", "unit": "八度",
     "must": "逐曲跨度中位数，并单独给最大跨度；不可把「个体曲目跨度」当「音域」"},
    {"key": "studio_vs_live_delta", "label": "现场 vs 录音室差值", "unit": "半音",
     "must": "同曲优先；现场对现场、录音室对录音室"},
]

CONTROLS = [
    "年龄段：优先取 30–40 岁样本（与本项目主口径可比）；超出范围须标注年龄段并单列",
    "同曲目优先：有共同曲目时优先比较共同曲目，避免风格差异混入",
    "语境对齐：现场对现场、录音室对录音室，不跨语境直接比",
    "同管线同口径：demucs htdemucs 人声分离 + 自研 YIN 逐帧 F0（fmin 55 / fmax 1100 / "
    "frame 2048 / hop 512 / sr 22050）+ 稳健过滤；不同管线产出不得混表",
    "素材条件：标明音源（官方音源/现场直拍/综艺音轨）与码率；有损音源须标注",
    "样本量：每维度记录 n（出现次数）与曲目数；n 不足即标 insufficient_sample",
    "地域与语言：注明语种与唱法（流行/美声/通俗），跨唱法比较须标注",
]

SINGERS = [
    {"id": "wangxi", "name": "王晰", "role": "基准（本站主口径）",
     "age_band": "30–40 岁（主口径样本期）", "note": "数据源为本站既有实测，见 archive_vocal.json / archive_vocal_albums.json"},
    {"id": "zhaopeng", "name": "赵鹏", "role": "对照候选（常与王晰并提的低音男声）",
     "age_band": "待标注", "note": "本站尚未测；已登记入 data/analysis_queue.json，待 tools/ 管线跑出结果后回填"},
]


def schema_doc():
    return {
        "schema": "comparison_schema v1",
        "purpose": "在同一标准下比较王晰与常被宣传「低音」的流行歌手；只呈现数据与测量条件，不写主观结论。",
        "discipline": [
            "条件不匹配的样本必须标注，不得混入。",
            "未测歌手写 null + status=pending，不填估计值或二手说法。",
            "外部读数（论坛/媒体/粉丝扒谱）只作档案记录，标注来源与方法状态。",
        ],
        "controls": CONTROLS,
        "dimensions": DIMENSIONS,
        "singers": SINGERS,
        "output": "data/comparison/<歌手id>.json，结构与 data/archive_vocal.json 同构",
    }


def singer_doc(s):
    dims = {}
    for d in DIMENSIONS:
        dims[d["key"]] = {
            "value": None, "unit": d["unit"], "n": 0, "songs": [],
            "source": "", "confidence": "", "status": "pending",
            "note": d["must"],
        }
    if s["id"] == "wangxi":
        alb = json.load(io.open(os.path.join(ROOT, "data", "archive_vocal_albums.json"), encoding="utf-8"))
        voc = json.load(io.open(os.path.join(ROOT, "data", "archive_vocal.json"), encoding="utf-8"))
        sm = alb["summary"]
        dr = json.load(io.open(os.path.join(ROOT, "data", "archive_dynamic_range.json"), encoding="utf-8"))
        b1 = next((c for c in dr["classes"] if c["note"] == "B1"), {})
        dims["lowest_stable_note"].update({
            "value": f'{sm["lowest"]["note"]} {sm["lowest"]["hz"]}Hz',
            "n": sm["songs"], "songs": [sm["lowest"]["song"]],
            "source": "data/archive_vocal_albums.json", "confidence": "主口径（全量录音室）",
            "status": "measured"})
        dims["dynamic_range_db"].update({
            "value": (b1.get("dynamic_range_db") or {}).get("range_db"),
            "n": b1.get("n", 0), "songs": b1.get("songs") or [],
            "source": "data/archive_dynamic_range.json（B1 音级）",
            "confidence": "低音带读数聚合", "status": (b1.get("dynamic_range_db") or {}).get("status", "pending")})
        dims["vibrato_rate_hz"].update({
            "value": sm["vibrato_rate_hz_median"], "n": sm["songs"],
            "source": "data/archive_vocal_albums.json", "confidence": "中位（录音室）", "status": "measured"})
        dims["vibrato_extent_cents"].update({
            "value": sm["vibrato_extent_cents_median"], "n": sm["songs"],
            "source": "data/archive_vocal_albums.json", "confidence": "中位（录音室）", "status": "measured"})
        dims["stability_cents"].update({
            "value": sm["stability_cents_median"], "n": sm["songs"],
            "source": "data/archive_vocal_albums.json", "confidence": "中位（录音室）", "status": "measured"})
        dims["span_octaves"].update({
            "value": sm["span_median_octaves"], "n": sm["songs"],
            "source": "data/archive_vocal_albums.json",
            "confidence": f'逐曲跨度中位；最大 {sm["span_max_octaves"]} 个八度', "status": "measured"})
        dims["lowest_reach_note"].update({
            "value": None,
            "n": len([x for x in voc["songs"] if x.get("reach_note")]),
            "songs": [x["name"] for x in voc["songs"] if x.get("reach_note")],
            "source": "data/archive_vocal.json（各曲 reach_* 字段）",
            "confidence": "触达音口径（展示但不作能力依据）", "status": "measured_per_song",
            "note": "触达音为逐曲字段而非单一值：请见 data/archive_vocal.json 每曲 reach_note/reach_hz/reach_duration；"
                    "仅展示，不作能力依据"})
        dims["studio_vs_live_delta"].update({
            "value": None, "n": 11,
            "source": "data/archive_context_compare.json",
            "confidence": "同曲对照 + 组间检验（11 项指标，含 p 值）",
            "status": "measured_per_metric",
            "note": "为 11 项指标的对照集合而非单一值：见 data/archive_context_compare.json"})

    return {
        "schema": "comparison_singer v1",
        "id": s["id"], "name": s["name"], "role": s["role"],
        "age_band": s["age_band"], "note": s["note"],
        "pipeline": ("demucs htdemucs 人声分离 + 自研 numpy YIN 逐帧 F0"
                     "（fmin 55 / fmax 1100 / frame 2048 / hop 512 / sr 22050）+ 稳健过滤"),
        "dimensions": dims,
        "caveats": [
            "不同歌手的素材可得性不同（音源/码率/语境），跨歌手比较必须先对齐语境。",
            "本表不排名、不评优劣；只提供同一标准下的数值与条件。",
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    os.makedirs(DIR, exist_ok=True)
    targets = [(SCHEMA_OUT, json.dumps(schema_doc(), ensure_ascii=False, indent=1))]
    for s in SINGERS:
        targets.append((os.path.join(DIR, s["id"] + ".json"),
                        json.dumps(singer_doc(s), ensure_ascii=False, indent=1)))
    drift = []
    for path, out in targets:
        old = io.open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if old.strip() == out.strip():
            print("  %-40s 已一致 ✅" % os.path.relpath(path, ROOT))
            continue
        drift.append(os.path.relpath(path, ROOT))
        if args.check:
            print("  %-40s 需更新" % os.path.relpath(path, ROOT))
        else:
            io.open(path, "w", encoding="utf-8").write(out)
            print("  %-40s 已生成" % os.path.relpath(path, ROOT))
    if args.check and drift:
        print("\n[FAIL] %d 个文件漂移" % len(drift))
        return 1
    print("\n[OK] 横向对比框架：%d 个文件" % len(targets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
