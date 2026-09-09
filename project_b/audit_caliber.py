#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""口径审计（单一事实源一致性自检）——每次改数据后跑一次，防止「同一指标多个数」。

设计原则（第一性原理）：
  1. 所有计数必须从**单一事实源**派生：巡演歌单长表（xlsx）→ 场次；
     dashboard/dashboard_data.json → 追踪歌曲；各 manifest → 语义层规模。
  2. 同一指标只允许一个口径；凡「巡演场次」与「全站场次」必须成对出现。
  3. 本脚本只读不写，输出「期望值 vs 实际值」，差异即硬伤。

用法：
  python project_b/audit_caliber.py
  python project_b/audit_caliber.py --setlist <长表.xlsx>
退出码：0=全部一致；1=存在不一致（可用于 CI / 操作中心前置检查）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_SETLIST = r"E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx"
TOUR_RE = re.compile(r"^(一巡|二巡|三巡|四巡|五巡|六巡)")

problems: list[str] = []
notes: list[str] = []


def ok(label: str, expect, actual) -> None:
    flag = "OK  " if expect == actual else "FAIL"
    line = f"[{flag}] {label}: 期望 {expect} / 实际 {actual}"
    print(line)
    if expect != actual:
        problems.append(line)


def info(label: str, value) -> None:
    notes.append(f"{label}: {value}")
    print(f"[info] {label}: {value}")


def truth_from_setlist(path: str) -> dict:
    """从长表派生真值：全站场次 / 巡演场次 / 签唱会等非巡演场次 / 城市数"""
    import pandas as pd

    df = pd.read_excel(path, sheet_name="合并长表")
    df = df[df["曲目"].notna() & (df["曲目"].astype(str).str.strip() != "")].copy()
    # 日期归一化（str/Timestamp 混排会把一场拆成两组）
    df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
    shows = df.groupby(["日期", "场次", "巡次"]).size().reset_index(name="n")
    tours = shows["巡次"].astype(str).str.extract(TOUR_RE)[0]
    tour_mask = tours.notna()
    # 城市归一化：必须复用站点同一口径（generate_tour_index._clean_city），
    # 否则「北京收官」「上海（返场）」会被算成两个城市 → 城市数虚增。
    from generate_tour_index import _clean_city

    cities = {_clean_city(s) for s in shows["场次"].astype(str)}
    cities.discard("")
    return {
        "shows_total": int(len(shows)),
        "shows_tour": int(tour_mask.sum()),
        "shows_other": int((~tour_mask).sum()),
        "cities": len(cities),
        "songs_rows": int(len(df)),
    }


