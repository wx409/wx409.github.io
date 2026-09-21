# -*- coding: utf-8 -*-
"""本地清单：哪些场次有视频素材（按 64 场逐场列出，含 BV/时长/文件、本地路径、是否已实测）。

判据：
  · 视频文件 = 本地扫到的 .mp4/.mkv/.flv/.webm/.ts/.LRF（含场次音频目录、声音素材库、六巡等）
  · 同时给出该场已入库的实测素材数（站点现场层）与 BV 数（来源台账/轨迹索引/路径命中）
输出：E:\\wx\\论文素材_王晰作传\\有视频场次清单_王晰巡演.md（本地留存）＋ data/video_shows.json
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\有视频场次清单_王晰巡演.md")
AUD = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")
SCAN = [AUD, Path(r"E:\wx\声音素材库"), Path(r"E:\wx\六巡"), Path(r"D:\wx409.github.io\temp"),
        Path(r"G:\王晰巡演素材存档"),                 # 自录大疆/ZOOM 素材（2026-09-18 归档到 G 盘）
        Path(r"E:\wx\论文素材_王晰作传\原始材料"),
        Path(r"E:\wx\download")]
VIDEO = (".mp4", ".mkv", ".flv", ".webm", ".ts", ".lrf", ".mov", ".avi")
DATE8 = re.compile(r"(20\d{2})[.\-_]?(\d{2})[.\-_]?(\d{2})")
BV = re.compile(r"(BV[0-9A-Za-z]{10})")


def main() -> int:
    shows = json.loads((DATA / "setlists.json").read_text(encoding="utf-8"))["setlists"]
    cities = sorted({v.get("city", "") for v in shows.values() if v.get("city")}, key=len, reverse=True)
    tour = json.loads((DATA / "archive_stage_tour.json").read_text(encoding="utf-8"))
    measured = defaultdict(int)
    for r in tour.get("rows", []):
        measured[(r.get("city", ""), str(r.get("date"))[:10])] += 1

    # 扫描本地视频
    vids = defaultdict(list)      # (city,date) -> [(file, size, path)]
    loose = defaultdict(list)     # (city,tour) -> files（无法定到日）
    n_video = 0
    scanned, missing = [], []
    for root in SCAN:
        if not root.exists():
            missing.append(str(root))
            continue
        scanned.append(str(root))
        root_tour = next((t for t in ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡", "签唱会") if t in str(root)), "")
        for dp, _d, fs in os.walk(root):
            for f in fs:
                if not f.lower().endswith(VIDEO):
                    continue
                n_video += 1
                blob = dp + "\\" + f
                city = next((c for c in cities if c in blob), "")
                for y, m, dd in DATE8.findall(blob):
                    try:
                        d0 = date(int(y), int(m), int(dd))
                    except ValueError:
                        continue
                    for off in (-1, 0, 1):
                        ds = (d0 + timedelta(days=off)).isoformat()
                        if ds in shows and (not city or city == shows[ds].get("city")):
                            vids[(shows[ds].get("city", ""), ds)].append((f, os.path.getsize(os.path.join(dp, f)), dp))
                            break
                if city:
                    for t in ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡", "签唱会"):
                        if t in blob or t == root_tour:
                            loose[(city, t)].append((f, dp))
                            break

    rows = []
    for ds, v in sorted(shows.items()):
        city, t = v.get("city", ""), v.get("tour", "")
        got = vids.get((city, ds), [])
        bvs = sorted({b for f, _s, _p in got for b in BV.findall(f)})
        rows.append({
            "date": ds, "city": city, "tour": t, "songs": len(v.get("songs", [])),
            "video_files": len(got), "video_mb": round(sum(s for _f, s, _p in got) / 2**20, 1),
            "bvs": bvs, "measured_materials": measured.get((city, ds), 0),
            "has_video": bool(got), "samples": [f"{f}（{s/2**20:.0f}MB）" for f, s, _p in got[:3]],
            "only_loose": (not got) and bool(loose.get((city, t))),
        })
    with_video = [r for r in rows if r["has_video"]]
    stat = {"generated_at": datetime.now().isoformat(timespec="seconds"),
            "shows_total": len(rows), "shows_with_video": len(with_video),
            "shows_loose_only": sum(1 for r in rows if r["only_loose"]),
            "shows_no_video": sum(1 for r in rows if not r["has_video"] and not r["only_loose"]),
            "video_files_scanned": n_video, "scanned_roots": scanned, "missing_roots": missing,
            "video_gb": round(sum(r["video_mb"] for r in rows) / 1024, 2)}

    L = [f"# 有视频的场次清单（自动生成 {datetime.now():%Y-%m-%d %H:%M}）", "",
         f"- 64 场巡演/签唱会中，**{stat['shows_with_video']} 场有本地视频**（合计约 {stat['video_gb']} GB）｜"
         f"仅能定位到「巡次+城市」的 {stat['shows_loose_only']} 场｜无视频 {stat['shows_no_video']} 场",
         f"- 扫描本地视频文件 {n_video} 个", ""]
    if missing:
        L += ["## ⚠️ 未挂载的素材根（清单不完整的原因）", ""]
        L += [f"- `{m}`" for m in missing]
        L += ["", "> 这些盘/目录当前不存在，其视频**未计入下表**。插回后重跑本脚本即可补全"
                  "（`python -X utf8 project_b\\build_video_show_list.py`）。", ""]
    L += ["".join(["已扫描根："] + ["，".join(f"`{s}`" for s in scanned)]), "",
          "## 有视频的场次", "",
          "| 日期 | 城市 | 巡次 | 歌单曲数 | 视频文件 | 体积 | BV | 已实测素材 |", "|---|---|---|---|---|---|---|---|"]
    for r in with_video:
        L.append(f"| {r['date']} | {r['city']} | {r['tour']} | {r['songs']} | {r['video_files']} | "
                 f"{r['video_mb']:.0f} MB | {'、'.join(r['bvs'][:2]) or '—'} | {r['measured_materials'] or '—'} |")
    L += ["", "## 只能定位到「巡次+城市」（视频名无日期）", "",
          "、".join(f"{r['city']}{r['date'][5:]}（{r['tour']}）" for r in rows if r["only_loose"]) or "无", "",
          "## 无任何视频的场次", "",
          "、".join(f"{r['city']}{r['date'][5:]}（{r['tour']}）" for r in rows
                    if not r["has_video"] and not r["only_loose"]) or "无", "",
          "## 明细样例（每场前 3 个文件）", ""]
    for r in with_video:
        L.append(f"- **{r['date']} {r['city']}**：" + "；".join(r["samples"]))
    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    (DATA / "video_shows.json").write_text(json.dumps({"stat": stat, "shows": rows}, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    print(f"→ {OUT_MD}\n→ data/video_shows.json")
    assert stat["shows_total"] == 64
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
