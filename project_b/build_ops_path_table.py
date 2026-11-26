# -*- coding: utf-8 -*-
import csv, json, re
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
s = (ROOT / "操作中心.bat").read_bytes().decode("gbk")
lines = s.splitlines()

menu, labels, disp = [], {}, {}
seen_menu = set()
for i, l in enumerate(lines):
    if l.strip().lower().startswith("rem"):
        continue
    m = re.match(r'echo\s+(\d+)\.\s*(.*)', l.strip())
    if m and int(m.group(1)) > 0 and int(m.group(1)) not in seen_menu:
        seen_menu.add(int(m.group(1)))
        menu.append((int(m.group(1)), m.group(2).strip()))
    m = re.match(r':([A-Za-z0-9_]+)', l.strip())
    if m:
        labels[m.group(1)] = i
for l in lines:
    m = re.search(r'if "%op%"=="(\d+)" goto (\S+)', l)
    if m:
        disp[int(m.group(1))] = m.group(2)

pat_abs = re.compile(r'([A-Za-z]:\\[^"\s&]+?\.(?:py|bat|ps1))', re.I)
pat_rel = re.compile(r'((?:project_b|tools|tavern)\\[^"\s&]+?\.(?:py|bat|ps1))', re.I)
pat_bare = re.compile(r'(?:^|\s)([A-Za-z0-9_.-]+\.py)(?:\s|$)', re.I)

rows = []
for n, label in menu:
    lab = disp.get(n, "")
    st = labels.get(lab, -1)
    scripts, cmds = [], []
    cwd = ""
    if st >= 0:
        for l in lines[st + 1:st + 50]:
            t = l.strip()
            if t.startswith("goto menu") or t.startswith("pause"):
                break
            if not t or t.startswith("echo") or t.startswith("cls"):
                continue
            cmds.append(t)
            m = re.match(r'cd\s+/d\s+"?([^"]+)"?', t, re.I)
            if m:
                cwd = m.group(1).strip()
        for c in cmds:
            found = []
            for pat in (pat_abs, pat_rel):
                found += [m.group(1) for m in pat.finditer(c)]
            for m in pat_bare.finditer(c):
                found.append(m.group(1))
            for x in found:
                if re.match(r'^[A-Za-z]:\\', x):
                    p = Path(x)
                elif "\\" in x:
                    p = (Path(cwd) / x) if cwd else (ROOT / x)
                elif cwd:
                    p = Path(cwd) / x
                else:
                    p = ROOT / x
                scripts.append(str(p))
    scripts = list(dict.fromkeys(scripts))
    rows.append({"no": n, "label": label, "sub": lab, "scripts": scripts,
                 "cmd": " ; ".join(cmds)[:500], "cwd": cwd})

reg = json.loads((ROOT / "project_b" / "pipeline_registry.json").read_text(encoding="utf-8"))
deploy = {x.get("script") for x in reg.get("tasks", []) if x.get("in_deploy")}
counts = {}
for r in rows:
    for x in r["scripts"]:
        counts[x] = counts.get(x, 0) + 1

ARCHIVE = {17, 18, 20, 108, 216, 217, 218, 282}
MERGE = {10, 11, 12, 202, 203, 204, 244, 245, 246, 248, 249, 250, 251, 100, 104, 109}
MERGE_STAGE = {54, 58, 60, 68, 71, 77, 79, 82, 160, 238}
for r in rows:
    n = r["no"]
    if not r["scripts"]:
        kind = "无脚本（手工/打开页面）"
    elif n in ARCHIVE:
        kind = "归档候选（一次性/旧流程）"
    elif n in MERGE or n in MERGE_STAGE:
        kind = "合并候选"
    elif any(Path(x).name in deploy for x in r["scripts"]):
        kind = "部署/流水线"
    else:
        kind = "手动"
    if len(set(r["scripts"])) > 1:
        kind += " · 多脚本"
    r["kind"] = kind
    r["path"] = " | ".join(r["scripts"])

out = ROOT / "docs" / "操作中心程序路径表_20261126.csv"
with out.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["编号", "菜单", "子程序", "工作目录", "脚本路径", "类型", "命令"])
    for r in rows:
        w.writerow([r["no"], r["label"], r["sub"], r["cwd"], r["path"], r["kind"], r["cmd"]])

md = ["# 操作中心程序路径表（2026-11-26）", "",
      "由 `操作中心.bat` 自动解析；共 %d 个菜单项。完整 CSV：`docs/操作中心程序路径表_20261126.csv`。" % len(rows), "",
      "| # | 菜单 | 子程序 | 路径 | 类型 |", "|---:|---|---|---|---|"]
for r in rows:
    md.append("| %d | %s | `%s` | %s | %s |" % (r["no"], r["label"].replace("|", "\\|"), r["sub"], r["path"].replace("|", "<br>") or "—", r["kind"]))
(ROOT / "docs" / "操作中心程序路径表_20261126.md").write_text("\n".join(md), encoding="utf-8")
print("rows", len(rows), "missing", sum(1 for r in rows if not r["scripts"]), "multi", sum(1 for r in rows if len(r["scripts"]) > 1))
