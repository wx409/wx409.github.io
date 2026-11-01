"""把曲库同步进「收听人数（2026.7.24）.xlsx」——可反复运行（幂等）

规则：
  · 曲库里有 mid、但表里没有的歌 → 追加一行（格式与现有行一致）
  · 表里有、曲库里已找不到的 mid → 在「状态」列标「已下架（曲库无此曲）」
  · 曲库里没有 mid 的歌 → 不写入（写进去也放不了），单独统计
用法：
  python -X utf8 project_b/sync_listener_xlsx.py [--dry]
"""
import argparse
import ast
import json
import re
import shutil
import time

import openpyxl
import pandas as pd

XLSX = r"E:\wx\收听人数（2026.7.24）.xlsx"
COMPACT = r"D:\wx409.github.io\tavern\songs_compact.json"
TPL = ("https://y.qq.com/m/client/music_index/index.html?ADTAG=cbshare"
       "&channelId=10036163&mid=%s&openinqqmusic=1&type=%s")
STATUS_COL_NAME = "状态"


def load_pool():
    d = json.load(open(COMPACT, encoding="utf-8"))
    items = d["songs"] if isinstance(d, dict) and "songs" in d else d
    out = []
    for x in items:
        uid = str(x.get("uid") or "")
        if uid.startswith("L:") and len(uid) > 2:
            out.append({"name": str(x.get("name") or "").split("\n")[0].strip(),
                        "mid": uid[2:]})
    return items, out


def clean(name):
    return re.sub(r"[（(].*?[)）]", "", name).strip()


def mid_of_link(v):
    m = re.search(r"[?&]mid=([0-9A-Za-z]+)", str(v or ""))
    return m.group(1) if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    all_items, pool = load_pool()
    print("曲库 %d 首｜其中有 mid 的 %d 首" % (len(all_items), len(pool)))

    wb = openpyxl.load_workbook(XLSX)
    ws = wb.active

    # 定位/新建「状态」列
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    if STATUS_COL_NAME in headers:
        status_col = headers.index(STATUS_COL_NAME) + 1
    else:
        status_col = ws.max_column + 1
        ws.cell(1, status_col, STATUS_COL_NAME)
    print("状态列：第 %d 列" % status_col)

    # 表内已有 mid
    existing = {}
    for r in range(2, ws.max_row + 1):
        mid = mid_of_link(ws.cell(r, 4).value) or mid_of_link(ws.cell(r, 5).value)
        if mid:
            existing.setdefault(mid, r)
    print("表内已有 mid %d 个" % len(existing))

    pool_mids = {p["mid"] for p in pool}
    todo = [p for p in pool if p["mid"] not in existing]
    print("需追加 %d 首" % len(todo))

    # 标记已下架
    stale = [m for m in existing if m not in pool_mids]
    print("表中已不在曲库的 mid %d 个 → 标「已下架」" % len(stale))
    for m in stale:
        r = existing[m]
        if not a.dry:
            ws.cell(r, status_col, "已下架（曲库无此曲）")

    if a.dry:
        for p in todo[:10]:
            print("   +", p["name"][:26], p["mid"])
        print("（dry-run，未写入）")
        return

    if todo:
        bak = XLSX.replace(".xlsx", "_备份_%s.xlsx" % time.strftime("%Y%m%d%H%M"))
        shutil.copy2(XLSX, bak)
        print("备份 →", bak)

    # 续序号
    seq = 0
    for r in range(2, ws.max_row + 1):
        v = ws.cell(r, 1).value
        if isinstance(v, (int, float)):
            seq = max(seq, int(v))
        elif isinstance(v, str) and v.strip().isdigit():
            seq = max(seq, int(v.strip()))

    row = ws.max_row
    added = 0
    for p in sorted(todo, key=lambda x: x["name"]):
        row += 1
        seq += 1
        full = p["name"]
        link = TPL % (p["mid"], p["mid"])
        ws.cell(row, 1, seq)
        ws.cell(row, 2, full)
        ws.cell(row, 3, "王晰")
        ws.cell(row, 4, link)
        ws.cell(row, 5, link)
        ws.cell(row, 6, None)
        ws.cell(row, 7, clean(full))
        ws.cell(row, 8, "live" if "(Live)" in full else None)
        ws.cell(row, status_col, "在用")
        added += 1

    # 已有行补状态（未标记的）
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, status_col).value:
            continue
        mid = mid_of_link(ws.cell(r, 4).value) or mid_of_link(ws.cell(r, 5).value)
        if not mid:
            ws.cell(r, status_col, "无 mid（无法播放）")
        elif mid in pool_mids:
            ws.cell(r, status_col, "在用")
        else:
            ws.cell(r, status_col, "已下架（曲库无此曲）")

    wb.save(XLSX)
    print("已追加 %d 行｜表总行数 %d" % (added, ws.max_row))

    # 覆盖率
    df = pd.read_excel(XLSX)
    mids = set(df["ngrid_链接"].astype(str).str.extract(r"mid=([0-9A-Za-z]+)")[0].dropna())
    covered = sum(1 for p in pool if p["mid"] in mids)
    print("覆盖：曲库有 mid 的 %d 首中，%d 首已在表内（%.0f%%）"
          % (len(pool), covered, covered / max(len(pool), 1) * 100))
    print("曲库仍无 mid：%d 首（无法入表）" % (len(all_items) - len(pool)))


if __name__ == "__main__":
    main()