def scan_stale_counts(t: dict) -> list[str]:
    """扫描站点文件里的「N 场」字面量，凡不在 {全站场次, 巡演场次} 且落在场次可疑区间的，报为陈旧口径。

    只扫对外可见/生成物（html/json/txt/md/py），跳过 .git、temp、备份文件。
    """
    good = {t["shows_total"], t["shows_tour"], t["shows_other"]}
    suspect = {"58", "59", "60", "61", "62", "63", "64", "65", "66", "67"}
    pat = re.compile(r"(\d{2})\s*场")
    # 模糊/陈旧的口径措辞（曾出现在首页：覆盖 50+ 城市、累计 60+ 场次）
    vague = re.compile(r"(50\+|60\+)\s*(城市|城|场次|场)")
    skip_dirs = {".git", "temp", "node_modules", "__pycache__", ".venv", "venv"}
    out = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if not f.endswith((".html", ".json", ".txt", ".md", ".py", ".xml", ".js")):
                continue
            if ".bak" in f or f.endswith(".utf8"):
                continue
            p = Path(root) / f
            if p.resolve() == Path(__file__).resolve():
                continue
            try:
                s = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in pat.finditer(s):
                n = int(m.group(1))
                if n in suspect and n not in good:
                    rel = p.relative_to(ROOT)
                    ctx = s[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")
                    out.append(f"陈旧场次口径 {n} 场 @ {rel} … {ctx.strip()} …")
            for m in vague.finditer(s):
                rel = p.relative_to(ROOT)
                ctx = s[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")
                out.append(f"模糊场次口径「{m.group(0)}」 @ {rel} … {ctx.strip()} …（改用口径登记表的准确数字）")
    # 同一文件同一数字只报一次
    seen, uniq = set(), []
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq[:40]


def main() -> None:
    ap = argparse.ArgumentParser(description="口径审计：单一事实源一致性自检")
    ap.add_argument("--setlist", default=DEFAULT_SETLIST)
    args = ap.parse_args()

    print("=" * 68)
    print("口径审计 · 单一事实源一致性自检")
    print("=" * 68)
    t = truth_from_setlist(args.setlist)
    print(f"真值（长表 {Path(args.setlist).name}）：全站 {t['shows_total']} 场 = "
          f"巡演 {t['shows_tour']} 场 + 签唱会等 {t['shows_other']} 场；城市 {t['cities']}")
    print("-" * 68)

    # ---- 1) data/cities.json ----
    cj = json.loads((ROOT / "data" / "cities.json").read_text(encoding="utf-8"))
    rows = [s for node in cj.get("cities", {}).values() for s in node.get("shows", [])]
    uniq = {s["date"] for s in rows}
    ok("cities.json 行数 = 全站场次", t["shows_total"], len(rows))
    ok("cities.json 唯一日期 = 全站场次（无重复行）", t["shows_total"], len(uniq))
    ok("cities.json show_count 字段", t["shows_total"], cj.get("show_count"))
    ok("cities.json city_count 字段", t["cities"], cj.get("city_count"))

    # ---- 2) data/setlists.json ----
    sj = json.loads((ROOT / "data" / "setlists.json").read_text(encoding="utf-8"))
    ok("setlists.json 场次键数", t["shows_total"], len(sj.get("setlists", {})))
    ok("setlists.json show_count 字段", t["shows_total"], sj.get("show_count"))
    missing = uniq - set(sj.get("setlists", {}))
    if missing:
        problems.append(f"[FAIL] setlists.json 缺场次: {sorted(missing)}")
        print(f"[FAIL] setlists.json 缺场次: {sorted(missing)}")

    # ---- 3) entity_index.json ----
    ej = json.loads((ROOT / "entity_index.json").read_text(encoding="utf-8"))
    ei_dates = set()
    for node in ej.get("songs", {}).values():
        for lv in node.get("live", []) or []:
            if lv.get("date"):
                ei_dates.add(lv["date"])
    ok("entity_index.json 场次日期数", t["shows_total"], len(ei_dates))

    # ---- 4) story.html 口径成对 ----
    sp = ROOT / "story.html"
    if sp.exists():
        h = sp.read_text(encoding="utf-8")
        ok("story.html 含巡演场次（59）", True, f"{t['shows_tour']} 场" in h)
        ok("story.html 含全站场次（64）", True, f"{t['shows_total']} 场" in h)
        ok("story.html 无陈旧 60 场口径", True, "60 场" not in h)
        ok("story.html 无陈旧 65 场口径", True, "65 场" not in h)

    # ---- 5) llms.txt 计数（由 generate_llms.py 从 manifest 派生）----
    lp = ROOT / "llms.txt"
    cal = ROOT / "data" / "calibers.json"
    cal_map = {}
    if cal.exists():
        cal_map = {x["id"]: x["value"] for x in json.loads(cal.read_text(encoding="utf-8")).get("calibers", [])}
    if lp.exists():
        llms = lp.read_text(encoding="utf-8")
        m = re.search(r"(\d+)\s*场", llms)
        if m:
            ok("llms.txt 场次", t["shows_total"], int(m.group(1)))
        # llms.txt 的知识库计数必须与口径登记表一致（同一数据、两处展示）
        pairs = [("事实层", "kb_facts"), ("实体层", "kb_entities"), ("关系层", "kb_relations"),
                 ("语义索引", "semantic_docs"), ("问答", "qa_pairs")]
        for label, cid in pairs:
            if cid not in cal_map or cal_map[cid] is None:
                continue
            # 在 llms.txt 中找包含该标签且带数字的片段
            seg = ""
            for line in llms.splitlines():
                if label in line:
                    seg = line
                    break
            nums = [int(x) for x in re.findall(r"(\d{3,6})", seg)]
            if nums:
                ok(f"llms.txt {label} 与口径登记表一致", cal_map[cid], cal_map[cid] if cal_map[cid] in nums else f"未出现（{nums[:4]}）")

    # ---- 6) 语义层 / 知识库规模（信息项，便于跨页核对）----
    for rel, keys in [
        ("kb/manifest.json", ("facts", "entities", "relations")),
        ("semantic/manifest.json", ("events", "phases", "themes")),
    ]:
        p = ROOT / rel
        if p.exists():
            j = json.loads(p.read_text(encoding="utf-8"))
            info(rel, {k: j.get(k) for k in keys if k in j})

    dd = ROOT / "dashboard" / "dashboard_data.json"
    if dd.exists():
        d = json.loads(dd.read_text(encoding="utf-8"))
        info("dashboard 追踪歌曲", d.get("total_songs"))
        info("dashboard 链接数", d.get("tracked_links"))

    # ---- 7) 全站扫描：陈旧场次字面量（59/60/65 等）----
    stale = scan_stale_counts(t)
    if stale:
        for s in stale:
            problems.append(s)
            print(f"[FAIL] {s}")
    else:
        ok("全站无陈旧场次字面量（59/60/65 场）", True, True)

    print("-" * 68)
    if problems:
        print(f"结论：发现 {len(problems)} 处口径不一致 —— 必须修，禁止对外引用。")
        sys.exit(1)
    print("结论：全部一致（单一事实源闭环）。")
    sys.exit(0)


if __name__ == "__main__":
    main()
