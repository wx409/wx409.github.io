"""从长转写里挑出「他讲创作/音乐观」的重点段落，供人工校对

用法：python -X utf8 project_b/pick_key_paragraphs.py "<转写文件>" [--top 10]
输出：同目录 <name>_重点段落.md
"""
import os
import re
import sys

path = sys.argv[1]
top_n = 10
if "--top" in sys.argv:
    top_n = int(sys.argv[sys.argv.index("--top") + 1])

lines = [l for l in open(path, encoding="utf-8", errors="ignore").read().splitlines() if l.startswith("[")]

# 合并成段：时段间隔 >2.5s 或累计 >160 字则断开
paras = []
cur, cur_t = [], None
prev_t = None
for l in lines:
    m = re.match(r"^\[(\d{2}):(\d{2})\]\s*(.*)$", l)
    if not m:
        continue
    t = int(m.group(1)) * 60 + int(m.group(2))
    txt = m.group(3).strip()
    if cur and (t - (prev_t or t) > 2 or sum(len(x) for x in cur) > 160):
        paras.append((cur_t, "".join(cur)))
        cur, cur_t = [], None
    if not cur:
        cur_t = "%02d:%02d" % (t // 60, t % 60)
    cur.append(txt)
    prev_t = t
if cur:
    paras.append((cur_t, "".join(cur)))

KEY = ["专辑", "创作", "音乐", "作品", "写歌", "录音", "编曲", "制作", "表达", "理解",
       "低音", "声音", "唱", "歌", "概念", "想法", "为什么", "我自己", "我觉得", "希望"]


def score(p):
    body = p[1]
    s = sum(body.count(k) for k in KEY)
    if len(body) < 40:
        s -= 3
    return s


# 去重：相邻段落若高度重复则保留一个
seen = set()
picked = []
for t, body in sorted(paras, key=score, reverse=True):
    sig = body[:18]
    if sig in seen:
        continue
    seen.add(sig)
    picked.append((t, body))
    if len(picked) >= top_n:
        break
picked.sort(key=lambda x: x[0])

out = os.path.splitext(path)[0] + "_重点段落.md"
with open(out, "w", encoding="utf-8") as f:
    f.write("# 重点段落（%s）\n\n" % os.path.basename(path))
    f.write("按时间码排序，共 %d 段。看这几段就行，不用通读。\n\n" % len(picked))
    for i, (t, body) in enumerate(picked, 1):
        f.write("## %d. [%s]\n\n%s\n\n" % (i, t, body))

print("段落总数", len(paras), "| 选出", len(picked))
print("输出:", out)
for t, body in picked[:3]:
    print("\n[%s] %s" % (t, body[:120]))
