# -*- coding: utf-8 -*-
"""任务一致性审计：登记表 ↔ deploy_all ↔ 操作中心.bat ↔ Windows 计划任务。

背景：同一批任务原来有四处描述（手写菜单 121 项 / deploy_all STEPS / skill 文档 / 计划任务），
必然漂移——已发生过：`build_skill_page` 漏在 deploy_all（skill.html 长期不更新）、
3 个 show_feedback 计划任务停跑无人发现。

本审计用**与派生脚本同一套解析器**（seed_pipeline_registry），把四处描述放一起比对，漂移即 exit 1。

用法：python -X utf8 project_b/audit_pipeline.py [--quiet]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "project_b" / "pipeline_registry.json"
BAT = ROOT / "操作中心.bat"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seed_pipeline_registry import deploy_steps, resolve  # noqa: E402


def bat_state():
    raw = BAT.read_bytes().decode("gbk")
    menu = {int(m.group(1)) for m in re.finditer(r'^echo\s+(\d+)\.\s', raw, re.M) if int(m.group(1)) != 0}
    disp = {int(m.group(1)) for m in re.finditer(r'if "%op%"=="(\d+)" goto \w+', raw)}
    labels = {m.group(1) for m in re.finditer(r'^:(\w+)\s*$', raw, re.M)}
    return menu, disp, labels, raw


def tasks_state() -> dict[str, str]:
    out = {}
    r = subprocess.run(["schtasks", "/query", "/fo", "csv"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    for line in (r.stdout or "").splitlines()[1:]:
        if "wx409" not in line:
            continue
        name = line.split(",")[0].strip('"').lstrip("\\")
        q = subprocess.run(["schtasks", "/query", "/tn", name, "/fo", "list", "/v"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        cmd = next((l.split(":", 1)[1].strip() for l in q.stdout.splitlines() if l.startswith("Task To Run")), "")
        m = re.search(r'([\w\u4e00-\u9fa5\-]+\.py)', cmd)
        out[name] = m.group(1) if m else ""
    return out


def main() -> int:
    quiet = "--quiet" in sys.argv
    doc = json.loads(REG.read_text(encoding="utf-8"))
    tasks = {t["script"]: t for t in doc["tasks"] if t.get("script")}
    problems: list[str] = []

    dep = {s["script"] for s in deploy_steps()}
    reg_dep = {s for s, t in tasks.items() if t.get("in_deploy")}
    for s in sorted(reg_dep - dep):
        problems.append(f"登记表标了 in_deploy，但 deploy_all 里没有：{s}")
    for s in sorted(dep - reg_dep):
        problems.append(f"deploy_all 里有步骤，但登记表未标 in_deploy：{s}")
    if not quiet:
        print(f"[1] deploy_all 步骤 {len(dep)} 个｜登记表 in_deploy {len(reg_dep)} 个")

    menu, disp, labels, raw = bat_state()
    reg_menu = {t["menu"] for t in tasks.values() if t.get("menu")}
    for n in sorted(reg_menu - menu):
        problems.append(f"登记表有菜单号 {n}，bat 菜单里没有")
    for n in sorted(menu - disp):
        problems.append(f"bat 菜单 {n} 没有对应的 goto 分派（点了无响应）")
    for n in sorted(disp - menu):
        problems.append(f"bat 分派 {n} 没有菜单项（死分派）")
    for m in re.finditer(r'if "%op%"=="(\d+)" goto (\w+)', raw):
        if m.group(2) not in labels:
            problems.append(f"bat goto 目标缺失：{m.group(2)}（来自 {m.group(1)}）")
    if not quiet:
        print(f"[2] bat 菜单 {len(menu)} 项｜分派 {len(disp)} 项｜标签 {len(labels)} 个")

    live = tasks_state()
    reg_sched = {t["schedule"]["name"]: s for s, t in tasks.items() if t.get("schedule")}
    for name in sorted(set(reg_sched) - set(live)):
        problems.append(f"登记表有计划任务但系统里不存在：{name}")
    for name in sorted(set(live) - set(reg_sched)):
        problems.append(f"系统里有计划任务但登记表没有：{name}（脚本 {live[name]}）")
    for name in sorted(set(live) & set(reg_sched)):
        want, got = reg_sched[name], live[name]
        if want and got and Path(want).name != got:
            problems.append(f"计划任务 {name} 脚本不一致：登记表 {want} ≠ 实际 {got}")
    if not quiet:
        print(f"[3] 计划任务 {len(live)} 个｜登记表登记 {len(reg_sched)} 个")

    missing = [s for s in tasks if not s.startswith(("menu:", "task:")) and not resolve(s)]
    for s in sorted(missing):
        problems.append(f"登记表引用的脚本不存在：{s}")
    if not quiet:
        print(f"[4] 登记表引用脚本 {len(tasks)} 个｜定位失败 {len(missing)} 个")

    print("-" * 64)
    if problems:
        print(f"结论：发现 {len(problems)} 处漂移（必须修，否则无法回答「哪份是真的」）")
        for p in problems[:40]:
            print("   ✗", p)
        return 1
    print("结论：四处描述一致 ✅（登记表 / deploy_all / 操作中心 / 计划任务）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
