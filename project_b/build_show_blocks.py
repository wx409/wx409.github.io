# -*- coding: utf-8 -*-
"""生成本场「块级」可引用数据集：data/show_blocks/沉响与长歌_20261009.json

设计原则（2026-10-10 与用户确认）：
  · **只写可引用的部分**——分区时间预算、每块「谁在唱」、块级**分布型**指标（F0 中位/
    稳定性/音准/颤音/密度/低频占比/HNR）与其样本量 n；
  · **断言不写**——极值音（最低/最高稳定音）及其歌手归属一律不写入（见 calibers 对应口径）；
  · 不含本地绝对路径（公开 JSON 纪律）。

输入（本地过程稿，不入库）：
  E:\\wx\\论文素材_王晰作传\\原始材料\\沉响与长歌_20261009_声学分析_v4.json
  D:\\wx409.github.io\\temp\\audience_analysis\\2026-10-09_北京.json（已按本场关键词收紧）
输出：
  D:\\wx409.github.io\\data\\show_blocks\\沉响与长歌_20261009.json
用法：python -X utf8 project_b\\build_show_blocks.py
"""
from __future__ import annotations

import io
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(r"D:\wx409.github.io")
V4 = Path(r"E:\wx\论文素材_王晰作传\原始材料\沉响与长歌_20261009_声学分析_v4.json")
FB = ROOT / "temp" / "audience_analysis" / "2026-10-09_北京.json"
OUT_DIR = ROOT / "data" / "show_blocks"
OUT = OUT_DIR / "沉响与长歌_20261009.json"

# 曲名状态：只有人耳/直拍确证者才写曲名，其余 `待核`（不得猜）
NAME_STATUS = {
    5: {"song": "敕勒歌", "status": "已确证", "evidence": "用户口述+人耳（1240 王晰）+单曲直拍 BV1EZph65Ebh 对齐边际 +0.403（全场最强）"},
    6: {"song": "乌兰巴托的夜", "status": "已确证", "evidence": "同一直拍另一段（蒙语，人耳 1380 傲日）+ 块紧接 b05"},
    11: {"song": "英文串烧（Smoke Gets in Your Eyes / Moon River / Love Me Tender）", "status": "已确证",
         "evidence": "人耳确认（3805 王晰）+ 微博/直拍标题均列该三首"},
    13: {"song": "民族串烧（送亲歌 / 小草 / 莫合茹）", "status": "已确证", "evidence": "人耳确认（4105 傲日）+ 用户更正曲名"},
}


def mmss(t: float) -> str:
    return f"{int(t) // 60:02d}:{int(t) % 60:02d}"


