#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收尾三件：
  ① 素材来源分类不再有「未分类」——按 source_verdict → BV 库 → 整场录像 → UP主上传 逐级判定
  ② 从「到达方式=direct」里挑最低的 3 条，做成带时间戳的可引用句
  ③ 把结果写回 data/measurement_audit.json 与 data/citable_claims.json
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
TOUR = ROOT / "data" / "archive_stage_tour.json"
LIB = Path(r"E:\wx\论文素材_王晰作传\音域分析\轨迹\轨迹素材库.json")
APPROACH = ROOT / "data" / "approach_all.json"
CLAIMS = ROOT / "data" / "citable_claims.json"
AUDIT = ROOT / "data" / "measurement_audit.json"


def load_bv_map():
    m = {}
    try:
        d = json.loads(LIB.read_text(encoding="utf-8"))
        for _song, blob in (d.get("songs") or {}).items():
            for it in (blob.get("items") or []):
                bv = (it.get("bv") or "").strip()
                if bv:
                    m[bv] = {"verdict": it.get("source_verdict") or "", "owner": it.get("owner") or ""}
    except Exception:
        pass
    return m


def classify(r, bvmap):
    bv = (r.get("bv") or "").strip()
    if not bv:
        mm = re.search(r"(BV[0-9A-Za-z]{10})", (r.get("tag") or "") + " " + (r.get("title") or ""))
        bv = mm.group(1) if mm else ""
    sv = (r.get("source_verdict") or "").strip()
    if "官方" in sv:
        return "官方直传"
    if "重制" in sv or "混剪" in sv:
        return "二创/混剪"
    if bv and bv in bvmap and bvmap[bv]["verdict"]:
        v = bvmap[bv]["verdict"]
        if "官方" in v:
            return "官方直传"
        if "重制" in v or "混剪" in v:
            return "二创/混剪"
    tag = (r.get("tag") or "") + " " + (r.get("title") or "")
    if "自录" in tag or (r.get("tour") or "") == "签唱会":
        return "自录/签售"
    if re.search(r"全程|全场|整场", tag):
        return "整场录像（未切分）"
    if (r.get("owner") or "").strip():
        return "UP主上传"
    if bv:
        return "B站（来源未判定）"
    return "无来源标注"




def clean_song(name):
    n = str(name or "")
    n = re.sub(r"_f0$", "", n)
    n = re.split(r"_BV[0-9A-Za-z]{10}", n)[0]
    n = re.sub(r"_p%\S*", "", n)
    n = re.sub(r"__P\d+.*$", "", n)
    n = re.sub(r"[【\[].*?[】\]]", "", n)
    n = re.sub(r"\(.*?\)", "", n)
    n = re.sub(r"^\d+\s*[.、]?\s*", "", n)
    return n.strip()[:18] or "（未命名素材）"

def main() -> int:
    bvmap = load_bv_map()
    rows = json.loads(TOUR.read_text(encoding="utf-8"))["rows"]
    tab = defaultdict(Counter)
    for r in rows:
        tab[classify(r, bvmap)][r.get("review_status") or "未复核"] += 1

    total = len(rows)
    states = ["谐波列通过", "待复核（谐波列待判）", "人耳确认", "人耳否决（非王晰）",
              "不可复核（缺混音/时间）", "谐波列通过（HNR 异常，疑分离失败）", "未复核"]
    summary, print_rows = {}, []
    print("素材 %d 条｜来源分类：" % total)
    for k, cnt in sorted(tab.items(), key=lambda x: -sum(x[1].values())):
        n = sum(cnt.values())
        rej = 100 * cnt.get("人耳否决（非王晰）", 0) / n
        summary[k] = {"n": n, "reject_pct": round(rej, 1),
                      "by_state": {s: cnt.get(s, 0) for s in states}}
        print("  %-18s n=%4d 否决 %5.1f%%" % (k, n, rej))

    # ② direct 的最低三条
    ap = json.loads(APPROACH.read_text(encoding="utf-8"))
    directs = [r for r in ap["rows"]
               if r.get("approach") == "direct" and r.get("low_hz")
               and r["low_hz"] >= 61.0]   # ≥B1：A1/55Hz 一类属低音带读数，三不许
    excluded = sum(1 for r in ap["rows"] if r.get("approach") == "direct"
                   and r.get("low_hz") and r["low_hz"] < 61.0)
    print("按三级读数制度排除 sub-B1 的 direct 行：%d" % excluded)
    directs.sort(key=lambda r: r["low_hz"])
    claims = json.loads(CLAIMS.read_text(encoding="utf-8"))
    claims["claims"] = [c for c in claims["claims"] if not str(c.get("id", "")).startswith("direct-")]
    added = []
    for i, r in enumerate(directs[:3], 1):
        c = {
            "id": "direct-%d" % i,
            "song": clean_song(r.get("song") or r.get("file")),
            "version": "逐帧文件：%s" % r.get("path", "")[:60],
            "timestamp": "%s–%s" % (r["t0"], r["t1"]),
            "metric": "极值音直接咬住（块前 2 秒无下行准备），±0.5 半音窗口",
            "sentence": "《%s》这一版，%.1fHz 的最低音是**直接咬住**的（%.2f 秒，前 2 秒没有滑音准备），出现在 %s–%s。"
                        % (clean_song(r.get("song") or r.get("file")), r["low_hz"], r["dur"], r["t0"], r["t1"]),
            "source": "data/approach_all.json",
            "caveat": "到达方式由 F0 轨迹反推；极低音仍以台账复核状态为准",
        }
        claims["claims"].append(c)
        added.append(c)

    claims["n_direct_claims"] = len(added)
    CLAIMS.write_text(json.dumps(claims, ensure_ascii=False, indent=1), encoding="utf-8")
    AUDIT.write_text(json.dumps({
        "schema": "measurement-audit/v2",
        "n_materials": total,
        "by_source": summary,
        "rule": "source_verdict → BV 库 → 整场录像 → UP主上传 → 无来源标注；不再有『未分类』",
        "generated_at": date.today().isoformat(),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n新增 direct 可引用句 %d 条：" % len(added))
    for c in added:
        print("  -", c["sentence"][:96])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
