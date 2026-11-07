#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""③ 测量误差基准：自动 F0 分析在流行录音上「多久错一次、错成什么样」。

数据：data/archive_stage_tour.json（843 条素材的复核台账）
产出：data/measurement_audit.json

口径
  · 素材类型：按 tag / source_verdict / tour 推断（饭拍·直拍 / 官方·自录 / 电视·晚会 / 未分类）
  · 复核状态：谐波列通过 / 待判 / 人耳确认 / 人耳否决 / 不可复核 / HNR 异常 / 未复核
  · 错误形态：从 harmonic_screen.why 与 a3_final_note 归类（1f0 弱 / 次谐波 / bass 污染 / 缺混音）
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "archive_stage_tour.json"
OUT = ROOT / "data" / "measurement_audit.json"


LIB = Path(r"E:\wx\论文素材_王晰作传\音域分析\轨迹\轨迹素材库.json")


def load_bv_map():
    """BV → source_verdict / owner / title（来自轨迹素材库）。"""
    m = {}
    try:
        d = json.loads(LIB.read_text(encoding="utf-8"))
    except Exception:
        return m
    for song, blob in (d.get("songs") or {}).items():
        for it in (blob.get("items") or []):
            bv = (it.get("bv") or "").strip()
            if bv:
                m[bv] = {"verdict": it.get("source_verdict") or "",
                         "owner": it.get("owner") or "",
                         "title": it.get("title") or ""}
    return m


BV_MAP = load_bv_map()


def kind_of(r):
    # ① 先用 BV 查素材库的权威判定
    bv = (r.get("bv") or "").strip()
    if not bv:
        import re as _re
        mm = _re.search(r"(BV[0-9A-Za-z]{10})", (r.get("tag") or "") + " " + (r.get("title") or ""))
        bv = mm.group(1) if mm else ""
    if bv and bv in BV_MAP:
        v = BV_MAP[bv]["verdict"]
        if "官方" in v:
            return "官方"
        if "重制" in v or "混剪" in v:
            return "二创/混剪"
    return _kind_heuristic(r)


def _kind_heuristic(r):
    tag = (r.get("tag") or "") + " " + (r.get("title") or "")
    sv = r.get("source_verdict") or ""
    tour = r.get("tour") or ""
    if "自录" in tag or tour == "签唱会":
        return "自录/签售"
    if "官方" in sv or "官方直传" in sv:
        return "官方"
    if any(k in tag for k in ("直拍", "P0", "_P")) or "饭拍" in tag:
        return "直拍/饭拍"
    if any(k in tag for k in ("晚会", "春晚", "节目", "采访", "综艺")):
        return "电视/晚会"
    return "未分类"


def err_form(r):
    if (r.get("review_status") or "") == "谐波列通过":
        return "通过（无需归因）"
    why = ((r.get("harmonic_screen") or {}).get("why") or "")
    note = r.get("a3_final_note") or ""
    if "缺混音" in str(note) or "缺混音" in why:
        return "缺混音/无法复核"
    if "1f0" in why:
        gap = (r.get("harmonic_screen") or {}).get("fund_gap_db")
        if gap is not None and gap <= -30:
            return "基频极弱（疑次谐波/分离伪影）"
        return "基频偏弱（待判）"
    if "人耳否决" in note:
        return "人耳否决（非本人）"
    return "无异常标记"


def main() -> int:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    rows = d.get("rows") or []
    tab = defaultdict(Counter)
    forms = Counter()
    hn = []
    for r in rows:
        k = kind_of(r)
        st = r.get("review_status") or "未复核"
        tab[k][st] += 1
        forms[err_form(r)] += 1
        if r.get("hnr_db") is not None:
            hn.append((k, float(r["hnr_db"]), st))

    total = len(rows)
    print("素材 %d 条｜类型分布：%s" % (total, {k: sum(v.values()) for k, v in tab.items()}))
    states = ["谐波列通过", "待复核（谐波列待判）", "人耳确认", "人耳否决（非王晰）",
              "不可复核（缺混音/时间）", "谐波列通过（HNR 异常，疑分离失败）", "未复核"]
    print("\n类型 × 复核状态：")
    hdr = "  %-12s %6s %6s %6s %6s %6s %6s %6s  %s" % ("类型", "通过", "待判", "人耳√", "人耳✗", "不可复核", "HNR异常", "未复核", "否决率")
    print(hdr)
    summary = {}
    for k, cnt in sorted(tab.items(), key=lambda x: -sum(x[1].values())):
        n = sum(cnt.values())
        v = [cnt.get(s, 0) for s in states]
        rej = 100 * v[3] / n if n else 0
        print("  %-12s %6d %6d %6d %6d %6d %6d %6d  %5.1f%%" % (k, *v, rej))
        summary[k] = {"n": n, "by_state": {s: cnt.get(s, 0) for s in states},
                      "reject_pct": round(rej, 1)}
    print("\n错误形态分布：")
    for k, v in forms.most_common():
        print("  %-28s %4d  (%4.1f%%)" % (k, v, 100 * v / total))

    OUT.write_text(json.dumps({
        "schema": "measurement-audit/v1",
        "n_materials": total,
        "by_kind": summary,
        "error_forms": dict(forms),
        "generated_at": date.today().isoformat(),
        "note": "否决率=人耳否决（非王晰）占比；待判=基频弱且未定案",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n→", OUT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
