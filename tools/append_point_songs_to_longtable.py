# -*- coding: utf-8 -*-
"""把“工作室微博佐证、人工核对后确认”的点歌补进巡演歌单长表。

使用前确认：
  - 长表：E:\\wx\\index_records\\历次巡演歌单\\王晰巡演歌单长表_单一事实源.xlsx
  - 本脚本会先备份，再追加缺失行
  - 已通过别名/归一化跳过已存在的歌，避免重复

用法（在普通 PowerShell 中运行，需要有 E:\\wx 写权限）：
  python -X utf8 D:\\wx409.github.io\\tools\\append_point_songs_to_longtable.py
  python -X utf8 D:\\wx409.github.io\\tools\\append_point_songs_to_longtable.py --dry-run
"""
from __future__ import annotations

import argparse
import datetime
import re
import shutil
from pathlib import Path

import openpyxl

LONG_XLSX = Path(r"E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx")

# 已核对确认要补的点歌（非别名、非专辑话题）
# 每条：date/city/tour/song/note/source
CONFIRMED_ADDITIONS = [
    {
        "date": "2021-01-10",
        "city": "武汉",
        "tour": "二巡·王晰2021个人巡回音乐会",
        "song": "漫长的告别",
        "note": "点歌/安可曲目（工作室微博佐证：2021-01-11“昨日武汉开唱……点歌《漫长的告别》”）",
        "source": "工作室微博",
    },
]

# 微博常见写法 -> 长表已收录标准名（避免误加重复）
ALIAS_TO_CANONICAL = {
    "甩啦甩啦": "甩了甩了",
    "千万次地问": "千万次的问",
    "敕勒川": "敕勒歌",
}


def norm(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"[\s:：,，、+＋/／·•\-—_（）()《》\"'“”‘’]+", "", s)
    # 去掉常见语气/结构字，用于宽松去重
    s = s.replace("啦", "").replace("了", "").replace("的", "")
    return s


def canonical_song(name: str) -> str:
    return ALIAS_TO_CANONICAL.get(name.strip(), name.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只显示将要追加的行，不写文件")
    a = ap.parse_args()

    wb = openpyxl.load_workbook(LONG_XLSX)
    ws = wb["合并长表"]

    rows = list(ws.iter_rows(values_only=True))
    # 找目标场次现有行，收集已有歌名和最大序号
    added_any = False
    for add in CONFIRMED_ADDITIONS:
        target_date = add["date"]
        target_city = add["city"]
        song = add["song"]
        song_norm = norm(song)
        target_rows = [
            r for r in rows[1:]
            if r[1] and str(r[1])[:10] == target_date
            and target_city in str(r[2] or "")
        ]
        if not target_rows:
            print(f"[跳过] 长表找不到场次 {target_date} {target_city}")
            continue

        # 跳过别名/已有
        existing_norms = {norm(r[4]) for r in target_rows if r[4]}
        existing_raw = {str(r[4]).strip() for r in target_rows if r[4]}
        canon = canonical_song(song)
        if norm(canon) in existing_norms or canon in existing_raw or song in existing_raw:
            print(f"[跳过] 长表已有 {target_date} {target_city} 的「{song}」（可能以 {canon} 收录）")
            continue

        # 场次内序号：取该场已有最大数字序号 + 1
        max_seq = 0
        for r in target_rows:
            seq = r[3]
            if isinstance(seq, (int, float)) and not isinstance(seq, bool):
                max_seq = max(max_seq, int(seq))
        new_seq = max_seq + 1 if max_seq else None

        tour = add.get("tour") or target_rows[0][0] or ""
        print(f"[追加] {target_date} {target_city} 第{new_seq if new_seq else '?'}首《{song}》")
        print(f"       备注: {add['note']}")
        added_any = True

        if not a.dry_run:
            # 备份
            bak = LONG_XLSX.with_name(
                LONG_XLSX.stem + f"_bak_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            shutil.copy2(LONG_XLSX, bak)
            print(f"[备份] {bak.name}")

            ws.append([
                tour,
                datetime.datetime.strptime(target_date, "%Y-%m-%d"),
                target_city,
                new_seq,
                song,
                add["note"],
                song,
                add.get("source", "工作室微博"),
            ])
            wb.save(LONG_XLSX)
            print(f"[已写入] {LONG_XLSX}")

    if a.dry_run:
        print("\n[dry-run] 以上为预览，未修改长表。")
    elif not added_any:
        print("\n没有需要追加的新内容。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
