#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把站内最新结论同步进「社媒传播灵感库」（E:\\wx\\论文素材_王晰作传\\社媒传播灵感库_王晰.md）。

只改写文件里 AUTO:CLAIMS 标记之间的区域，手写区一字不动。
每次有新的可引用句/新结论，跑一次本脚本即可。

用法：python -X utf8 project_b\\sync_praise_library.py [--check]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = Path(r"E:\wx\论文素材_王晰作传\社媒传播灵感库_王晰.md")
CLAIMS = ROOT / "data" / "citable_claims.json"
APPROACH = ROOT / "data" / "approach_all.json"
VARIANCE = ROOT / "data" / "variance_bootstrap.json"

START = "<!-- AUTO:CLAIMS:START -->"
END = "<!-- AUTO:CLAIMS:END -->"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def build_block() -> str:
    lines = []
    try:
        d = json.loads(CLAIMS.read_text(encoding="utf-8"))
    except Exception:
        return "(可引用句数据缺失)\n"
    lines.append("> 生成时间：%s ｜ 口径：%s" % (datetime.now().strftime("%Y-%m-%d %H:%M"),
                                                d.get("caliber", "")))
    lines.append("")
    claims = [c for c in (d.get("claims") or []) if c.get("sentence")]
    # 按类型分组
    groups = [("录音室", [c for c in claims if str(c.get("id", "")).startswith("studio-")]),
              ("现场", [c for c in claims if str(c.get("id", "")).startswith("stage-")]),
              ("直接咬住（direct）", [c for c in claims if str(c.get("id", "")).startswith("direct-")]),
              ("同台对照", [c for c in claims if str(c.get("id", "")).startswith("duet-")])]
    for name, items in groups:
        if not items:
            continue
        lines.append("### %s（%d 条）" % (name, len(items)))
        lines.append("")
        lines.append("| 曲目 | 版本 | 时间戳 | 可引用的一句话 |")
        lines.append("|---|---|---|---|")
        for c in items:
            lines.append("| %s | %s | %s | %s |" % (
                str(c.get("song") or "—").replace("|", "/"),
                str(c.get("version") or "—").replace("|", "/"),
                str(c.get("timestamp") or "—"),
                str(c.get("sentence") or "").replace("|", "/").replace("\n", " ")))
        lines.append("")

    # 概览数字
    try:
        ap = json.loads(APPROACH.read_text(encoding="utf-8"))
        dist = ap.get("distribution") or {}
        n = ap.get("n_files") or 0
        if dist:
            lines.append("### 到达方式概览（%d 个逐帧文件）" % n)
            lines.append("")
            lines.append("| 方式 | 占比 |")
            lines.append("|---|---|")
            for k, lab in (("direct", "直接咬住"), ("slide", "滑入"), ("jump", "跳进"), ("head", "段落起点")):
                if k in dist:
                    lines.append("| %s | %.1f%% |" % (lab, 100 * dist[k] / max(1, sum(dist.values()))))
            lines.append("")
    except Exception:
        pass

    try:
        v = json.loads(VARIANCE.read_text(encoding="utf-8"))
        m = (v.get("metrics") or {})
        if m:
            lines.append("### 状态 vs 特质（方差分解）")
            lines.append("")
            lines.append("| 指标 | 场次解释率 | 95%CI | 判读 |")
            lines.append("|---|---|---|---|")
            for k, item in m.items():
                sh = item.get("show") or {}
                if sh.get("icc_pct") is None:
                    continue
                lines.append("| %s | %.1f%% | [%s, %s] | %s |" % (
                    item.get("label", k), sh["icc_pct"],
                    sh.get("ci95", ["—", "—"])[0], sh.get("ci95", ["—", "—"])[1],
                    sh.get("verdict", "")))
            lines.append("")
    except Exception:
        pass
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not TARGET.exists():
        print("目标文件不存在：", TARGET)
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print("找不到 AUTO 标记，请先补标记")
        return 1
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    new = head + START + "\n" + build_block() + END + tail
    if new == text:
        print("已是最新")
        return 0
    if args.check:
        print("需要更新（--check）")
        return 1
    TARGET.write_text(new, encoding="utf-8", newline="")
    print("已同步：", TARGET)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
