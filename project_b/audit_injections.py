# -*- coding: utf-8 -*-
"""注入审计（结果指纹版）——补上今天暴露的守门缺口。

为什么需要它
------------
2026-09-21 发现：5 个注入器（首页巡演事实/更新说明/Last updated/听众说、vocal 音域摘要、长声章、人耳确认章）
全部因为「锚点被历史重建清掉」或「排在 build_compact 之前被覆盖」而长期 **no-op**，
而**没有任何审计报警** —— 这就是"口头说改好了、页面上其实是断链"的根因。

审计口径（只看结果，不看机制）
------------------------------
对每个注入器，检查它的**产物指纹**是否出现在目标页的可见位置，并要求达到最小数量：
  · inject_index_facts   → index.html：“巡演”事实块与 Last updated 块都有可见文字
  · inject_essay_quotes  → index.html：`quote-item` ≥ 3 条
  · inject_vocal_summary → vocal.html：音域摘要句（含“精测表”与“首”）
  · inject_long_notes    → vocal.html：长声章（含“≥8 秒”与表格行）
  · inject_top_verified  → vocal.html：人耳确认读数块（含“人耳确认识别”或“最高”）
退出码 1 = 有注入未落地（部署应中断）。
用法：python -X utf8 project_b\\audit_injections.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def count(html: str, pat: str) -> int:
    return len(re.findall(pat, html))


def main() -> int:
    idx = (ROOT / "index.html").read_text(encoding="utf-8")
    voc = (ROOT / "vocal.html").read_text(encoding="utf-8")
    checks = [
        ("inject_index_facts → 首页巡演事实块",
         count(idx, r"TOUR-FACTS:START[\s\S]{80,}?TOUR-FACTS:END") >= 1),
        ("inject_index_facts → 首页 Last updated",
         count(idx, r"LAST-UPDATED:START[\s\S]{40,}?LAST-UPDATED:END") >= 1),
        ("inject_essay_quotes → 首页听众说（≥3 条）",
         count(idx, r'class="quote-item"') >= 3),
        ("inject_vocal_summary → vocal 音域摘要",
         ("精测表" in voc) and ("首" in voc)),
        ("inject_long_notes → vocal 长声章（含 ≥8 秒 + 行）",
         ("≥8 秒" in voc) and count(voc, r"<tr>") > 5),
        ("inject_top_verified → vocal 人耳确认块",
         ("人耳确认" in voc)),
    ]
    print("=" * 70)
    print("注入审计（结果指纹版）")
    print("=" * 70)
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    print()
    if bad:
        print(f"结论：{len(bad)} 处注入未落地 ❌（页面数字会静默脱管）")
        print("修法：先 build_compact，再依次跑 5 个注入器，最后 build_nav；"
              "deploy_all 已内置「注入复跑守卫」。")
        return 1
    print("结论：注入链路完整 ✅（页面上都能看到注入产物）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
