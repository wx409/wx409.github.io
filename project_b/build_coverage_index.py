# -*- coding: utf-8 -*-
"""场次覆盖索引 v2：**多方匹配**（BV 映射 + 精确日期 + 台账 tag + 表 + 路径线索）。

数据源（全部本地，自动 join）：
  S1 站点现场层 data/archive_stage_tour.json      （bv / city / date / tag）
  S2 场次音频\\来源台账.json                        （bv / tag=巡次+城市+YYYYMMDD）
  S3 temp\\_tour_parts_index.json                  （BV → 标题，标题含场次名与日期）
  S4 temp\\_attr\\shows_tour.json                   （date + city + tour）
  S5 temp\\王晰历年巡演目录.csv                      （巡次 + 时间 + 城市）
  S6 本地素材路径（场次音频 / 声音素材库\\media / 六巡 / 轨迹）→ BV、8 位日期、城市、巡次词

证据分级：L1 精确（BV 映射到该场 / 路径含该场日期）｜L2 强（表直接给出该场 / 日期±2天）
          L3 中（城市+年月）｜L4 弱（仅巡次+城市）
产出：data/coverage_index.json
"""
from __future__ import annotations

import csv
import json
import os
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
AUD = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")
MEDIA = Path(r"E:\wx\声音素材库\media")
TEMP = ROOT / "temp"
TOURS = ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡", "签唱会")
SCAN_ROOTS = [AUD, MEDIA, Path(r"E:\wx\六巡"), Path(r"E:\wx\论文素材_王晰作传\音域分析\轨迹"),
              Path(r"G:\王晰巡演素材存档")]   # 自录大疆/ZOOM 原件（外置盘；未挂载时自动跳过）

