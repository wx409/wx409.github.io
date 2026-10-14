# -*- coding: utf-8 -*-
"""给来源台账补登两条**切片素材**（英文串烧切片 / Moon River 切片），并给已测切片打上
正确的曲名、巡次、城市、日期、BV 与 source_verdict —— 供 `生成巡演现场报告.py` 取用，
避免现场层出现「其他演出 / song 空白 / 无 BV」的不可追溯行。

切片口径（必须与读数同引）：
  · Moon River：`BV1SQ4y1e7Dg` 三巡广州站（2021-12-04）三段串烧中的**第 1 段**
    （0:00–3:40，标题「Moon river / Close to you / You needed me」→ 顺序由标题推定）
  · Smoke Gets in Your Eyes：`BV1Mypv6zECb` p20「17.王晰-英文串烧」（5:59）三段切片之一，
    **切片边界由人工/标题推定（±2s 量级）**，本次先测三段并择一为「Smoke 段」
用法：python -X utf8 project_b\\register_slice_ledger.py [--apply]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LEDGER = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频\来源台账.json")

ENTRIES = [
    {"song": "Moon River", "tag": "切片1_MoonRiver", "bv": "BV1SQ4y1e7Dg",
     "title": "王晰 三巡广州站《Moon river》《Close to you》《You needed me》",
     "owner": "MOON丨TBC", "pubdate": "2021-12-06", "duration_s": 220,
     "audio_kind": "切片(m4a copy)", "bandwidth_kbps": 321,
     "file": r"场次音频\Moon River_切片\切片1_MoonRiver_BV1SQ4y1e7Dg.m4a",
     "size_mb": 2.7, "duration_probe_s": 220.0, "source_verdict": "官方直传·切片",
     "exclude_hits": [],
     "note": "三巡广州站**同场三段中的第 1 段**（0:00–3:40），曲名由标题顺序推定；"
             "切片边界为等分推定（±2s 量级）须与读数同引",
     "series": "三巡广州串烧", "tour": "三巡", "city": "广州", "date": "2021-12-04",
     "fetched_at": "2026-10-14"},
    {"song": "Close to You", "tag": "切片2_CloseToYou", "bv": "BV1SQ4y1e7Dg",
     "title": "（同上，第 2 段）", "owner": "MOON丨TBC", "pubdate": "2021-12-06",
     "duration_s": 220, "audio_kind": "切片(m4a copy)", "bandwidth_kbps": 321,
     "file": r"场次音频\Moon River_切片\切片2_CloseToYou_BV1SQ4y1e7Dg.m4a",
     "size_mb": 2.8, "duration_probe_s": 220.0, "source_verdict": "官方直传·切片",
     "exclude_hits": [], "note": "三巡广州串烧第 2 段（3:40–7:20），曲名由标题顺序推定",
     "series": "三巡广州串烧", "tour": "三巡", "city": "广州", "date": "2021-12-04",
     "fetched_at": "2026-10-14"},
    {"song": "You Needed Me", "tag": "切片3_YouNeededMe", "bv": "BV1SQ4y1e7Dg",
     "title": "（同上，第 3 段）", "owner": "MOON丨TBC", "pubdate": "2021-12-06",
     "duration_s": 210, "audio_kind": "切片(m4a copy)", "bandwidth_kbps": 321,
     "file": r"场次音频\Moon River_切片\切片3_YouNeededMe_BV1SQ4y1e7Dg.m4a",
     "size_mb": 2.7, "duration_probe_s": 210.2, "source_verdict": "官方直传·切片",
     "exclude_hits": [], "note": "三巡广州串烧第 3 段（7:20–10:50）",
     "series": "三巡广州串烧", "tour": "三巡", "city": "广州", "date": "2021-12-04",
     "fetched_at": "2026-10-14"},
    {"song": "Smoke Gets in Your Eyes", "tag": "切片1", "bv": "BV1Mypv6zECb",
     "title": "261009 沉响与长歌 北京场 4K全程 p20「17.王晰-英文串烧」",
     "owner": "月弯弯与芋圆圆", "pubdate": "2026-10-10", "duration_s": 120,
     "audio_kind": "切片(m4a copy)", "bandwidth_kbps": 187,
     "file": r"场次音频\英文串烧_切片\切片1_BV1Mypv6zECb.m4a",
     "size_mb": 2.7, "duration_probe_s": 120.0, "source_verdict": "重制(二次制作)·切片",
     "exclude_hits": [],
     "note": "**【现场·串烧切片】英文串烧第 1 段（0:00–2:00）**；切片边界由人工/标题推定，"
             "±2s 量级误差须与读数同引；该曲为**首次演唱**（用户确认 2026-10-14）",
     "series": "沉响20261009英文串烧", "tour": "东演双人场（待核）", "city": "北京", "date": "2026-10-09",
     "fetched_at": "2026-10-14"},
    {"song": "Moon River", "tag": "切片2", "bv": "BV1Mypv6zECb",
     "title": "（同上，英文串烧第 2 段）", "owner": "月弯弯与芋圆圆", "pubdate": "2026-10-10",
     "duration_s": 120, "audio_kind": "切片(m4a copy)", "bandwidth_kbps": 187,
     "file": r"场次音频\英文串烧_切片\切片2_BV1Mypv6zECb.m4a",
     "size_mb": 2.8, "duration_probe_s": 120.0, "source_verdict": "重制(二次制作)·切片",
     "exclude_hits": [], "note": "英文串烧第 2 段（2:00–4:00），曲名由分P标题顺序推定",
     "series": "沉响20261009英文串烧", "tour": "东演双人场", "city": "北京", "date": "2026-10-09",
     "fetched_at": "2026-10-14"},
    {"song": "Love Me Tender", "tag": "切片3", "bv": "BV1Mypv6zECb",
     "title": "（同上，英文串烧第 3 段）", "owner": "月弯弯与芋圆圆", "pubdate": "2026-10-10",
     "duration_s": 119, "audio_kind": "切片(m4a copy)", "bandwidth_kbps": 186,
     "file": r"场次音频\英文串烧_切片\切片3_BV1Mypv6zECb.m4a",
     "size_mb": 2.8, "duration_probe_s": 119.0, "source_verdict": "重制(二次制作)·切片",
     "exclude_hits": [], "note": "英文串烧第 3 段（4:00–5:59）",
     "series": "沉响20261009英文串烧", "tour": "东演双人场", "city": "北京", "date": "2026-10-09",
     "fetched_at": "2026-10-14"},
    # 一生中最爱（三巡舟山）已由下载器登记，这里只补 tour/city/date（若缺）
    {"song": "一生中最爱", "tag": "三巡舟山20260523", "bv": "BV13MVK6uEa9",
     "title": "王晰「一生中最爱」【4K横版】20260523舟山听海而歌演唱会",
     "owner": "SMARTELVIS", "pubdate": "2026-05-26", "duration_s": 252,
     "audio_kind": "dash", "bandwidth_kbps": 102,
     "file": r"场次音频\一生中最爱\三巡舟山20260523_BV13MVK6uEa9.m4a",
     "size_mb": 3.1, "duration_probe_s": 251.8, "source_verdict": "重制(二次制作) · 待听辨",
     "exclude_hits": [],
     "note": "用户确认该曲三巡唱过；4K 横版（二次制作）→ 读数须注明批次与来源判定",
     "tour": "三巡", "city": "舟山", "date": "2026-05-23", "fetched_at": "2026-10-14"},
]


def main() -> int:
    apply = "--apply" in sys.argv
    d = json.loads(LEDGER.read_text(encoding="utf-8"))
    items = d.setdefault("items", [])
    have = {(x.get("tag"), x.get("bv")) for x in items}
    add, upd = [], 0
    for e in ENTRIES:
        key = (e["tag"], e["bv"])
        if key in have:
            for x in items:
                if (x.get("tag"), x.get("bv")) == key:
                    for k in ("song", "tour", "city", "date", "series", "note"):
                        if e.get(k) and x.get(k) != e.get(k):
                            x[k] = e[k]
                            upd += 1
            continue
        items.append(e)
        add.append(e)
    print("[台账] 新增 %d 条；补齐字段 %d 处；合计 %d 条" % (len(add), upd, len(items)))
    if apply:
        LEDGER.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[写入]", LEDGER)
    else:
        print("（试算，未写盘；加 --apply 落地）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
