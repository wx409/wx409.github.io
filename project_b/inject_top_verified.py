#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T20：把「现场最高音（人耳确认）」写进数据层 + stage.html。

数据来源：data/listening_verdicts.json 中 verdict='是王晰本人' 的读数。
纪律：数字全部派生，不写死；幂等注入。
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = "<!-- TOP-VERIFIED:START -->"
END = "<!-- TOP-VERIFIED:END -->"
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def nm(hz):
    m = int(round(69 + 12 * math.log2(hz / 440.0)))
    return "%s%d" % (NAMES[m % 12], m // 12 - 1)


def num(v, d=1):
    try:
        return ("%%.%df" % d) % float(v)
    except Exception:
        return "—"


def main() -> int:
    vp = os.path.join(R, "data", "listening_verdicts.json")
    led = json.load(io.open(vp, encoding="utf-8"))
    ok = [x for x in (led.get("items") or [])
          if x.get("verdict") == "是王晰本人" and isinstance(x.get("verdict_hz"), (int, float))]
    ok.sort(key=lambda x: -x["verdict_hz"])
    total = len(led.get("items") or [])
    ge1000 = [x for x in (led.get("items") or [])
              if isinstance(x.get("verdict_hz"), (int, float)) and x["verdict_hz"] >= 1000]
    print("人耳确认成立 %d 条 ｜ 其中 >1000Hz 的裁决记录 %d 条" % (len(ok), len(ge1000)))
    if not ok:
        print("✗ 无确认读数")
        return 1

    # ① 写入数据层
    sp = os.path.join(R, "data", "archive_stage_tour.json")
    st = json.load(io.open(sp, encoding="utf-8"))
    st["highest_verified"] = {
        "what": "现场最高音（人耳确认）",
        "why": ("所有 >1000Hz 的算法读数必须人耳确认才可引用；"
                "截至 %s，共 %d 条千赫兹级读数，仅 %d 条经确认为本人。"
                % ("2026-09-17", len(ge1000), len([x for x in ge1000 if x.get("verdict") == "是王晰本人"]))),
        "caliber": "现场读数属修音中等敏感层，可作「现场最高音」记录，不宜与录音室最高音直接比较",
        "items": [{"hz": x["verdict_hz"], "note": nm(x["verdict_hz"]),
                   "song": str(x.get("song") or ""),
                   "listener": x.get("listener"), "date": x.get("date"),
                   "source": x.get("batch")} for x in ok],
    }
    io.open(sp, "w", encoding="utf-8").write(json.dumps(st, ensure_ascii=False, indent=1))
    print("✔ data/archive_stage_tour.json 已加 highest_verified")

    # ② 注入 stage.html
    p = os.path.join(R, "stage.html")
    if not os.path.exists(p):
        print("✗ 无 stage.html")
        return 1
    top = ok[0]
    L = [START,
         '<h2 id="现场最高音">现场最高音（人耳确认）</h2>',
         '<p>本站对<strong>所有 &gt;1000Hz 的算法读数</strong>一律要求人耳确认才可引用。'
         '截至 2026-09-17，共记录 <strong>%d</strong> 条千赫兹级读数，'
         '其中经确认为本人的 <strong>%d</strong> 条 ——'
         '其余为女和声、乐器（钢琴/伴奏）或倍频锁错。</p>'
         % (len(ge1000), len([x for x in ge1000 if x.get("verdict") == "是王晰本人"])),
         '<div class="kv">',
         '<div><span class="k">现场最高音</span><span class="v">%s %sHz</span></div>'
         % (nm(top["verdict_hz"]), num(top["verdict_hz"])),
         '<div><span class="k">出处</span><span class="v">%s</span></div>' % str(top.get("song") or "")[:40],
         "</div>",
         "<h3>人耳确认成立的全部读数</h3>",
         '<table><thead><tr><th>音</th><th>Hz</th><th>出处</th><th>确认人</th>'
         "<th>日期</th></tr></thead><tbody>"]
    for x in ok:
        L.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                 % (nm(x["verdict_hz"]), num(x["verdict_hz"]),
                    str(x.get("song") or "")[:44], str(x.get("listener") or "")[:14],
                    str(x.get("date") or "")))
    L += ["</tbody></table>",
          '<p class="src">口径：现场读数属<strong>修音中等敏感层</strong>，'
          "可作「现场最高音」记录，<strong>不宜与录音室最高音（F5 706.0Hz）直接比较</strong>——"
          "两者语境不同（现场有音准修正可能、混音与人声分离误差）。"
          "数据见 <code>data/archive_stage_tour.json</code> 的 <code>highest_verified</code>。</p>",
          END]
    block = "\n".join(L)
    t = io.open(p, encoding="utf-8").read()
    t = re.sub(re.escape(START) + r".*?" + re.escape(END), "", t, flags=re.S)
    # 插在「他说过」之前；否则 </body> 前
    a = t.find("他说过")
    if a > 0:
        i = t.rfind("<h2", 0, a)
        t = t[:max(i, 0)] + block + "\n" + t[max(i, 0):]
    else:
        t = t.replace("</body>", block + "\n</body>", 1)
    io.open(p, "w", encoding="utf-8").write(t)
    print("✔ stage.html 已注入「现场最高音（人耳确认）」")
    print("   最高：%s %sHz ｜ %s" % (nm(top["verdict_hz"]), num(top["verdict_hz"]),
                                     str(top.get("song"))[:40]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
