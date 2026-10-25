#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""versions 矩阵一致性审计：纳入+排除=总数、全站合计=102、待判不进中位、主张绑定有效。"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LV = ROOT / "data" / "live_versions.json"
CL = ROOT / "data" / "claims.json"
MAP = ROOT / "data" / "song_claims.json"


def main() -> None:
    lv = json.loads(LV.read_text(encoding="utf-8"))
    claims = {c["id"]: c for c in json.loads(CL.read_text(encoding="utf-8"))["claims"]}
    mapping = json.loads(MAP.read_text(encoding="utf-8"))["mapping"]
    errors, warns = [], []

    total_v = total_incl = total_exc = total_pend = 0
    for s in lv["songs"]:
        song = s["song"]
        total = len(s["versions"])
        pend = sum(1 for v in s["versions"] if v.get("state") == "pending")
        ok = [v["low_hz"] for v in s["versions"] if v.get("state") == "ok" and v.get("low_hz")]
        rest = total - len(ok)
        total_v += total
        total_incl += len(ok)
        total_exc += rest
        total_pend += pend

        cid = mapping.get(song)
        if not cid or cid not in claims:
            errors.append(f"{song}：缺少有效主张绑定")
            continue
        sc = claims[cid].get("scope") or {}
        if sc.get("total_versions") != total:
            errors.append(f"{song}：主张总数 {sc.get('total_versions')} ≠ 实际 {total}")
        if sc.get("included", 0) + sc.get("excluded", 0) != total:
            errors.append(f"{song}：纳入 {sc.get('included')} + 排除 {sc.get('excluded')} ≠ 总数 {total}")
        if sc.get("excluded") != rest:
            errors.append(f"{song}：主张排除 {sc.get('excluded')} ≠ 实际未纳入 {rest}")

        if ok:
            med = round(st.median(ok), 2)
            if s.get("low_median") is not None and abs(med - s["low_median"]) > 0.01:
                errors.append(f"{song}：重算中位 {med} ≠ 页面 {s['low_median']}（待判可能进了统计）")
        if claims[cid].get("status") == "可用" and not claims[cid].get("can_write"):
            errors.append(f"{song}：状态可用但无可引用句")

    if total_v != 102:
        errors.append(f"版本总数 {total_v} ≠ 102")
    if total_pend != 11:
        errors.append(f"待判总数 {total_pend} ≠ 11")
    if total_exc != 16:
        errors.append(f"未纳入总数 {total_exc} ≠ 16（待判 11 + 未过门槛 4 + 排除 1）")
    if total_incl + total_exc != total_v:
        errors.append(f"纳入 {total_incl} + 排除 {total_exc} ≠ 总数 {total_v}")

    print(f"曲目 {len(lv['songs'])}｜版本 {total_v}｜纳入 {total_incl}｜待判 {total_pend}｜未过门槛 {total_exc - total_pend}")
    print(f"主张绑定 {len(mapping)} 首")
    if errors:
        print("\n[硬错误]")
        for e in errors:
            print("  ·", e)
    else:
        print("矩阵一致性：通过 ✅")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
