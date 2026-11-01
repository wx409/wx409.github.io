"""扫描全仓库：数字型兜底默认值（可能掩盖过期口径）

只报告「看起来是统计数字」的兜底：default=<数字>，并给出上下文与判定
"""
import io
import os
import re

ROOTS = [r"D:\wx409.github.io"]
SKIP_DIRS = {".git", "node_modules", "__pycache__", "temp", "logs", ".dsh"}

PAT = re.compile(r"default\s*=\s*(\d[\d_\.]*)")


def walk():
    for root in ROOTS:
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                if f.endswith((".py", ".js")):
                    yield os.path.join(base, f)


# 明显是统计口径的变量名特征
STAT_HINT = re.compile(r"(count|total|num|n_|_n$|days|shows|songs|cities|facts|entities|"
                       r"relations|semantic|qa|tracked|hz|sessions|episodes|plays|views)", re.I)
BENIGN = re.compile(r"(timeout|retry|retries|delay|sleep|limit|max_|min_|width|height|size|"
                    r"port|time|ms|seconds|page|top|round|precision|nd)", re.I)

rows = []
for p in walk():
    try:
        s = io.open(p, encoding="utf-8", errors="ignore").read()
    except Exception:
        continue
    for m in PAT.finditer(s):
        line_start = s.rfind("\n", 0, m.start()) + 1
        line_end = s.find("\n", m.end())
        line = s[line_start:line_end].strip()
        if "def " in line and "default=" in line and BENIGN.search(line):
            continue
        var = ""
        vm = re.search(r"([A-Za-z_][\w\.]*)\s*=\s*[\w\.]*\([^)]*$", s[line_start:m.start()])
        if vm:
            var = vm.group(1)
        stat = bool(STAT_HINT.search(line))
        benign = bool(BENIGN.search(line)) and not stat
        if benign:
            continue
        rows.append({"file": os.path.relpath(p, ROOTS[0]), "line": line[:110],
                     "value": m.group(1), "stat": stat})

rows.sort(key=lambda r: (not r["stat"], r["file"]))
print("可疑数字兜底 %d 处（其中像统计口径 %d 处）\n"
      % (len(rows), sum(1 for r in rows if r["stat"])))
for r in rows:
    tag = "口径" if r["stat"] else "  ? "
    print("[%s] %-46s %s" % (tag, r["file"][:46], r["line"][:96]))
