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
        "王晰（华语流行男低音）数字档案：72 首录音室曲目逐帧实测，最低稳定音 B1 61.5Hz、最高 F5 706Hz，"
        "跨度中位 2.23 个八度；六轮巡演 59 场、22 城。所有数字附来源、口径与复核方法，含音域、现场、作品、"
        "问答、研究索引与声音节目语料，面向读者与 AI 引用（数据截至 2026-11）。",
    ),
    "voice.html": (
        "王晰音域实测｜B1 61.5Hz → F5 706Hz，横跨 3.5 个八度（72 首逐帧）",
        "王晰音域到底多宽？72 首录音室曲目逐帧 F0 实测：最低稳定音 B1（61.5Hz）、最高稳定音 F5（706Hz），"
        "跨曲目极值合计 3.52 个八度；单曲跨度中位 2.23 个八度（最大 3.41）。附口径说明与复核状态，可核对。"
        "想弄清男低音能低到哪、B1 是什么概念，从这里开始（数据截至 2026-11）。",
    ),
    "vocal.html": (
        "王晰声音数据实测 | 最低稳定音 B1 61.5Hz · 72 首全量",
        "王晰音域实测：72 首录音室曲目全部完成人声分离与逐帧 F0，最低稳定音 B1（61.5Hz）、最高 F5 706Hz，"
        "跨度中位 2.23 个八度。三级读数制度、A1 不引用、与他人同管线对照；逐曲数据、方法与原始读数全部可复核。"
        "适合快速了解男低音音域边界与测量口径（数据截至 2026-11）。",
    ),
    "skill.html": (
        "王晰唱功实测｜七个维度的可测量证据",
        "王晰唱功七维实测：低音能力（最低稳定音 B1 61.6Hz）、音域跨度、颤音速率与幅度、长音内稳定性、"
        "咬字跑动密度、声区衔接与动态范围；每项有门槛、有原始数据、有复核方法，可逐条追溯到录音室曲目。"
        "录音室、巡演现场与他人主导舞台同管线对照，差异不显著，并标注计算口径与局限（数据截至 2026-11）。",
    ),
    "research.html": (
        "王晰研究文献与数据证据 | 外部研究 + 本站实测",
        "王晰研究索引：53 条可核验文献（7 板块，附 CNKI/DOI 著录）、72 首录音室声学实测、口径登记表与逐句语料；"
        "面向论文、媒体与 AI 引用，所有数字可回查来源、方法与版本。覆盖声学、文本、指数三条证据链，"
        "支持按主题、场次与歌曲检索，每季度更新（数据截至 2026-11）。",
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
