# -*- coding: utf-8 -*-
"""《歌曲证据总表》——一行一首歌，多源交叉，破解"指数与高光期错开"。

列（每列独立来源，互不依赖）
--------------------------
声学：最低音 / 最低音Hz / 低音区占比(<C3)   ← archive_vocal_albums.json（录音室 72 曲稳定音口径）
现场：演出场次                            ← songs_meta.show_count
      舞台素材数                          ← archive_stage_tour.json（现场层逐素材）
文本：微博/语料提及数                     ← weibo_merged + wx_textmine_corpus（整曲名出现次数）
声音：声音素材提及数                       ← 声音素材清单/转写（有则填）
指数：指数寿命(天) / 中位 / 峰值            ← index_source（权威全量源，current_index>0）

设计原则：**不合成单一分数**，保留每列原值 + 记录"几源有据"，避免把不同口径混合。
用法：python -X utf8 project_b\\build_song_evidence_master.py [--no-text]
产出：data/song_evidence_master.json ＋ E:\\wx\\论文素材_王晰作传\\歌曲证据总表.md
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from index_source import load as load_idx, canon  # noqa: E402

OUT_JSON = SITE / "data" / "song_evidence_master.json"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\歌曲证据总表.md")
TEXT_ROOTS = [Path(r"E:\wx\私有工具\weibo_merged"), Path(r"E:\wx\wx_textmine_corpus")]
VOICE_CANDIDATES = [SITE / "data" / "voice_corpus.json", SITE / "data" / "voice_episodes.json",
                    SITE / "tavern" / "tavern_transcripts.json", SITE / "data" / "archive_voice.json"]


def text_mentions(names: set[str]) -> Counter:
    """统计每个曲名在微博/语料正文里的整名出现次数（长名优先匹配，避免子串误计）。"""
    cnt = Counter()
    pat = {n: re.compile(re.escape(n)) for n in sorted(names, key=len, reverse=True) if len(n) >= 2}
    files = []
    for root in TEXT_ROOTS:
        if root.exists():
            files += [p for p in root.rglob("*.txt") if "content" in p.name or p.suffix == ".txt"]
    files = [p for p in files if p.stat().st_size < 400 * 1024]
    print(f"  文本源：{len(files)} 个文件")
    for i, p in enumerate(files):
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for n, rx in pat.items():
            if n in t and rx.search(t):
                cnt[n] += 1
        if i % 800 == 0:
            print(f"    …已扫 {i}/{len(files)}")
    return cnt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-text", action="store_true", help="跳过文本源扫描（快，用于调试）")
    a = ap.parse_args()

    alb = json.loads((SITE / "data" / "archive_vocal_albums.json").read_text(encoding="utf-8"))
    ac = {}
    for x in alb["songs"]:
        if x.get("title"):
            ac[canon(x["title"])] = x
    meta = json.loads((SITE / "data" / "songs_meta.json").read_text(encoding="utf-8"))["songs"]
    shows, kinds = {}, {}
    for k, v in meta.items():
        cn = canon(re.sub(r"\s+", " ", str((v or {}).get("name") or k)).split("\n")[0])
        shows[cn] = (v or {}).get("show_count") or 0
        kinds[cn] = (v or {}).get("attr") or ""

    # 舞台素材数
    stage = Counter()
    st = json.loads((SITE / "data" / "archive_stage_tour.json").read_text(encoding="utf-8"))
    for r in (st.get("rows") or st.get("materials") or []):
        for key in ("song", "title", "曲目"):
            v = r.get(key)
            if v:
                stage[canon(str(v))] += 1
                break

    # 指数
    df = load_idx()
    good = df.dropna(subset=["current_index"])
    good = good[good["current_index"] > 0]
    idx = {}
    for s, g in good.groupby("canon"):
        vals = g["current_index"]
        idx[s] = {"days": int(g["day"].nunique()), "median": round(float(vals.median()), 1),
                  "peak": float(vals.max()), "first": g["day"].min(), "last": g["day"].max()}

    names = set(ac) | set(shows) | set(idx) | set(stage)
    names = {n for n in names if n and len(n) >= 2}
    print(f"并入曲目（多源并集）：{len(names)} 首")

    men = Counter()
    if not a.no_text:
        men = text_mentions({k for k in names if len(k) >= 2})

    rows = []
    for n in names:
        A = ac.get(n) or {}
        rs = A.get("register_share") or {}
        rows.append({
            "song": n,
            "low_note": A.get("low"), "low_hz": A.get("low_hz"),
            "bass_share": rs.get("low_lt_C3"),
            "show_count": shows.get(n, 0),
            "stage_materials": stage.get(n, 0),
            "text_mentions": men.get(n, 0),
            "idx_days": (idx.get(n) or {}).get("days", 0),
            "idx_median": (idx.get(n) or {}).get("median"),
            "idx_peak": (idx.get(n) or {}).get("peak"),
            "idx_first": (idx.get(n) or {}).get("first"),
        })
    for r in rows:
        r["sources_with_data"] = sum(1 for k in ("low_hz", "show_count", "stage_materials",
                                                 "text_mentions", "idx_days")
                                     if (r.get(k) or 0))
    rows.sort(key=lambda r: (-(r["idx_days"]), -(r["text_mentions"] or 0)))

    payload = {"generated_at": datetime.now().isoformat(timespec="seconds"),
               "n_songs": len(rows),
               "coverage": {"with_acoustic": sum(1 for r in rows if r["low_hz"]),
                            "with_shows": sum(1 for r in rows if r["show_count"]),
                            "with_stage": sum(1 for r in rows if r["stage_materials"]),
                            "with_text": sum(1 for r in rows if r["text_mentions"]),
                            "with_index": sum(1 for r in rows if r["idx_days"])},
               "rows": rows}
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["# 歌曲证据总表（多源交叉）", "",
         f"生成 {datetime.now():%Y-%m-%d %H:%M}｜并入曲目 **{len(rows)}** 首", "",
         "**为什么不合成单一分数**：五个来源口径不同（声学是秒级测量、舞台素材是文件数、",
         "文本是整名出现次数、指数是平台口径），合成一个数会掩盖差异。本表保留原值 + 「几源有据」。", "",
         "## 覆盖情况", "",
         "| 来源 | 有数据曲目数 |", "|---|---|"]
    for k, v in payload["coverage"].items():
        L.append(f"| {k} | {v} |")
    L += ["", "## 明细（按指数寿命降序，取前 80）", "",
          "| 曲目 | 最低音 | Hz | 低音占比 | 演出 | 舞台素材 | 文本提及 | 指数天数 | 指数中位 | 峰值 | 源数 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows[:80]:
        L.append(f"| {r['song'][:18]} | {r['low_note'] or '—'} | {r['low_hz'] or '—'} | "
                 f"{r['bass_share'] if r['bass_share'] is not None else '—'} | {r['show_count']} | "
                 f"{r['stage_materials']} | {r['text_mentions']} | {r['idx_days']} | "
                 f"{r['idx_median'] if r['idx_median'] is not None else '—'} | "
                 f"{r['idx_peak'] if r['idx_peak'] is not None else '—'} | {r['sources_with_data']} |")

    # 多源并看：文本/舞台/演出 三源都强的曲目（不依赖指数）
    strong = [r for r in rows if r["text_mentions"] >= 5 and r["stage_materials"] >= 3]
    strong.sort(key=lambda r: -(r["text_mentions"] * 3 + r["stage_materials"] * 5 + r["show_count"] * 4))
    L += ["", "## 不依赖指数的证据强度榜（文本≥5 且 舞台素材≥3）", "",
          "| 曲目 | 文本提及 | 舞台素材 | 演出场次 | 指数天数 |", "|---|---|---|---|---|"]
    for r in strong[:40]:
        L.append(f"| {r['song'][:18]} | {r['text_mentions']} | {r['stage_materials']} | "
                 f"{r['show_count']} | {r['idx_days']} |")
    L += ["", "## 边界", "",
          "- 文本提及 = 整曲名在微博/语料正文出现次数（同名会互相干扰，长名优先匹配）",
          "- 声学仅录音室曲目；舞台素材来自现场层；指数来自权威全量源（current_index>0）",
          "- **不作因果推断**：本表用于「哪首歌有多源证据支持」，不用于排名或断言因果", ""]
    OUT_MD.write_text("\n".join(L), encoding="utf-8")

    print("\n覆盖：", payload["coverage"])
    print(f"不依赖指数的证据强曲（文本≥5 且 舞台≥3）：{len(strong)} 首")
    print("  Top10:", [r["song"] for r in strong[:10]])
    print(f"\n→ {OUT_JSON}\n→ {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
