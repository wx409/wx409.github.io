#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_extreme_prior.py —— 第 34 条纪律的实现：用「该曲已知音域」筛除假极值。

为什么需要它（2026-09-17 用户指出）：
  用户用一句「**这首歌《茕茕》本身就不高**」直接否掉了现场报出的 1035.8Hz。
  —— 算法不知道歌名，也就不知道"这首歌该有多高"。
  而档案里恰好有 72 首录音室曲目 + 现场层 228 条素材的实测音域，可作**先验上限**。

判据（第 34 条纪律）：
  对任一现场/新素材的「最高稳定音」H1，查该曲的已知上限 H0：
    H1 ≤ H0 + 5 半音          → 正常
    5 < H1−H0 < 12 半音       → ⚠️ 待核（须人耳）
    H1−H0 ≥ 12 半音（一个八度）→ ❌ 疑假极值
  同理对「最低稳定音」做下限先验（低于已知下限 5 半音 → 待核）。

⚠️ 它只是**筛除工具**，不能替代人耳：
   用户的另一条判据「人声在钢琴下」是音色判断，算法做不到。

用法：
  python -X utf8 project_b/audit_extreme_prior.py                 # 审计全部现场素材
  python -X utf8 project_b/audit_extreme_prior.py --root <目录>    # 只审计指定目录
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AN = r"E:\wx\论文素材_王晰作传\音域分析"
SEMI_WARN = 5.0
SEMI_FAKE = 12.0


def semi(a, b):
    return 12.0 * math.log2(a / b) if (a and b) else 0.0


def load_prior():
    """已知音域表：专辑 72 首 + 现场层 228 条。"""
    hi, lo = {}, {}
    p = os.path.join(R, "data", "archive_vocal_albums.json")
    if os.path.exists(p):
        d = json.load(io.open(p, encoding="utf-8"))
        for x in (d.get("songs") or []):
            t = str(x.get("title") or "")
            if t and x.get("high_hz"):
                hi[t] = max(hi.get(t, 0), x["high_hz"])
            if t and x.get("low_hz"):
                lo[t] = min(lo.get(t, 1e9), x["low_hz"])
    p2 = os.path.join(R, "data", "archive_stage_tour.json")
    if os.path.exists(p2):
        d = json.load(io.open(p2, encoding="utf-8"))
        for x in (d.get("rows") or []):
            t = str(x.get("song") or "")
            h = x.get("high_hz")
            l = x.get("low_hz")
            if t and isinstance(h, (int, float)):
                hi[t] = max(hi.get(t, 0), h)
            if t and isinstance(l, (int, float)):
                lo[t] = min(lo.get(t, 1e9), l)
    return hi, lo


def judge(title, h1, l1, HI, LO):
    """返回 (高音判词, 低音判词, 高音半音差, 低音半音差)。"""
    fh = fl = ""
    dh = dl = None
    base = HI.get(title)
    if base and h1:
        dh = semi(h1, base)
        if dh >= SEMI_FAKE:
            fh = "❌疑假(超已知+%.1f半音)" % dh
        elif dh >= SEMI_WARN:
            fh = "⚠️待核(超已知+%.1f半音)" % dh
    base2 = LO.get(title)
    if base2 and base2 < 1e8 and l1:
        dl = semi(l1, base2)     # 负值 = 比已知更低
        if dl <= -SEMI_FAKE:
            fh2 = "❌疑假(低于已知%.1f半音)" % dl
            fl = fh2
        elif dl <= -SEMI_WARN:
            fl = "⚠️待核(低于已知%.1f半音)" % dl
    return fh, fl, dh, dl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="", help="只审计指定分析目录")
    a = ap.parse_args()
    HI, LO = load_prior()
    print("[先验表] 已知高音上限 %d 曲 ｜ 已知低音下限 %d 曲" % (len(HI), len(LO)))

    roots = ([a.root] if a.root else
             [d for d in glob.glob(os.path.join(AN, "场次音频", "*_分析")) if os.path.isdir(d)])
    flagged = []
    total = 0
    for root in roots:
        for f in glob.glob(os.path.join(root, "*", "*_stats.json")):
            try:
                d = json.load(open(f, encoding="utf-8"))
            except Exception:
                continue
            t = str(d.get("title") or "")
            h1 = (d.get("high_stable") or {}).get("hz")
            l1 = (d.get("low_stable") or {}).get("hz")
            total += 1
            # 整场素材文件名不是歌名 → 用文件名里的曲名部分尽力匹配
            base_key = t.split("__")[0]
            fh, fl, dh, dl = judge(base_key, h1, l1, HI, LO)
            if not fh and not fl:
                fh, fl, dh, dl = judge(t, h1, l1, HI, LO)
            if fh or fl:
                flagged.append({"root": os.path.basename(root), "title": t,
                                "high": h1, "low": l1, "fh": fh, "fl": fl,
                                "dh": round(dh, 2) if dh is not None else None,
                                "dl": round(dl, 2) if dl is not None else None})
    print("[审计] 共 %d 条素材 ｜ 触发先验 %d 条" % (total, len(flagged)))
    print()
    if flagged:
        print("  %-34s %9s %9s %s" % ("素材", "高Hz", "低Hz", "判词"))
        for x in sorted(flagged, key=lambda y: -(y["dh"] or 0)):
            print("  %-34s %9s %9s %s / %s" % (
                x["title"][:34], x["high"] or "—", x["low"] or "—", x["fh"] or "—", x["fl"] or "—"))
    out = os.path.join(R, "temp", "_extreme_prior_audit.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(
        {"prior_size": {"high": len(HI), "low": len(LO)}, "total": total,
         "flagged": flagged}, ensure_ascii=False, indent=1))
    print()
    print("  → %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
