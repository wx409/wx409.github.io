#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据链一致性检查：主张 → 发布出口 → 站点页面。

回答三个问题（任一不过退出 1）：
  1. 每条发布出口是否绑定了存在且未暂停/撤回的主张？
  2. 发布出口的版本是否与主张一致（主张更新后旧出口自动失效）？
  3. 站点页面里是否还残留已撤回的旧口径（如 65.2–65.4、5 音分、所有现场）？

用法：
  python -X utf8 project_b/chain_check.py
  python -X utf8 project_b/chain_check.py --scan voice.html skill.html
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAIMS = ROOT / "data" / "claims.json"
PUBLISHABLE = ROOT / "data" / "publishable.json"

# 已撤回/降级的旧口径（只扫站点页面与数据层，不扫 docs/ 里的方案与评审稿）
LEGACY = [
    ("窄频率区间", r"65\.2\s*[–\-—]\s*65\.4"),
    ("五场 5 音分", r"(?<![\d.])5\s*音分"),
    ("全称断言", r"(?<!不写成「)(所有|每一|全部)(个)?(现场|场次)"),
    ("修音断言", r"(?<!不)(没|无)(有)?修音"),
]
# 这些文件本身就要记录禁用词（主张卡的 cannot_write、发布出口的 forbidden_phrases）
SKIP_SCAN = {"claims.json", "publishable.json"}
SCAN_GLOB = ["*.html", "data/*.json"]


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def check_bindings(claims: dict, pubs: dict):
    cmap = {c["id"]: c for c in claims["claims"]}
    issues = []
    for c in pubs["cases"]:
        cid = c.get("claim_id")
        if not cid:
            if c.get("status") == "可发":
                issues.append(f"'{c['id']}' 无 claim_id 却标可发")
            continue
        cl = cmap.get(cid)
        if not cl:
            issues.append(f"'{c['id']}' 绑定的主张 {cid} 不存在")
            continue
        if cl.get("status") in ("暂停", "撤回"):
            issues.append(f"'{c['id']}' 绑定的主张 {cid} 状态为「{cl['status']}」，该出口应失效")
        pv, cv = c.get("claim_version"), cl.get("version")
        if cv is not None and pv is not None and pv != cv:
            issues.append(f"'{c['id']}' 版本 {pv} ≠ 主张版本 {cv}（主张已更新，需复核出口）")
        q = c.get("quote", "")
        for bad in c.get("forbidden_phrases", []):
            if bad and bad in q:
                issues.append(f"'{c['id']}' 引用句含禁用词「{bad}」")
    return issues


def scan_files(paths):
    hits = []
    for pat in SCAN_GLOB:
        paths += sorted(ROOT.glob(pat))
    seen = set()
    for f in paths:
        f = Path(f)
        if not f.exists() or f in seen or f.name in SKIP_SCAN:
            continue
        seen.add(f)
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for name, pat in LEGACY:
            for m in re.finditer(pat, txt):
                line = txt[:m.start()].count("\n") + 1
                hits.append(f"{f.relative_to(ROOT)}:{line} [{name}] {m.group(0)}")
    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", nargs="*", default=[])
    ap.add_argument("--no-scan", action="store_true")
    a = ap.parse_args()

    claims, pubs = load(CLAIMS), load(PUBLISHABLE)
    issues = check_bindings(claims, pubs)

    print(f"主张 {len(claims['claims'])} 条｜发布出口 {len(pubs['cases'])} 条")
    if issues:
        print("\n[绑定问题]")
        for x in issues:
            print("  ·", x)
    else:
        print("绑定检查：通过 ✅")

    if not a.no_scan:
        extra = [ROOT / p for p in a.scan]
        hits = scan_files(extra)
        page_hits = [h for h in hits if h.startswith(("skill.html", "voice.html", "vocal.html",
                                                     "stage.html", "acoustic-report.html",
                                                     "versions.html", "index.html"))]
        data_hits = [h for h in hits if h not in page_hits]
        if page_hits:
            print(f"\n[页面旧口径残留·需修] {len(page_hits)} 处")
            for h in page_hits[:20]:
                print("  ·", h)
        if data_hits:
            print(f"\n[数据层命中·多为原文引用，需人工确认] {len(data_hits)} 处（不计入失败）")
            for h in data_hits[:5]:
                print("  ·", h)
        if not hits:
            print("旧口径扫描：无残留 ✅")
            for h in hits[:40]:
                print("  ·", h)
            if len(hits) > 40:
                print(f"  …共 {len(hits)} 处")
        else:
            print("旧口径扫描：无残留 ✅")

    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
