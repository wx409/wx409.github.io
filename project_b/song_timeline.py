#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""song_timeline.py —— 同曲跨年索引（为「成长线」准备）

不删任何文件、不做跨场去重（每场保持完整）；只是**建立索引**：
  某首歌（按归一名）→ 每年的哪一场、哪个文件、哪条 BV、音轨码率

产出：
  data/成长线_同曲跨年.md     人看：按年份跨度排序，标出跨 5 年 / 10 年的曲目
  data/成长线_同曲跨年.json   程序用
规律：
  - 年份取自场次日期
  - 跨度 = 最新年 - 最早年；≥10 年标 ★★，≥5 年标 ★
  - 「待核」行单独列出，不参与跨度统计
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
XLSX = DATA / "最优音频清单.xlsx"


def norm_song(name: str) -> str:
    n = re.sub(r"^\[[^\]]+\]", "", str(name or ""))
    n = re.sub(r"\.(flac|wav|m4a|mp3)$", "", n, flags=re.I)
    n = re.sub(r"[\s，,。、·・\-—_（）()《》「」【】!！?？]", "", n)
    n = re.sub(r"^(点歌|安可|encore)", "", n, flags=re.I)
    n = re.sub(r"^\d{1,2}[\s._、-]*", "", n)      # 去掉小卡带/分P 的序号
    n = re.sub(r"^第[一二三四五六七八九十\d]+(首|曲)", "", n)
    return n.strip()


def main():
    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    cols = [c.value for c in ws[1]]
    idx = {c: i for i, c in enumerate(cols)}

    songs = defaultdict(list)
    pending = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        date8 = re.sub(r"\D", "", str(r[idx["日期"]] or ""))[:8]
        if len(date8) < 8:
            continue
        year = int(date8[:4])
        file = str(r[idx["文件名"]] or "")
        song = norm_song(file)
        if not song or len(song) > 30:
            continue          # 整场/长标题不算"单曲"
        if "未复制" in song or song in ("上半场", "下半场", "全场", "清唱 安可", "清唱+安可"):
            continue
        note = str(r[idx["备注"]] or "") if "备注" in idx else ""
        item = {"year": year, "date": date8, "city": str(r[idx["城市"]] or ""),
                "tour": str(r[idx["巡次"]] or ""), "file": file,
                "path": str(r[idx["目标路径"]] or ""),
                "bv": str(r[idx["BV"]] or "") if "BV" in idx else "",
                "kbps": r[idx["码率kbps"]] if "码率kbps" in idx else None,
                "src": str(r[idx["来源"]] or "")}
        if "待核" in note:
            pending.append(item)
            continue
        songs[song].append(item)

    rows = []
    for song, items in songs.items():
        years = sorted({i["year"] for i in items})
        if len(years) < 2:
            continue
        span = years[-1] - years[0]
        rows.append({"song": song, "years": years, "span": span,
                     "count": len(items),
                     "items": sorted(items, key=lambda x: x["year"])})
    rows.sort(key=lambda x: (-x["span"], x["song"]))

    md = ["# 同曲跨年索引（成长线素材）", "",
          f"> 曲目 {len(rows)} 首存在跨年演唱；★=跨 5 年以上，★★=跨 10 年以上",
          f"> 待核 {len(pending)} 条另列，不计入跨度", ""]
    for r in rows:
        star = "★★" if r["span"] >= 10 else ("★" if r["span"] >= 5 else "")
        md.append(f"## {r['song']} {star}（{r['years'][0]}–{r['years'][-1]}，跨 {r['span']} 年，{r['count']} 次）")
        md.append("")
        md.append("| 年份 | 日期 | 巡次/城市 | 音轨 | 文件 | BV |")
        md.append("|---|---|---|---|---|---|")
        for it in r["items"]:
            md.append(f"| {it['year']} | {it['date']} | {it['tour']} {it['city']} | {it['kbps'] or ''} | "
                      f"{it['file'][:36]} | {it['bv']} |")
        md.append("")
    if pending:
        md += ["# 待核", "", "| 日期 | 城市 | 文件 | BV |", "|---|---|---|---|"]
        for it in pending:
            md.append(f"| {it['date']} | {it['city']} | {it['file'][:40]} | {it['bv']} |")

    (DATA / "成长线_同曲跨年.md").write_text("\n".join(md), encoding="utf-8")
    (DATA / "成长线_同曲跨年.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    top = [r for r in rows if r["span"] >= 5]
    print(f"跨年曲目 {len(rows)} 首；跨 5 年以上 {len(top)} 首；待核 {len(pending)} 条")
    for r in rows[:12]:
        star = "★★" if r["span"] >= 10 else ("★" if r["span"] >= 5 else " ")
        print(f"  {star} {r['song'][:18]:18} {r['years'][0]}–{r['years'][-1]} 跨{r['span']}年 {r['count']}次")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
