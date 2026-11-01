"""专名对照：把字幕 OCR 与 ASR 里出现的书名号/人名候选并排列出，供一次性确认"""
import collections
import json
import os
import re

BASE = r"E:\wx\私有\王晰全文库\采访目录\全文"
asr = os.path.join(BASE, "5128145411770407_转写_turbo.txt")
sub = os.path.join(BASE, "5128145411770407_转写_turbo_字幕校正版.txt")
out = os.path.join(BASE, "专名对照_待确认.md")

a = open(asr, encoding="utf-8", errors="ignore").read()
s = open(sub, encoding="utf-8", errors="ignore").read()

ta = collections.Counter(re.findall(r"《([^》]{1,12})》", a))
ts = collections.Counter(re.findall(r"《([^》]{1,12})》", s))

names = ["王晰", "王熙", "王熹", "王娇", "王听", "胖蜀黍", "胖叔", "崔迪", "秦屹", "流水纪", "流水季"]

rows = []
for k in sorted(set(ta) | set(ts)):
    rows.append((k, ta.get(k, 0), ts.get(k, 0)))

with open(out, "w", encoding="utf-8") as f:
    f.write("# 专名对照（字幕OCR vs 转写ASR）\n\n")
    f.write("同一首歌/专辑在两边的写法并排，请确认哪个正确（打 √ 或写正确写法）。\n\n")
    f.write("| 写法 | 字幕OCR次数 | 转写次数 | 判断 |\n|---|---|---|---|\n")
    for k, na, ns in sorted(rows, key=lambda x: -(x[1] + x[2])):
        f.write("| %s | %d | %d |  |\n" % (k, na, ns))
    f.write("\n## 人名候选\n\n| 写法 | 转写中次数 |\n|---|---|\n")
    for n in names:
        f.write("| %s | %d |\n" % (n, a.count(n)))

print("条目", len(rows), "→", out)
for k, na, ns in sorted(rows, key=lambda x: -(x[1] + x[2]))[:12]:
    print("  %-10s 字幕%d 转写%d" % (k, na, ns))
