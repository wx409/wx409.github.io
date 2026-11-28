#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修 md-wx409 预设：① 写死数字改为「读单一事实源」 ② 补齐 0.2.2 新增能力行

同时改两处，保持一致：
  D:\\DSH\\_presets-bundle\\cordis.patch.yml   （真正生效）
  D:\\DSH\\.dsh\\.agent-presets\\md-wx409\\agent.cordis.yml （迁移源）
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BUNDLE = Path(r"D:\DSH\_presets-bundle\cordis.patch.yml")
SRC = Path(r"D:\DSH\.dsh\.agent-presets\md-wx409\agent.cordis.yml")

# (旧串, 新串)：把「会漂移的计数」改成「去读单一事实源」
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

# 0.2.2 新增能力行（缩进由插入位置决定）
ROWS = {
    "time-context": "- id: time-context\n  name: '@deepseek-ai/dsh-time-context'\n",
    "command-goal": "- id: command-goal\n  name: '@deepseek-ai/dsh-command-goal'\n",
    "tool-schedule": "- id: tool-schedule\n  name: '@deepseek-ai/dsh-tool-schedule'\n",
    "present": "- id: present\n  name: '@deepseek-ai/dsh-tool-present'\n",
    "tool-office": "- id: tool-office\n  name: '@deepseek-ai/dsh-tool-office'\n",
}


def indent_lines(block: str, indent: str) -> str:
    return "".join(indent + ln if ln.strip() else ln for ln in block.splitlines(keepends=True))


def add_rows(text: str, indent: str) -> tuple[str, int]:
    added = 0
    # 1) time-context 放在 tool-bash 之前
    if "id: time-context" not in text:
        m = re.search(rf"^{re.escape(indent)}- id: tool-bash\s*$", text, re.M)
        if m:
            text = text[:m.start()] + indent_lines(ROWS["time-context"], indent) + "\n" + text[m.start():]
            added += 1
    # 2) command-goal 放在 tool-goal 之前
    if "id: command-goal" not in text:
        m = re.search(rf"^{re.escape(indent)}- id: tool-goal\s*$", text, re.M)
        if m:
            text = text[:m.start()] + indent_lines(ROWS["command-goal"], indent) + "\n" + text[m.start():]
            added += 1
    # 3) tool-schedule 放在 tool-jobs 之后（即下一个同缩进 - id: 之前）
    if "id: tool-schedule" not in text:
        m = re.search(rf"^{re.escape(indent)}- id: tool-jobs\s*\n(?:.*\n)*?(?=^{re.escape(indent)}- id: )", text, re.M)
        if m:
            text = text[:m.end()] + indent_lines(ROWS["tool-schedule"], indent) + "\n" + text[m.end():]
            added += 1
    # 4) present + tool-office 放在 remaining 注释之前
    if "id: tool-office" not in text:
        m = re.search(rf"^{re.escape(indent)}# ── remaining model-facing rows", text, re.M)
        if m:
            block = indent_lines(ROWS["present"], indent) + "\n" + indent_lines(ROWS["tool-office"], indent) + "\n"
            text = text[:m.start()] + block + text[m.start():]
            added += 1
    return text, added


def main():
    total_repl = 0
    for path, indent in ((BUNDLE, " " * 10), (SRC, "")):
        if not path.exists():
            print("跳过（不存在）:", path)
            continue
        text = path.read_text(encoding="utf-8")
        bak = path.with_suffix(path.suffix + ".bak_before_dynamic")
        if not bak.exists():
            bak.write_text(text, encoding="utf-8")
        n = 0
        for old, new in REPL:
            if old in text:
                text = text.replace(old, new)
                n += 1
        text, added = add_rows(text, indent)
        path.write_text(text, encoding="utf-8")
        total_repl += n
        print(f"{path.name}: 替换数字 {n} 处，补能力行 {added} 组")
    print("合计替换:", total_repl)
    return 0


if __name__ == "__main__":
    sys.exit(main())
