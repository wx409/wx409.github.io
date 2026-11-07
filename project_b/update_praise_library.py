#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动更新链：把声学研究的新发现，按「人话」追加进社媒传播灵感库。

工作方式
  · 读站内几个数据文件，算出「值得写的一条」：新纪录、新曲目、口径变化、里程碑
  · 与上次运行的状态比对（data/praise_library_state.json），**只写新的**
  · 追加到目标文件末尾的「自动追加」区，日期分段，一条一段，直接可发
  · 没有新东西就什么都不写（幂等）

用法
  python -X utf8 project_b\\update_praise_library.py            # 有新增才写
  python -X utf8 project_b\\update_praise_library.py --dry      # 只打印
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = Path(r"E:\wx\论文素材_王晰作传\社媒传播灵感库_王晰.md")
STATE = ROOT / "data" / "praise_library_state.json"
MARK = "<!-- AUTO:APPEND:START -->"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load(rel, default=None):
    p = ROOT / rel
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def hz_round(v):
    return round(float(v), 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--seed", action="store_true", help="只写状态、不追加")
    args = ap.parse_args()

    alb = load("data/archive_vocal_albums.json")
    tour = load("data/archive_stage_tour.json")
    apr = load("data/approach_all.json")
    claims = load("data/citable_claims.json")
    var = load("data/variance_bootstrap.json")
    dash = load("dashboard/dashboard_data.json")

    songs = alb.get("songs") or []
    low5 = [s for s in songs if s.get("low_hz")]
    b1 = sorted([s for s in low5 if s["low_hz"] < 62.0], key=lambda s: s["low_hz"])
    min_song = b1[0] if b1 else None
    n_mat = (tour.get("summary") or {}).get("n_materials") or 0
    n_ver = (tour.get("summary") or {}).get("n_verified") or 0
    dist = apr.get("distribution") or {}
    tot = sum(dist.values()) or 1
    direct_pct = round(100 * dist.get("direct", 0) / tot, 1)
    claim_ids = sorted(c.get("id", "") for c in (claims.get("claims") or []))

    state = load("data/praise_library_state.json") if STATE.exists() else {}
    old = {
        "b1": state.get("b1") or [],
        "min_hz": state.get("min_hz"),
        "n_mat": state.get("n_mat") or 0,
        "direct_pct": state.get("direct_pct"),
        "claims": state.get("claims") or [],
        "releases": state.get("releases") or [],
        "tours": state.get("tours") or [],
        "last_append": state.get("last_append"),
    }

    if args.seed:
        STATE.write_text(json.dumps({
            "b1": [s.get("title") for s in b1],
            "min_hz": min_song["low_hz"] if min_song else None,
            "n_mat": n_mat, "direct_pct": direct_pct, "claims": claim_ids,
            "last_append": state.get("last_append"),
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print("状态已初始化（不追加）")
        return 0

    insights = []

    # ① 新出现 B1 级曲目
    new_b1 = [s for s in b1 if s.get("title") not in old["b1"]]
    for s in new_b1:
        insights.append(
            "**又一首唱到 B1 的歌：《%s》（%s）。** 最低 %s，%.1f 赫兹。到今天，72 首录音室作品里有 %d 首在这个音区。"
            % (s.get("title"), s.get("album"), s.get("low"), s["low_hz"], len(b1)))

    # ② 最低音纪录
    if min_song and (old["min_hz"] is None or min_song["low_hz"] < float(old["min_hz"]) - 0.05):
        insights.append(
            "**最低音纪录更新：《%s》唱到了 %.1f 赫兹（%s）。** 比男低音的及格线 Low C（65.4）还低 %.1f 个半音。"
            % (min_song.get("title"), min_song["low_hz"], min_song.get("low"),
               (65.4 - min_song["low_hz"]) / 1.0 and round(12 * __import__("math").log2(65.4 / min_song["low_hz"]), 1)))

    # ③ 素材量里程碑（每 50 条一次）
    if n_mat >= old["n_mat"] + 50:
        insights.append(
            "**现场素材破 %d 条。** 其中 %d 条过了复核门槛；剩下的是待判、不可复核或已被否决——都留在台账里。"
            % (n_mat // 50 * 50, n_ver))

    # ④ 进入方式变化（≥2 个百分点）
    if old["direct_pct"] is not None and abs(direct_pct - float(old["direct_pct"])) >= 2:
        trend = "更常直接站在那个音上" if direct_pct > float(old["direct_pct"]) else "更多用滑音走进去"
        insights.append(
            "**低音的进入方式变了：** 直接咬住占 %.1f%%（上次 %s%%）。素材一多，这个数会动——现在看，他越来越%s。"
            % (direct_pct, old["direct_pct"], trend))

    # ⑤ 新增可引用句
    new_claims = [c for c in (claims.get("claims") or []) if c.get("id") not in old["claims"] and c.get("sentence")]
    for c in new_claims[:3]:
        insights.append("**新记录：** %s" % (c.get("sentence") or "").strip())

    # ⑥ 新歌发行 / 新演出（首次运行只登记，不追加）
    rel_now = [str(x[1]) for x in (dash.get("release_events") or []) if len(x) > 1]
    tour_now = [str(x[1]) for x in (dash.get("tour_events") or []) if len(x) > 1]
    first_time = not (state.get("releases") or state.get("tours"))
    if not first_time:
        for t in rel_now:
            if t not in old["releases"]:
                insights.append("**新歌上线：%s。** 发行之后通常两三天内能在指数上看到动静，"
                                "值得盯一下它有没有把整个曲目池带起来。" % t)
        for t in tour_now:
            if t not in old["tours"]:
                insights.append("**新演出登记：%s。** 现场的低声区是最好听的证据，"
                                "等这批素材测完，可以补一句「这场他又唱到哪」。" % t)

    if first_time:
        STATE.write_text(json.dumps({
            "b1": [x.get("title") for x in b1],
            "min_hz": min_song["low_hz"] if min_song else None,
            "n_mat": n_mat, "direct_pct": direct_pct, "claims": claim_ids,
            "releases": rel_now, "tours": tour_now,
            "last_append": state.get("last_append"),
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print("首次登记：发行 %d 条、巡演 %d 条，未追加" % (len(rel_now), len(tour_now)))
        return 0

    if not insights:
        print("没有新发现，未写入")
        return 0

    # 只在有新内容时才更新状态
    block = ["", "## 自动追加（%s）" % date.today().isoformat(), ""]
    for i, text in enumerate(insights, 1):
        block.append("%d. %s" % (i, text))
    block.append("")
    body = "\n".join(block)

    print("本次新增 %d 条：" % len(insights))
    for t in insights:
        print("  -", t[:88])

    if not args.dry:
        text = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if MARK not in text:
            text = text.rstrip() + "\n\n" + MARK + "\n"
        head, tail = text.split(MARK, 1)
        new = head + MARK + "\n" + body + tail
        TARGET.write_text(new.rstrip() + "\n", encoding="utf-8", newline="")
        STATE.write_text(json.dumps({
            "b1": [s.get("title") for s in b1],
            "min_hz": min_song["low_hz"] if min_song else None,
            "n_mat": n_mat,
            "direct_pct": direct_pct,
            "claims": claim_ids,
            "last_append": date.today().isoformat(),
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print("已追加到", TARGET)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
