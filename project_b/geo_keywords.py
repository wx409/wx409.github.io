#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO：把「王晰 音域」「男低音王晰」两个真实高曝光词写进关键页 title/description。

原因：Bing 后台 120 天数据显示——「王晰」100+ 曝光、「男低音王晰」8、「王晰 音域」6，
而这三页原本标题未含这些词。此脚本在页面生成之后执行（幂等），并接进 deploy_all。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")

TARGETS = {
    "index.html": (
        "王晰｜男低音歌手 · 音域实测与数字档案（最低稳定音 B1 61.5Hz）",
        "王晰（华语流行男低音）数字档案：72 首录音室逐帧实测，音域 B1 61.5Hz → F5 706Hz，"
        "横跨 3.5 个八度；颤音 5.12Hz、现场 879 条素材可检索；全部数字标注出处与口径。",
    ),
    "voice.html": (
        "王晰音域实测｜B1 61.5Hz → F5 706Hz，横跨 3.5 个八度（72 首逐帧）",
        "王晰音域到底多宽？72 首录音室曲目逐帧 F0 实测：最低稳定音 B1（61.5Hz）、最高稳定音 F5（706Hz），"
        "跨曲目极值合计 3.52 个八度；单曲跨度中位 2.23 个八度（最大 3.41）。附口径说明与复核状态，可核对。",
    ),
    "quotes.html": (
        "王晰金句（男低音歌手）｜深夜小酒馆 278 条，带时间码与出处",
        "王晰在《深夜小酒馆》里的 278 条金句，其中 198 条带时间码与期次出处；"
        "另附音域实测与现场素材交叉链接，供引用与核对。",
    ),
}

T_DESC = re.compile(r'(<meta\s+name=["\']description["\']\s+content=["\'])(.*?)(["\'])', re.S | re.I)


def main() -> int:
    changed = []
    for name, (title, desc) in TARGETS.items():
        p = ROOT / name
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        o = s
        m = re.search(r"<title>(.*?)</title>", s, re.S | re.I)
        if m and m.group(1).strip() != title:
            s = s.replace(m.group(0), f"<title>{title}</title>", 1)
        d = T_DESC.search(s)
        if d and d.group(2).strip() != desc:
            s = s[: d.start()] + d.group(1) + desc + d.group(3) + s[d.end():]
        if s != o:
            p.write_text(s, encoding="utf-8")
            changed.append(name)
    print(f"更新 {len(changed)} 页：{changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
