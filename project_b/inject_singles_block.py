#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""往 voice.html 注入「单曲补充实测」区块（幂等）。

内容只写已过复核的数：
  · 苏幕遮 C#2 71.0Hz → D#5 621.3Hz = 3.13 八度（高音过谐波复核）
  · 爱于此生 D2 73.3Hz → E5 668.2Hz = 3.19 八度（保守值；A5 882Hz 待核）
不写：55.3Hz（伴奏低音）、A5 882Hz（待核）、无荒（合唱归属未定）
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
PAGE = ROOT / "voice.html"
MARK = "<!-- singles-supplement -->"

BLOCK = MARK + """
<section id="singles-supplement">
<h2>单曲补充实测（非专辑）</h2>
<p class="sub">专辑 72 首之外的正式单曲 / OST，按同一口径（人声分离 + 逐帧 F0）实测；
高音读数须通过「原始混音谐波列」复核才计入。</p>
<table>
<thead><tr><th>曲目</th><th>最低稳定音</th><th>最高（已复核）</th><th>跨度</th><th>说明</th></tr></thead>
<tbody>
<tr><td>苏幕遮</td><td>C#2 · 71.0Hz</td><td>D#5 · 621.3Hz</td><td><b>3.13 八度</b></td><td>高音通过谐波复核</td></tr>
<tr><td>爱于此生</td><td>D2 · 73.3Hz</td><td>E5 · 668.2Hz</td><td><b>3.19 八度</b></td><td>保守值；A5 882Hz 待人耳确认</td></tr>
</tbody></table>
<p class="sub">以下读数不计入：55.3Hz 低音（与伴奏低音声部重合，非人声）、A5 882Hz（谐波存疑）、
《无荒》（与谭维维合唱，音高归属未定）、谱面 5̇（D6，实录未见该音）。</p>
<p class="sub">曲谱参考：网友 <b>@柯烬</b> 扒谱合集（已获作者授权；谱面仅本地留存，不在本站公开）。</p>
</section>
"""


def main() -> int:
    if not PAGE.exists():
        print("voice.html 不存在")
        return 1
    s = PAGE.read_text(encoding="utf-8")
    if MARK in s:
        s = re.sub(re.escape(MARK) + r".*?</section>\s*", "", s, flags=re.S)
    anchor = "</main>" if "</main>" in s else "</body>"
    s = s.replace(anchor, BLOCK + "\n" + anchor, 1)
    PAGE.write_text(s, encoding="utf-8")
    print("已注入单曲补充区块")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
