#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快照审计：派生结果、快照登记、页面引用、hook 状态四者是否一致。

退出码 1 = 有硬错误。检查项：
  E1 派生结果与当前数据重算不一致
  E2 派生结果的 snapshot_id 未在 snapshots.json 登记
  E3 输入指纹变化但 snapshot_id 未更新（说明数据改了、快照没升）
  E4 派生结果标记为可发布，但页面仍显示旧快照值
  E5 hook 里出现新值但未标记 disabled
"""
from __future__ import annotations

import hashlib
import json
import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALBUMS = ROOT / "data" / "archive_vocal_albums.json"
SNAPS = ROOT / "data" / "snapshots.json"
DERIVED = ROOT / "data" / "derived" / "vibrato_spread.json"
HOOKS = ROOT / "data" / "hooks_pool.json"
PAGES = ["topic-vibrato.html", "series-vibrato.html", "share.html", "insight.html",
         "facts.html", "versions.html", "stage.html", "voice.html", "vocal.html", "skill.html"]


def recompute() -> tuple[float, dict, str]:
    albums = json.loads(ALBUMS.read_text(encoding="utf-8"))
    by: dict[str, list[float]] = {}
    for s in albums.get("songs", []):
        v = s.get("vibrato_hz")
        if v and s.get("album"):
            by.setdefault(s["album"], []).append(float(v))
    med = {a: round(st.median(v), 2) for a, v in by.items()}
    spread = round(max(med.values()) - min(med.values()), 2)
    fp = hashlib.sha256(
        json.dumps({a: sorted(by[a]) for a in sorted(by)}, sort_keys=True).encode()).hexdigest()[:16]
    return spread, med, fp


def main() -> None:
    errors, warns = [], []
    derived = json.loads(DERIVED.read_text(encoding="utf-8"))
    snaps = {s["snapshot_id"] for s in json.loads(SNAPS.read_text(encoding="utf-8"))["snapshots"]}
    spread, med, fp = recompute()

    if abs(spread - derived["value_hz"]) > 1e-9:
        errors.append(f"E1 派生值 {derived['value_hz']} ≠ 重算 {spread}")
    if derived["snapshot_id"] not in snaps:
        errors.append(f"E2 snapshot_id {derived['snapshot_id']} 未登记")
    if fp != derived["input_fingerprint"]:
        errors.append(f"E3 输入指纹 {fp} ≠ 快照记录 {derived['input_fingerprint']}（数据改了但快照未升）")

    # 页面引用检查：release 值永远允许；candidate 值只在研究页且标注「候选」时允许
    rv = (derived.get("release") or {}).get("value_hz")
    cv = (derived.get("candidate") or {}).get("value_hz")
    cand_pub = bool((derived.get("candidate") or {}).get("publishable"))
    for name in PAGES:
        p = ROOT / name
        if not p.exists():
            continue
        txt = re.sub(r"<[^>]+>", " ", p.read_text(encoding="utf-8", errors="ignore"))
        for m in re.finditer(r"0\.(27|39)\s*Hz", txt):
            val = float("0." + m.group(1))
            is_cand = cv is not None and abs(val - cv) < 0.005
            is_rel = rv is not None and abs(val - rv) < 0.005
            if is_cand and not cand_pub:
                ctx = txt[max(0, m.start() - 160): m.end() + 160]
                if name.startswith("share"):
                    errors.append(f"E4 {name} 属于分享出口，无论是否标注「候选」都不得出现 {val}Hz")
                elif "候选" in ctx:
                    warns.append(f"{name} 标注为候选值 {val}Hz（允许，但不得进发布出口）")
                else:
                    errors.append(f"E4 {name} 使用了未达发布条件的新值 {val}Hz 且未标「候选」")
            elif is_cand and cand_pub and is_rel:
                pass
            elif not is_rel and not is_cand:
                warns.append(f"{name} 引用 {val}Hz（既非当前发布值也非候选值）")

    # hook 检查
    if HOOKS.exists():
        s = HOOKS.read_text(encoding="utf-8")
        for m in re.finditer(r"[^\"]{0,40}0\.39\s*Hz[^\"]{0,20}", s):
            frag = m.group(0)
            idx = s.rfind("{", 0, m.start())
            block = s[idx:idx + 600]
            if '"disabled": true' not in block:
                errors.append(f"E5 hook 含新值但未禁用：{frag[:40]}")

    print(f"快照审计｜派生值 {derived['value_hz']}Hz｜重算 {spread}Hz｜状态 {derived['status']}"
          f"｜publishable={derived.get('publishable')}")
    print(f"逐碟中位：{med}")
    if warns:
        print(f"\n[待统一] {len(warns)} 处页面仍用旧值：")
        for w in warns[:10]:
            print("  ·", w)
    if errors:
        print("\n[硬错误]")
        for e in errors:
            print("  ·", e)
    else:
        print("\n快照一致性：通过 ✅")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
