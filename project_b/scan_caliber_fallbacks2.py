"""精确扫描：从 calibers 读数字时带兜底的调用（排除 CLI 参数）

判定：
  A) cal("xxx", ..., default=<数字>)        ← 真正的口径兜底
  B) CAL.get("xxx") ... 后面跟 or <数字>
  C) calibers.json 读出后 .get(key, <数字>)
"""
import io
import os
import re

ROOT = r"D:\wx409.github.io"
SKIP = {".git", "node_modules", "__pycache__", "temp", "logs"}

A = re.compile(r"cal\(\s*[\"'][\w]+[\"'][^)]*default\s*=\s*\d")
B = re.compile(r"CAL(?:IBERS)?\.get\(\s*[\"'][\w]+[\"'][^)]*\)\s*or\s+\d")
C = re.compile(r"(?:calibers|CALIBERS|CAL)\b[\s\S]{0,80}?\.get\(\s*[\"'][\w]+[\"']\s*,\s*\d")

found = []
for base, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for f in files:
        if not f.endswith(".py"):
            continue
        p = os.path.join(base, f)
        s = io.open(p, encoding="utf-8", errors="ignore").read()
        for label, rx in (("A cal(default=N)", A), ("B CAL.get or N", B), ("C calibers.get(k,N)", C)):
            for m in rx.finditer(s):
                seg = re.sub(r"\s+", " ", s[max(0, m.start() - 30):m.start() + 90])
                found.append((label, os.path.relpath(p, ROOT), seg))

print("真正「读口径带数字兜底」%d 处\n" % len(found))
seen = set()
for label, f, seg in found:
    k = (label, f, seg[:40])
    if k in seen:
        continue
    seen.add(k)
    print("[%s] %-42s %s" % (label, f[:42], seg[:88]))
