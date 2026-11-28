#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 _presets-bundle/cordis.patch.yml 的 preset-md-wx409 块内：
   ① 把写死数字改成「读单一事实源」
   ② 补齐 time-context / command-goal / tool-schedule / present / tool-office

只在 md-wx409 这一个块内动手（上一版误插到了别的预设块里，已回滚）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BUNDLE = Path(r"D:\DSH\_presets-bundle\cordis.patch.yml")
SRC = Path(r"D:\DSH\.dsh\.agent-presets\md-wx409\agent.cordis.yml")

REPL = [
    ("本机已装 markitdown 0.1.7，含 pdf/docx/pptx/xlsx 支持",
     "本机已装 markitdown（版本以 `python -m markitdown --version` 现查为准），含 pdf/docx/pptx/xlsx 支持"),
    ("本机工具已就绪：markitdown 0.1.7（pip）、PyMuPDF、GOT-OCR2.0 离线 OCR",
     "本机工具已就绪：markitdown（pip，版本现查）、PyMuPDF、GOT-OCR2.0 离线 OCR"),
    ("操作中心 D:\\wx409.github.io\\操作中心.bat（GBK 编码，**已扩到 114 项**，分 A~R 组",
     "操作中心 D:\\wx409.github.io\\操作中心.bat（GBK 编码；**菜单项数不要凭记忆，一律以 `docs/操作中心全图.md` 的实际条目为准**，改过 bat 先跑 `python project_b/dump_ops_map.py`；分 A~R 组"),
    ("build_calibers.py（口径登记表，**22 项**）",
     "build_calibers.py（口径登记表；**项数以运行时 data/calibers.md 的实际条目为准**）"),
    ("引用计数前看 data/calibers.md（**22 项**：",
     "引用计数前看 data/calibers.md（项数与数值都以该文件当前内容为准，下面是 2026-09 的示例："),
    ("（corpus 2315条，**实为4源** studio1042/wx807/baijiahao440/baike26",
     "（corpus 条数与来源分布以 `run_pipeline.py` 最新一次输出为准；2026-09 时点：4 源 studio/wx/baijiahao/baike"),
    ("**72 首录音室专辑全量实测**",
     "**录音室专辑全量实测**（曲数以 `data/archive_vocal_albums.json` 的条目数为准）"),
    ("**全站 64 = 六轮巡演 59 + 签唱会 5**",
     "**场次唯一口径以 `data/coverage_index.json` 的 shows_total 为准**（按巡次拆分见同一文件的 shows 字段）"),
    ("kb/（实体1416/事实1150/关系1942 + semantic 4702）",
     "kb/（实体/事实/关系/语义条数以 `data/kb/manifest.json` 为准）"),
    ("qa_bank.json（315条）",
     "qa_bank.json（条数以文件当前条目数为准）"),
    ("覆盖天数对外用**已发布长表的 1282 天**",
     "覆盖天数对外用**已发布长表的实际天数**（现查 `music_index_long.csv` 的唯一日期数）"),
]

ROWS = {
    "time-context": "  - id: time-context\n    name: '@deepseek-ai/dsh-time-context'\n",
}


def block_bounds(lines, preset_id="preset-md-wx409"):
    start = None
    for i, ln in enumerate(lines):
        if re.match(rf"\s*- id: {preset_id}\s*$", ln):
            start = i
            break
    if start is None:
        return None, None
    ind = len(lines[start]) - len(lines[start].lstrip())
    for j in range(start + 1, len(lines)):
        ln = lines[j]
        if ln.strip().startswith("- id: preset-") and (len(ln) - len(ln.lstrip())) == ind:
            return start, j
    return start, len(lines)


def insert_before(lines, idx, block_text):
    lines.insert(idx, block_text)


def main():
    text = BUNDLE.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    s, e = block_bounds(lines)
    if s is None:
        print("找不到 preset-md-wx409"); return 1
    print(f"md-wx409 块: L{s+1}..L{e}（{e-s} 行）")

    block = "".join(lines[s:e])
    n = 0
    for old, new in REPL:
        if old in block:
            block = block.replace(old, new); n += 1

    # 按缩进插入 5 行（plugins 层缩进 = 10 空格）
    def add_after(anchor_id, new_id, name):
        nonlocal block
        if new_id in block:
            return 0
        m = re.search(rf"^( *)  - id: {anchor_id}\s*\n(?:.*\n)*?(?=^ *- id: |^ *- insert:|^# |\Z)", block, re.M)
        if not m:
            return 0
        indent = " " * (len(m.group(1)) + 2)
        add = f"{indent}- id: {new_id}\n{indent}  name: '{name}'\n"
        pos = m.end()
        block = block[:pos] + add + block[pos:]
        return 1

    added = 0
    added += add_after("tool-jobs", "tool-schedule", "@deepseek-ai/dsh-tool-schedule")
    added += add_after("tool-skill", "command-goal", "@deepseek-ai/dsh-command-goal")
    added += add_after("tool-ai-placeholder", "time-context", "@deepseek-ai/dsh-time-context")

    # 兜底：time-context 插在 tool-bash 之前
    if "id: time-context" not in block:
        m = re.search(r"^( *)  - id: tool-bash\s*$", block, re.M)
        if m:
            indent = " " * (len(m.group(1)) + 2)
            block = block[:m.start()] + f"{indent}- id: time-context\n{indent}  name: '@deepseek-ai/dsh-time-context'\n" + block[m.start():]
            added += 1
    # present + tool-office 插在 remaining 注释前
    if "id: tool-office" not in block:
        m = re.search(r"^( *)  # ── remaining model-facing rows", block, re.M)
        if m:
            indent = " " * (len(m.group(1)) + 2)
            block = (block[:m.start()]
                     + f"{indent}- id: present\n{indent}  name: '@deepseek-ai/dsh-tool-present'\n\n"
                     + f"{indent}- id: tool-office\n{indent}  name: '@deepseek-ai/dsh-tool-office'\n\n"
                     + block[m.start():])
            added += 1

    new_text = "".join(lines[:s]) + block + "".join(lines[e:])
    BUNDLE.write_text(new_text, encoding="utf-8")
    print(f"替换数字 {n} 处，补能力 {added} 组")

    # 同步源文件（仅替换数字；能力行之前已补过）
    if SRC.exists():
        t = SRC.read_text(encoding="utf-8")
        m2 = 0
        for old, new in REPL:
            if old in t:
                t = t.replace(old, new); m2 += 1
        SRC.write_text(t, encoding="utf-8")
        print(f"源文件替换数字 {m2} 处")
    return 0


if __name__ == "__main__":
    sys.exit(main())
