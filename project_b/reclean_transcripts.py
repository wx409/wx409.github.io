"""按最新清洗规则重新过一遍已有转写（就地改写，原文件备份到 全文_清洗前）"""
import glob
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transcript_clean import clean_text, is_noise  # noqa: E402

T = r"E:\wx\私有\王晰全文库\采访目录\全文"
BAK = r"E:\wx\私有\王晰全文库\采访目录\全文_清洗前"
os.makedirs(BAK, exist_ok=True)

n_files = n_drop = 0
for f in sorted(glob.glob(os.path.join(T, "*转写_*.txt"))):
    raw = open(f, encoding="utf-8", errors="ignore").read()
    head, sep, body = raw.partition("\n\n")
    lines = [l for l in body.splitlines() if l.strip()]
    out = []
    for l in lines:
        m = re.match(r"^(\[\d{2}:\d{2}\])\s*(.*)$", l)
        if not m:
            continue
        ts, txt = m.group(1), clean_text(m.group(2))
        line = "%s %s" % (ts, txt)
        if is_noise(line):
            n_drop += 1
            continue
        out.append(line)
    if out == lines:
        continue
    bak = os.path.join(BAK, os.path.basename(f))
    if not os.path.exists(bak):
        shutil.copy2(f, bak)
    open(f, "w", encoding="utf-8").write(head + sep + "\n".join(out) + "\n")
    n_files += 1

print("重清洗文件 %d 个｜丢弃噪音行 %d" % (n_files, n_drop))
