#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_scan_missing.py —— 扫描 9 个 UP 的 B站空间，列出「标题含王晰 + 巡演词、且本地没有」的视频

输出 temp/up_missing.json（供 bili_best_fetch.py --from-missing 使用）
空间接口用 wbi 签名（不带签名会返回 0 条），每页 50，默认只扫第一页。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
sys.path.insert(0, str(ROOT / "project_b"))
import importlib.util


def load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


A = load("aud", str(ROOT / "project_b" / "bili_up_audit.py"))


def main():
    pages = 3
    if "--pages" in sys.argv:
        try:
            pages = int(sys.argv[sys.argv.index("--pages") + 1])
        except Exception:
            pages = 3
    m = A.load_dl()
    h = A.headers(m)
    have = A.local_bvs()
    res, missing = {}, []
    for name, mid in A.MIDS.items():
        vids = A.space(m, h, mid, pages)
        res[name] = len(vids)
        for v in vids:
            bv = v.get("bvid")
            t = (v.get("title") or "").strip()
            if not bv or "王晰" not in t:
                continue
            if any(w in t for w in A.BAD_WORDS) or not any(w in t for w in A.TOUR_WORDS):
                continue
            if bv in have:
                continue
            missing.append({"up": name, "bv": bv, "title": t, "len": v.get("length"),
                            "play": v.get("play"), "created": v.get("created")})
        print(f"{name}: {len(vids)} 条", flush=True)
        time.sleep(6)
    out = ROOT / "temp" / "up_missing.json"
    out.write_text(json.dumps({"ups": res, "missing": missing}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"未收录 {len(missing)} 条 -> {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
