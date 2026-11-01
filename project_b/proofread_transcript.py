"""转写校对辅助：标出可疑片段，方便人工快速过一遍

用法：python -X utf8 project_b/proofread_transcript.py "<转写文件路径>"
输出：同目录 <name>_校对清单.md（按可疑度排序，带时间码）
"""
import os
import re
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8", errors="ignore").read()
lines = [l for l in text.splitlines() if l.startswith("[")]
print("转写行数", len(lines))

PATTERNS = [
    ("数字/年份", re.compile(r"\d|[一二三四五六七八九十]{2,}(年|月|日|岁|场)")),
    ("英文/字母", re.compile(r"[A-Za-z]{2,}")),
    ("重复字", re.compile(r"([\u4e00-\u9fff])\1\1")),
    ("疑似错名", re.compile(r"王熙|王西|希哥|印象家|声入人新|沉想|沈想|秦毅|胖叔叔")),

    ("超短碎片", re.compile(r"^\[\d{2}:\d{2}\]\s*.{1,4}$")),
    ("疑似人名/歌名", re.compile(r"《[^》]{1,12}》")),
    ("口头重复", re.compile(r"(就是就是|然后然后|这个这个|那个那个)")),
]

try:
    import opencc
    _cc = opencc.OpenCC("t2s")
except Exception:
    _cc = None

hits = []
for i, l in enumerate(lines):
    body = re.sub(r"^\[\d{2}:\d{2}\]", "", l)
    tags = [name for name, pat in PATTERNS if pat.search(body)]
    if _cc and _cc.convert(body) != body:
        tags.append("繁体残留")
    if tags:
        hits.append((len(tags), i, l.strip(), tags))

hits.sort(key=lambda x: -x[0])
out = os.path.splitext(path)[0] + "_校对清单.md"
with open(out, "w", encoding="utf-8") as f:
    f.write("# 校对清单（%d 行中转写，%d 行可疑）\n\n" % (len(lines), len(hits)))
    f.write("| 时间码 | 问题类型 | 原文 |\n|---|---|---|\n")
    for score, i, l, tags in hits[:120]:
        f.write("| %s | %s | %s |\n" % (l[:8], "、".join(tags), l[9:].replace("|", "／")[:70]))

from collections import Counter
c = Counter(t for _, _, _, tags in hits for t in tags)
print("可疑行", len(hits), "| 类型分布", dict(c))
print("清单:", out)