def main() -> int:
    v4 = json.loads(V4.read_text(encoding="utf-8"))
    fb = json.loads(FB.read_text(encoding="utf-8"))
    blocks = []
    for b in v4["blocks"]:
        m = b["strict"]
        nm = NAME_STATUS.get(b["no"], {})
        blocks.append({
            "no": b["no"],
            "who_confirmed": b["who"],                 # 人耳确认「该段有此歌手人声」
            "t0": b["t0"], "t1": b["t1"], "dur_s": b["dur"],
            "t0_hms": mmss(b["t0"]), "t1_hms": mmss(b["t1"]),
            "ear_anchor_count": b["n_anchor"],
            "separation_qc": (b["qc"].split("（")[0] if b.get("qc") else "—"),
            "passthru_frac": b.get("passthru"),
            "in_stats": bool(not b["qc"].startswith("⚠") and b["dur"] >= 60),
            "song": nm.get("song", "待核"),
            "song_status": nm.get("status", "待核"),
            "song_evidence": nm.get("evidence", ""),
            # ── 仅分布型指标（不含极值）──
            "f0_median_note": m["f0_median_note"], "f0_median_midi": m["f0_median_midi"],
            "stability_cents_median": m["stability_cents_median"],
            "intonation_cents_median": m["intonation_cents_median"],
            "vibrato_hz_median": m["vibrato_rate_hz_median"],
            "vibrato_cents_median": m["vibrato_extent_cents_median"],
            "density_per_s": m["density_per_s"],
            "low_ratio_db": m["low_ratio_db"],
            "hnr_db_median": m["hnr_db_median"],
            "notes_kept": m["notes_kept"], "notes_total": m["notes_total"],
        })
    payload = {
        "schema": 1,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "show": {"name": "《沉响与长歌》演唱会 北京站", "date": "2026-10-09",
                 "venue": "北京天桥艺术中心·大剧场", "organizer": "中国东方演艺集团",
                 "cast": "王晰 × 傲日其愣", "note": "王晰为制作人之一兼主演"},
        "layer": "双人场次块级（非能力上限口径）",
        "policy": {
            "what_is_this": "本场为**双人场次**：18 个演唱块中每块只记「人耳确认该段有谁的人声」，"
                            "指标为该块**人声轨的分布型统计**（含伴奏/和声残留）。",
            "not_included": ["最低/最高稳定音（极值音）及其歌手归属",
                             "音域跨度主张（依赖极值读数）",
                             "任何「某人唱到 X Hz」的表述"],
            "why": "手机实录 + demucs 分离条件下，极值音的歌手归属不可判定"
                   "（见 data/calibers.md「场次音频切分与歌手归属」）",
            "median": "statistics.median",
            "gate": "严格门 HNR≥8dB、时长≥0.20s、强度≥音符中位−12dB；分离质量 QC 告警块不进统计",
        },
        "budget": {k: v for k, v in v4["budget"].items() if k != "overlap"},
        "budget_extra": {"overlap_dur_s": v4["budget"]["overlap"].get("overlap_dur", 0),
                         "audience_sing_s": v4["budget"]["audience"]["dur"],
                         "whistle_s": v4["budget"]["whistle"]["dur"],
                         "undetermined_s": v4["budget"]["undetermined"]},
        "n_in_stats": v4["n_used"],
        "blocks": blocks,
        "block_medians": {
            who: {k: v for k, v in v4["comparison"].items()} for who in ["王晰", "傲日"]
        },
        "comparison": v4["comparison"],
        "feedback": {
            "source": "temp/audience_analysis/2026-10-09_北京.json（已按本场关键词收紧）",
            "total": fb["stats"]["total"], "platforms": fb["stats"]["platforms"],
            "dimensions": fb["stats"]["dimensions"], "sentiment": fb["stats"]["sentiment"],
            "song_mentions": fb["stats"]["song_top"][:8],
            "filter": fb["stats"].get("filter", {}),
            "filter_note": (lambda f: (
                f"聚合池 {f.get('pool_total')} 条 → 保留 {f.get('kept_total')} 条；"
                f"剔除 {f.get('dropped_total')} 条（原因："
                + "、".join(f"{k} {v}" for k, v in (f.get("dropped_reasons") or {}).items()) + "）"
            ))(fb["stats"].get("filter", {})),
            "caveat": ("本批为「本场关键词收紧」后的结果：必须命中剧名/场馆/日期之一且含主体词，"
                       "命中他场反证词且无强信号者剔除；旧的两个未收紧批次已备份"
                       "（*_旧批次_未收紧.*、*_v1.*）可回溯。"
                       "说明：曲目榜含少量非歌曲词（如节目名）属既有分析器词表问题，读榜时需人工剔除。"),
        },
        "provenance": {"acoustic_md": "原始材料/沉响与长歌_20261009_声学分析_v4.md（本地过程稿）",
                       "method_doc": "docs/场次声学切分与归属方法论_20261010.md",
                       "caliber": "场次音频切分与歌手归属"},
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    n_ok = sum(1 for b in blocks if b["in_stats"])
    n_named = sum(1 for b in blocks if b["song_status"] == "已确证")
    print(f"[ok] {OUT}")
    print(f"  块 {len(blocks)}（进统计 {n_ok}）｜已确证曲名 {n_named}｜待核 {len(blocks) - n_named}")
    print(f"  演唱 {payload['budget']['sing_total']}s/{payload['budget']['total']}s"
          f"（{payload['budget']['sing_pct']}%）｜反馈 {payload['feedback']['total']} 条")
    txt = OUT.read_text(encoding="utf-8")
    assert "E:\\" not in txt and "D:\\" not in txt, "公开 JSON 不得含本地绝对路径"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
