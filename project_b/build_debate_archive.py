#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_debate_archive.py —— 生成《王晰音域辩音总档》（传记素材，可持续累积）。

为什么做成生成器而不是手工合并：
  辩音记录散落在多处（9-9 引擎复核 / 9-11 单曲复核 / 9-15 首批听辨 / 9-16 全量辩音），
  将来还会继续增加。手工合并必然过期 → **用生成器，每次重跑即刷新**，
  与前缀「不写死数字、单一事实源」的项目纪律一致。

产出：E:\\wx\\论文素材_王晰作传\\辩音总档_王晰音域.md
用法：python -X utf8 project_b/build_debate_archive.py
"""
from __future__ import annotations

import io
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
AN = Path(r"E:\wx\论文素材_王晰作传\音域分析")
ARCH = Path(r"E:\wx\论文素材_王晰作传")
OUT = ARCH / "辩音总档_王晰音域.md"

# 前史材料（按时间序）——只列确实存在的
PRE = [
    ("2026-09-09", "十曲严格口径复核", AN / "复核_十曲严格口径.md",
     "建立「稳定音/触达音/低音带读数」三级读数制度的第一次系统性复核"),
    ("2026-09-10", "低音复核报告（Low C）", AN / "低音复核报告_LowC_20260909.md",
     "针对 Low C 区逐条复核，确立了「在原始混音上查谐波列」的判定方法"),
    ("2026-09-10", "引擎稳健性复核", AN / "轨迹" / "引擎稳健性复核.md",
     "YIN / CREPE 双引擎交叉，量化引擎差异"),
    ("2026-09-10", "引擎稳健性复核（他人主导）", AN / "轨迹" / "引擎稳健性复核_他人主导.md",
     "对照层（他人主导舞台）的引擎稳健性"),
    ("2026-09-11", "让她降落 B1 复核", AN / "轨迹" / "让她降落_B1复核_20260911.md",
     "单曲深挖：从 B1 候选到定案的全过程"),
    ("2026-09-11", "低音读数复核备忘", AN / "轨迹" / "备忘_低音读数复核_20260911.md",
     "复核结论与站点数据核对"),
]
MAIN = ARCH / "辩音全记录_20260916.md"          # 今天的正本
LED = ROOT / "data" / "listening_verdicts.json"


def read(p: Path, limit: int | None = None) -> str:
    if not p.exists():
        return ""
    t = p.read_text(encoding="utf-8", errors="replace")
    if limit and len(t) > limit:
        t = t[:limit] + "\n\n> ……（此处按长度截断；全文见原文件）\n"
    return t


def main() -> int:
    led = json.loads(LED.read_text(encoding="utf-8")) if LED.exists() else {}
    items = led.get("items") or []
    by_date = {}
    for x in items:
        by_date.setdefault(x.get("date") or "（早期）", []).append(x)

    L = []
    add = L.append
    add("# 王晰音域 · 人耳辩音总档")
    add("")
    add("> 生成：%s ｜ **由 `project_b/build_debate_archive.py` 生成，可重跑刷新**" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    add(">")
    add("> **这份档是什么**：把 2026-09-09 起全部「音域读数复核」与「人耳听辨」的过程与结论")
    add("> 汇成一份**持续累积**的传记素材。它记录的不是结论，而是**在没有共识的领域里，")
    add("> 一个可信结论是怎么被一点点争出来的**。")
    add(">")
    add("> **为什么值得写进传记**：他没有权威数据背书，外部说法互相矛盾；")
    add("> 每一个数字都要自己从音频里量、再自己用耳朵验。")
    add("> 这个「量了又听、听了又推翻」的过程本身，就是最鲜活的一手材料。")
    add("")

    add("## 时间线索引")
    add("")
    add("| 日期 | 阶段 | 内容 |")
    add("|---|---|---|")
    add("| 09-09 ~ 09-11 | **方法建立期** | 三级读数制度、谐波列判定法、双引擎交叉（无人工听辨） |")
    add("| 09-15 | **首批人工听辨** | 6 条定案；首次「耳朵否决算法」（C6 1059.3） |")
    add("| 09-16 | **全量辩音** | 三批共 59 条裁决；C6 三轮；切错源；2× 谐波锁 |")
    add("")
    add("**累计人耳裁决：%d 条**（按日期：%s）"
        % (len(items), "、".join("%s %d 条" % (k, len(v)) for k, v in sorted(by_date.items()))))
    add("")

    add("---")
    add("")
    add("# 第一部 · 方法建立期（09-09 ~ 09-11）")
    add("")
    add("> 这一阶段**还没有人工听辨**，全部工作是把「测量」做扎实：")
    add("> 建立三级读数制度、确立谐波列判定法、做双引擎交叉。")
    add("> 它是后面所有听辨的地基 —— **没有可信的测量，听辨就没有对象**。")
    add("")
    for date, name, path, why in PRE:
        add("## %s ｜ %s" % (date, name))
        add("")
        add("**这一步在做什么**：%s" % why)
        add("")
        add("**原文件**：`%s`" % path)
        add("")
        body = read(path)
        if body:
            add("<details><summary>展开原文</summary>")
            add("")
            add(body.strip())
            add("")
            add("</details>")
            add("")
        else:
            add("（原文件缺失）")
            add("")

    add("---")
    add("")
    add("# 第二部 · 全量辩音（09-15 ~ 09-16）")
    add("")
    add("> 正本见 `%s`，此处完整并入。" % MAIN)
    add("")
    add(read(MAIN).strip())
    add("")

    add("---")
    add("")
    add("# 附录 · 人耳裁决台账（机读源：`data/listening_verdicts.json`）")
    add("")
    add("| 日期 | 曲目 | 方面 | 裁决 |")
    add("|---|---|---|---|")
    for d in sorted(by_date):
        for x in by_date[d]:
            add("| %s | %s | %s | %s |" % (d, x.get("song"), x.get("aspect"), x.get("verdict")))
    add("")
    add("**台账纪律**（原样引用）：")
    for s in (led.get("discipline") or []):
        add("- %s" % s)
    add("")
    add("---")
    add("")
    add("> **本档由生成器产出，勿手改**：改动请改上游文件（09-09~09-11 各复核报告、")
    add("> `辩音全记录_20260916.md`、`data/listening_verdicts.json`）后重跑 ")
    add("> `python -X utf8 project_b/build_debate_archive.py`。")

    OUT.write_text("\n".join(L), encoding="utf-8")
    txt = OUT.read_text(encoding="utf-8")
    print("✔ 已生成：%s" % OUT)
    print("   %d 行 / %d 字" % (len(txt.split("\n")), len(txt)))
    print("   纳入前史 %d 份 ｜ 正本 %d 字 ｜ 裁决 %d 条"
          % (sum(1 for _, _, p, _ in PRE if p.exists()), len(read(MAIN)), len(items)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