DATE8 = re.compile(r"(20\d{2})[.\-_]?(\d{2})[.\-_]?(\d{2})")
DATE_CN = re.compile(r"(20\d{2})年(\d{1,2})月(\d{1,2})日")
BV = re.compile(r"(BV[0-9A-Za-z]{10})")


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def dates_in(s: str) -> set:
    out = set()
    for y, m, d in DATE8.findall(s):
        try:
            out.add(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    for y, m, d in DATE_CN.findall(s):
        try:
            out.add(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    return out


def main() -> int:
    shows = jload(DATA / "setlists.json").get("setlists", {})
    cities = sorted({v.get("city", "") for v in shows.values() if v.get("city")}, key=len, reverse=True)
    show_dates = {d: (v.get("city", ""), v.get("tour", "")) for d, v in shows.items()}

    # 场次 → 证据
    ev = defaultdict(list)          # date -> [(level, source, detail)]
    bv_to_show = {}                 # BV -> 场次日期

    # S3：BV → 标题 → 城市/日期/巡次
    parts = jload(TEMP / "_tour_parts_index.json")
    for bv, v in (parts.items() if isinstance(parts, dict) else []):
        title = str(v.get("title", ""))
        for d in dates_in(title) | dates_in(str(v.get("dir", ""))):
            ds = d.isoformat()
            if ds in show_dates:
                bv_to_show[bv] = ds
                ev[ds].append((1, "BV映射", f"{bv}｜{title[:40]}"))

    # S2：来源台账 tag
    tb = jload(AUD / "来源台账.json")
    for it in tb.get("items", []):
        tag = str(it.get("tag", ""))
        bv = str(it.get("bv", ""))
        for d in dates_in(tag):
            ds = d.isoformat()
            if ds in show_dates:
                ev[ds].append((2, "来源台账", f"{bv}｜{it.get('song','')}｜{tag}"))
                if bv:
                    bv_to_show.setdefault(bv, ds)

    # S4：shows_tour.json
    for it in jload(TEMP / "_attr" / "shows_tour.json") or []:
        ds = str(it.get("date"))[:10]
        if ds in show_dates:
            ev[ds].append((2, "shows_tour表", f"{it.get('city','')}｜{it.get('tour','')[:18]}"))

    # S5：历年巡演目录.csv（巡次+时间+城市）
    f = TEMP / "王晰历年巡演目录.csv"
    if f.exists():
        for row in csv.DictReader(f.open(encoding="utf-8-sig")):
            blob = " ".join(str(x) for x in row.values())
            for d in dates_in(blob):
                ds = d.isoformat()
                if ds in show_dates:
                    ev[ds].append((2, "巡演目录", f"{row.get('巡次','')[:16]}｜{row.get('场次','')}"))

    # S1：站点现场层
    for r in jload(DATA / "archive_stage_tour.json").get("rows", []):
        ds = str(r.get("date"))[:10]
        if ds in show_dates:
            ev[ds].append((1, "站点实测", f"{r.get('tag','')}｜{r.get('song','')}"))
            if r.get("bv"):
                bv_to_show.setdefault(str(r["bv"]), ds)

    # S6：扫描本地素材路径（BV / 日期 / 城市 / 巡次）
    l3 = defaultdict(int)   # (city, ym) -> 文件数
    l4 = defaultdict(int)   # (tour, city) -> 文件数
    n_files = 0
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for dp, _dns, fs in os.walk(root):
            for name in fs:
                n_files += 1
                blob = dp + "\\" + name
                for bv in BV.findall(blob):
                    if bv in bv_to_show:
                        ev[bv_to_show[bv]].append((1, "BV命中", bv))
                for d in dates_in(blob):
                    for off in (-2, -1, 0, 1, 2):
                        ds = (d + timedelta(days=off)).isoformat()
                        if ds in show_dates and off == 0:
                            ev[ds].append((1, "路径日期", name[:44]))
                city = next((c for c in cities if c in blob), "")
                if city:
                    tours = {t for t in TOURS if t in blob}
                    for y, m in re.findall(r"(20\d{2})[.\-_](\d{2})(?!\d)", blob):
                        if 1 <= int(m) <= 12:
                            l3[(city, f"{y}-{m}")] += 1
                            for t in tours:
                                pass
                    for t in tours:
                        l4[(t, city)] += 1

    rows, miss = [], []
    for ds, v in sorted(shows.items()):
        city, tour = v.get("city", ""), v.get("tour", "")
        e = ev.get(ds, [])
        best = min((x[0] for x in e), default=99)
        if e:
            rows.append({"date": ds, "city": city, "tour": tour, "songs": len(v.get("songs", [])),
                         "level": best, "evidence": [{"level": l, "src": s, "detail": d} for l, s, d in e[:6]],
                         "n_evidence": len(e)})
        elif l3.get((city, ds[:7])):
            rows.append({"date": ds, "city": city, "tour": tour, "songs": len(v.get("songs", [])),
                         "level": 3, "evidence": [{"level": 3, "src": "城市+年月", "detail": f"{l3[(city, ds[:7])]} 文件"}],
                         "n_evidence": 1})
        elif l4.get((tour, city)):
            rows.append({"date": ds, "city": city, "tour": tour, "songs": len(v.get("songs", [])),
                         "level": 4, "evidence": [{"level": 4, "src": "巡次+城市", "detail": f"{l4[(tour, city)]} 文件"}],
                         "n_evidence": 1})
        else:
            miss.append({"date": ds, "city": city, "tour": tour, "songs": len(v.get("songs", []))})

    lv = defaultdict(int)
    for r in rows:
        lv[r["level"]] += 1
    stat = {"generated_at": datetime.now().isoformat(timespec="seconds"),
            "shows_total": len(shows), "covered": len(rows), "missing": len(miss),
            "L1_精确": lv[1], "L2_强": lv[2], "L3_中": lv[3], "L4_弱": lv[4],
            "measured_shows_hint": "L1/L2 可视为已定位到具体场次", "files_scanned": n_files,
            "measured_shows_site": sum(1 for r in rows if any(
                e["src"] == "站点实测" for e in r.get("evidence", []))),
            "bv_mapped": len(bv_to_show)}
    (DATA / "coverage_index.json").write_text(
        json.dumps({"stat": stat, "shows": rows, "missing": miss}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    print("\n按巡次（已定位 L1+L2 / 总场次 / 有素材）：")
    agg = defaultdict(lambda: [0, 0, 0])
    for ds, v in shows.items():
        agg[v.get("tour", "")][1] += 1
    for r in rows:
        t = r["tour"]
        agg[t][2] += 1
        if r["level"] <= 2:
            agg[t][0] += 1
    for t, (a, b, c) in sorted(agg.items()):
        print(f"  {t}: {a}/{b}（有素材 {c}）")
    print("\n仍无任何线索：", "、".join(f'{m["city"]}{m["date"][5:]}' for m in miss))
    print("→ data/coverage_index.json")
    assert stat["shows_total"] == 64
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
