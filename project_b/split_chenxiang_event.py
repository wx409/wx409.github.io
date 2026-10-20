# -*- coding: utf-8 -*-
"""把《沉响与长歌》北京站从「一行合并」拆成**两行两场**（10-09 / 10-10），共享 series_id。

依据：`data/show_setlists/2026-10-09_北京.json`、`2026-10-10_北京.json`（各晚歌单）。
不删数据：备份原 xlsx；原合并曲目保留在备注里（旧值留痕）。
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

XLSX = Path(r"E:\wx\index_records\王晰演出活动.xlsx")
BAK = XLSX.with_name("王晰演出活动.备份20261020_沉响拆两场.xlsx")
S9 = Path(r"D:\wx409.github.io\data\show_setlists\2026-10-09_北京.json")
S10 = Path(r"D:\wx409.github.io\data\show_setlists\2026-10-10_北京.json")


def songs_of(p: Path) -> list[str]:
    d = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for seg in d.get("segment_list") or []:
        for s in seg.get("songs") or []:
            if s and s not in out:
                out.append(s)
    return out


def main() -> int:
    s9, s10 = songs_of(S9), songs_of(S10)
    print(f"10-09 曲目 {len(s9)}｜10-10 曲目 {len(s10)}")
    wb = load_workbook(XLSX)
    ws = wb.active
    hdr = [c.value for c in ws[1]]
    col = {h: i + 1 for i, h in enumerate(hdr)}
    r = next(i for i in range(2, ws.max_row + 1) if ws.cell(i, col["序号"]).value == 204)
    old_songs = str(ws.cell(r, col["演唱曲目"]).value or "")
    old_note = str(ws.cell(r, col["备注"]).value or "")
    # 原合并值留痕
    ws.cell(r, col["备注"]).value = (old_note + "；【2026-10-20 拆场】原为两晚合并一行（34 曲），"
                                             "现拆为 10-09 / 10-10 两行，各用本晚歌单；原合并曲目："
                                             + old_songs[:400])
    ws.cell(r, col["时间"]).value = datetime(2026, 10, 9)
    ws.cell(r, col["演唱曲目"]).value = "、".join(s9)

    # 追加 10-10 行
    new_r = ws.max_row + 1
    seq = ws.cell(r, col["序号"]).value
    ws.cell(new_r, col["序号"]).value = seq
    ws.cell(new_r, col["演出名称"]).value = ws.cell(r, col["演出名称"]).value
    ws.cell(new_r, col["时间"]).value = datetime(2026, 10, 10)
    ws.cell(new_r, col["地点"]).value = ws.cell(r, col["地点"]).value
    ws.cell(new_r, col["备注"]).value = "【2026-10-20 拆场】系列 series_id=沉响与长歌_2026北京；第二场（10-10）"
    ws.cell(new_r, col["演唱曲目"]).value = "、".join(s10)

    if not BAK.exists():
        shutil.copy2(XLSX, BAK)
        print("[备份]", BAK)
    wb.save(XLSX)
    print(f"[OK] 已拆：行 {r}=10-09（{len(s9)} 曲）｜新行 {new_r}=10-10（{len(s10)} 曲）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
