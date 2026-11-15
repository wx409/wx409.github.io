#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查询词缺口分析：拿 Bing 后台真实查询词，比对站内覆盖度，输出「高曝光 × 无覆盖」清单。

判定：
  · 每个查询词按「曝光」加权去重；
  · 站内语料 = 全部页面 title + meta description + qa_spec 问题 + 金句；
  · 覆盖分 = 查询词有效片段（≥2 字）在语料中出现的比例（0–1）。
输出：analysis/citeprobe/query_gaps_YYYY-MM-DD.md
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
sys.path.insert(0, str(ROOT / "project_b"))
from bing_wmt import call, load  # noqa: E402

STOP = set("王晰 的 了 是 吗 怎么 什么 哪些 多少 一个 有 没有".split())


def tokens(q: str):
    q = q.strip()
    parts = re.split(r"[\s，,。？！?]+", q)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # 中文长串按 2-3 字滑窗切，英文按词
        if re.search(r"[\u4e00-\u9fff]", p):
            if len(p) <= 4:
                out.append(p)
            else:
                for i in range(len(p) - 1):
                    out.append(p[i:i + 2])
        else:
            out.append(p.lower())
    return [t for t in out if t not in STOP and len(t) >= 2]


def main() -> int:
    key, site = load()
    qs = call("GetQueryStats", key, siteUrl=site)
    rows = qs.get("d") or []
    agg = defaultdict(lambda: [0, 0])  # q -> [imp, clicks]
    for r in rows:
        q = (r.get("Query") or "").strip()
        if not q:
            continue
        agg[q][0] += int(r.get("Impressions") or 0)
        agg[q][1] += int(r.get("Clicks") or 0)

    # 站内语料
    corpus = []
    for p in ROOT.rglob("*.html"):
        if any(x in p.parts for x in (".git", "temp", "data", "docs", "project_b", "tools", "templates")):
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"<title>(.*?)</title>", s, re.S | re.I)
        d = re.search(r'name=["\']description["\'][^>]*content=["\'](.*?)["\']', s, re.S | re.I)
        if m:
            corpus.append(m.group(1))
        if d:
            corpus.append(d.group(1))
    try:
        spec = json.loads((ROOT / "data" / "qa_spec.json").read_text(encoding="utf-8"))
        corpus += [i.get("q", "") + " " + i.get("a", "")[:200] for i in spec.get("items", [])]
    except Exception:
        pass
    try:
        cit = json.loads((ROOT / "data" / "tavern_citable.json").read_text(encoding="utf-8"))
        corpus += [i.get("quote", "") for i in cit.get("items", [])]
    except Exception:
        pass
    text = "\n".join(corpus).lower()

    scored = []
    for q, (imp, clk) in agg.items():
        ts = tokens(q)
        if not ts:
            continue
        hit = sum(1 for t in ts if t.lower() in text)
        cov = hit / len(ts)
        scored.append((imp, q, cov, clk))

    scored.sort(key=lambda x: (-x[0], x[2]))
    gaps = [s for s in scored if s[2] < 0.6][:25]
    covered = [s for s in scored if s[2] >= 0.6][:10]

    lines = [f"# Bing 查询词缺口分析 · {datetime.now().strftime('%Y-%m-%d %H:%M')}", "",
             f"后台真实查询词 **{len(agg)}** 个（去重后）；曝光合计 **{sum(v[0] for v in agg.values())}**；"
             f"点击合计 **{sum(v[1] for v in agg.values())}**。", "",
             "## 高曝光但站内覆盖不足（优先补）", "",
             "| 曝光 | 查询词 | 覆盖度 | 点击 |", "|---|---|---|---|"]
    for imp, q, cov, clk in gaps:
        lines.append(f"| {imp} | {q} | {cov:.0%} | {clk} |")
    lines += ["", "## 已覆盖良好（保持）", "", "| 曝光 | 查询词 | 覆盖度 |", "|---|---|---|"]
    for imp, q, cov, clk in covered:
        lines.append(f"| {imp} | {q} | {cov:.0%} |")

    out = ROOT / "analysis" / "citeprobe" / f"query_gaps_{datetime.now().strftime('%Y%m%d')}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:26]))
    print("\n→", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
