#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inject_long_notes.py —— 把 data/archive_long_notes.json 注入 vocal.html 第八章「长声持续能力」。

纪律：数字全部从 JSON 派生，不写死。
幂等：带标记块先删后插。
用法：python -X utf8 project_b/inject_long_notes.py
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = "<!-- LONG-NOTES:START -->"
END = "<!-- LONG-NOTES:END -->"


def num(v, d=1):
    try:
        return ("%%.%df" % d) % float(v)
    except Exception:
        return "—"


def build(doc):
    s = doc.get("stats") or {}
    top = doc.get("top") or []
    _flag = doc.get("top_flagged") or []
    _kept = doc.get("stats", {}).get("n_after_verdict_join", len(top))
    _kept_d = sorted([x.get("dur_s") or 0 for x in top], reverse=True)
    L = [START, '<h2 id="长声">八、长声持续能力（演唱，非 talk）</h2>',
         '<p>长声时长 = <strong>同一音高连续保持</strong>的秒数'
         '（连续同音高段，抖动 &lt;0.6 半音）。'
         '这是<strong>直接可观测量</strong>，无需自创判据。'
         '数据来自 %d 个演唱段（已排除 talk 段）。</p>' % int(s.get("n_ge6s") or 0),
         '<p class="sub">⚠️ 经「长声表 × 否决台账」反连接后，榜单只保留 <strong>%d</strong> 条；'
         '另有 <strong>%d</strong> 条已移出（%s）。'
         'C5 及以上长声默认需人耳归属确认——长声检测跑在 demucs vocals 轨上，而该轨含和声。</p>'
         % (_kept, len(_flag), "；".join(str(x.get("verdict_conflict", ""))[:28] for x in _flag) or "无"),
         '<div class="kv">',
         '<div><span class="k">≥8 秒（保留榜）</span><span class="v">%d 个</span></div>' % len([d for d in _kept_d if d >= 8]),
         '<div><span class="k">≥10 秒</span><span class="v">%d 个</span></div>' % len([d for d in _kept_d if d >= 10]),
         '<div><span class="k">≥12 秒</span><span class="v">%d 个</span></div>' % len([d for d in _kept_d if d >= 12]),
         '<div><span class="k">≥15 秒</span><span class="v">%d 个</span></div>' % len([d for d in _kept_d if d >= 15]),
         '<div><span class="k">中位</span><span class="v">%s 秒</span></div>'
         % (round(__import__("statistics").median(_kept_d), 1) if _kept_d else 0),
         '<div><span class="k">最长</span><span class="v">%s 秒</span></div>' % num(max(_kept_d) if _kept_d else 0),
         "</div>",
         "<h3>最长的 20 个长声</h3>",
         '<table><thead><tr><th>#</th><th>时长</th><th>音</th><th>Hz</th>'
         "<th>来源</th><th>曲目</th></tr></thead><tbody>"]
    for x in top[:20]:
        L.append("<tr><td>%d</td><td>%s 秒</td><td>%s</td><td>%s</td>"
                 "<td>%s</td><td>%s</td></tr>" % (
                     x.get("rank"), num(x.get("dur_s")), x.get("note"),
                     num(x.get("hz")), str(x.get("where") or "")[:24],
                     str(x.get("song") or "")))
    L += ["</tbody></table>",
          '<p class="src">方法：逐帧 F0（demucs 人声分离 → numpy YIN）→ '
          "连续同音高段切分（抖动 &lt;0.6 半音，≥6 秒）→ 取时长。"
          '<strong>只计演唱段</strong>：文件名排除 talk/点歌/讲话，'
          "且须匹配该场歌单曲目名。"
          "口径见 <code>data/archive_long_notes.json</code>。</p>",
          END]
    return "\n".join(L)


def main() -> int:
    p = os.path.join(R, "vocal.html")
    j = os.path.join(R, "data", "archive_long_notes.json")
    if not os.path.exists(j):
        print("✗ 缺 %s" % j)
        return 1
    doc = json.load(io.open(j, encoding="utf-8"))
    t = io.open(p, encoding="utf-8").read()
    block = build(doc)
    # 幂等：先删旧块
    t = re.sub(re.escape(START) + r".*?" + re.escape(END), "", t, flags=re.S)
    # 插在「他说过」之前；没有则插在 </body> 前
    anchor = t.find("他说过")
    if anchor > 0:
        # 回退到该区块起始标签
        i = t.rfind("<h2", 0, anchor)
        if i < 0:
            i = anchor
        t = t[:i] + block + "\n" + t[i:]
    else:
        t = t.replace("</body>", block + "\n</body>", 1)
    io.open(p, "w", encoding="utf-8").write(t)
    print("✔ vocal.html 已注入第八章（保留榜 ≥8 秒 %d 条 / 移出 %d 条，最长 %s 秒）"
          % (len([d for d in _kept_d if d >= 8]), len(_flag),
             num((doc.get("stats") or {}).get("max_s"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
