"""检查：还有哪些脚本从 calibers.json 读数字时带了「默认值」兜底

（CLI 参数默认值不算——那是运行参数，不是口径）
"""
import io
import os
import re

ROOT = r"D:\wx409.github.io"
SKIP = {".git", "node_modules", "__pycache__", "temp", "logs"}

CAL = re.compile(r"calibers\.json|CAL\b|calibers_data|cal\(|cal_str\(|cal_num\(")
DEF = re.compile(r"\.get\(\s*[\"'][\w]+[\"']\s*,\s*(\d)")
ALT = re.compile(r"cal\(\s*[\"'][\w]+[\"'][^)]*default\s*=\s*(\d)")

hits = []
for base, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for f in files:
        if not f.endswith(".py"):
            continue
        p = os.path.join(base, f)
        s = io.open(p, encoding="utf-8", errors="ignore").read()
        if "caliber" not in s.lower() and "cal(" not in s:
            continue
        for m in ALT.finditer(s):
            hits.append((os.path.relpath(p, ROOT), "cal(default=N)", s[max(0, m.start() - 40):m.start() + 60].replace("\n", " ")))
        for m in DEF.finditer(s):
            seg = s[max(0, m.start() - 60):m.start() + 60].replace("\n", " ")
            if "caliber" in s.lower():
                hits.append((os.path.relpath(p, ROOT), ".get(key, N)", seg))

print("疑似「读口径时带数字兜底」%d 处\n" % len(hits))
for f, kind, seg in hits[:40]:
    print("[%s] %-40s %s" % (kind, f[:40], seg[:92]))
