#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""往 voice.html 注入「单曲补充实测」区块（幂等，数据来自 data/vocal_singles.json）。

只写：
  · verified / corrected 的读数（corrected 附修正说明）
  · pending 的高音不写数字，只标「待核」
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
PAGE = ROOT / "voice.html"
DATA = ROOT / "data" / "vocal_singles.json"
MARK = "<!-- singles-supplement -->"

LABEL = {"verified": "已复核", "corrected": "已修正", "pending": "待核"}


def row(x: dict) -> str:
    song = html.escape(str(x.get("song") or ""))
    lo = x.get("low")
    lo_hz = x.get("low_hz")
    lo_txt = "%s · %.1fHz" % (lo, lo_hz) if lo and lo_hz else "—"
    hi = x.get("high")
    hi_hz = x.get("high_hz")
    hi_txt = "%s · %.1fHz" % (hi, hi_hz) if hi and hi_hz else "<b>待核</b>"
    span = x.get("span")
    span_txt = "<b>%.2f 八度</b>" % span if span else "—"
    note = html.escape(str(x.get("note") or ""))
    status = LABEL.get(str(x.get("status")), str(x.get("status")))
    tail = status + ("：" + note if note else "")
    return ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (song, lo_txt, hi_txt, span_txt, html.escape(tail)))


def build_block() -> str:
    d = json.loads(DATA.read_text(encoding="utf-8"))
    items = d.get("items") or []
    rows = "\n".join(row(x) for x in items)
    return MARK + """
<section id="singles-supplement">
<h2>单曲补充实测（非专辑）</h2>
<p class="sub">专辑 72 首之外的正式单曲 / OST，按同一口径（QQ音乐 320k → 人声分离 → 逐帧 F0）实测；
极值音经人声轨 CREPE + 谐波阶梯复核；高音双读数未决的标「待核」，不写数字。</p>
<table>
<thead><tr><th>曲目</th><th>最低稳定音</th><th>最高稳定音</th><th>跨度</th><th>状态 / 说明</th></tr></thead>
<tbody>
%s
</tbody></table>
<p class="sub">方法：%s。%s</p>
</section>
""" % (rows, html.escape(str(d.get("method") or "")), html.escape(str(d.get("note") or "")))


def main() -> int:
    if not PAGE.exists():
        print("voice.html 不存在")
        return 1
    s = PAGE.read_text(encoding="utf-8")
    if MARK in s:
        s = re.sub(re.escape(MARK) + r".*?</section>\s*", "", s, flags=re.S)
    anchor = "</main>" if "</main>" in s else "</body>"
    s = s.replace(anchor, build_block() + "\n" + anchor, 1)
    PAGE.write_text(s, encoding="utf-8")
    print("已注入单曲补充实测：", len(json.loads(DATA.read_text(encoding="utf-8")).get("items") or []), "条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
