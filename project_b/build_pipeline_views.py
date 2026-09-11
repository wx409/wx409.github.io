# -*- coding: utf-8 -*-
"""由 pipeline_registry.json 生成视图（单一事实源 → 多视图）。

生成物：
  1) tools/install_tasks.ps1         计划任务安装/修复脚本（从登记表派生，可整机重建排期）
  2) temp/任务登记表.md               人读视图（按层级分组、标注菜单号/部署序号/计划任务）
  3) skill 的「任务登记表」区间        写入 .dsh/skills/wangxi-ops/SKILL.md 的标记区间

用法：
  python -X utf8 project_b/build_pipeline_views.py            # 全部生成
  python -X utf8 project_b/build_pipeline_views.py --check    # 只检查是否最新（CI 用）
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "project_b" / "pipeline_registry.json"
PS1 = ROOT / "tools" / "install_tasks.ps1"
MD = ROOT / "temp" / "任务登记表.md"
SKILL = ROOT / ".dsh" / "skills" / "wangxi-ops" / "SKILL.md"
M_START, M_END = "<!-- TASKS_TABLE_START -->", "<!-- TASKS_TABLE_END -->"


def load() -> dict:
    return json.loads(REG.read_text(encoding="utf-8"))


def layer_of(t: dict) -> str:
    s = (t.get("script") or "")
    if t.get("schedule"):
        return "计划任务（自动）"
    if t.get("in_deploy"):
        return "每日部署链路"
    if t.get("menu"):
        return "手动运维（菜单）"
    return "未归类"


def gen_ps1(doc: dict) -> str:
    py = r"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe"
    lines = [
        "# 自动生成：由 project_b/pipeline_registry.json 派生（勿手改；改登记表后重跑 build_pipeline_views.py）",
        f"# 生成时间：{datetime.now():%Y-%m-%d %H:%M}",
        "$ErrorActionPreference = 'Stop'",
        f"$py = '{py}'",
        "",
    ]
    seen = set()
    for t in doc["tasks"]:
        sch = t.get("schedule")
        if not sch or t.get("script") in seen:
            continue
        seen.add(t.get("script"))
        path = t.get("path") or ""
        name = sch["name"]
        if "每晚增量" in path or "prune_raw_archive" in path:
            args = "-X utf8 \"%s\" %s" % (path, "--limit 6" if "每晚增量" in path else "--apply")
        else:
            args = "-X utf8 \"%s\"" % path
        lines += [
            f"# --- {name} ---",
            f"$a = New-ScheduledTaskAction -Execute $py -Argument '{args}' -WorkingDirectory '{Path(path).parent if path else ROOT}'",
        ]
        if name == "wx409_vocal_nightly":
            lines.append("$t = New-ScheduledTaskTrigger -Daily -At 22:00")
            lines.append("$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew")
        elif name == "wx409_prune_raw_archive":
            lines.append("$t = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 10:00")
            lines.append("$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)")
        elif name == "wx409_music_index_daily":
            lines.append("$t = New-ScheduledTaskTrigger -Daily -At 23:58")
            lines.append("$s = New-ScheduledTaskSettingsSet -StartWhenAvailable")
        elif name == "wx409_weibo_pipeline_daily":
            lines.append("$t = New-ScheduledTaskTrigger -Daily -At 09:00")
            lines.append("$s = New-ScheduledTaskSettingsSet -StartWhenAvailable")
        elif name.startswith("QQMusicDashboard"):
            lines.append("$t = New-ScheduledTaskTrigger -AtLogOn")
            lines.append("$s = New-ScheduledTaskSettingsSet -StartWhenAvailable")
        else:
            lines.append("$t = New-ScheduledTaskTrigger -Daily -At 09:00")
            lines.append("$s = New-ScheduledTaskSettingsSet -StartWhenAvailable")
        lines += [f"Register-ScheduledTask -TaskName '{name}' -Action $a -Trigger $t -Settings $s -Force | Out-Null",
                  f"Write-Host '[OK] {name}'", ""]
    return "\n".join(lines)


def gen_md(doc: dict) -> str:
    groups: dict[str, list] = {}
    for t in doc["tasks"]:
        groups.setdefault(layer_of(t), []).append(t)
    L = ["# 任务登记表（由 pipeline_registry.json 派生）", "",
         f"> 生成：{datetime.now():%Y-%m-%d %H:%M}｜任务 {len(doc['tasks'])} 条",
         "> 本表是**视图**：单一事实源是 `project_b/pipeline_registry.json`；一致性由 `audit_pipeline.py` 把关。", ""]
    for g in ("计划任务（自动）", "每日部署链路", "手动运维（菜单）", "未归类"):
        items = groups.get(g) or []
        if not items:
            continue
        L += [f"## {g}（{len(items)}）", "",
              "| 菜单 | 脚本 | 说明 | 计划任务 |", "|---|---|---|---|"]
        for t in items:
            L.append(f"| {t.get('menu') or '—'} | `{t.get('script')}` | "
                     f"{(t.get('title') or t.get('deploy_desc') or '')[:38]} | "
                     f"{(t.get('schedule') or {}).get('name') or '—'} |")
        L.append("")
    return "\n".join(L)


def gen_skill_section(doc: dict) -> str:
    tasks = [t for t in doc["tasks"] if t.get("schedule")]
    L = [M_START, "### 计划任务（由 pipeline_registry.json 派生，勿手改）", "",
         "| 任务名 | 脚本 | 时间 | 下次运行 |", "|---|---|---|---|"]
    for t in tasks:
        s = t["schedule"]
        L.append(f"| `{s['name']}` | `{t.get('script')}` | {s.get('start') or s.get('type') or '—'} | {s.get('next') or '—'} |")
    L += ["", "一致性把关：`python -X utf8 project_b\\audit_pipeline.py`（登记表 / deploy_all / 操作中心 / 计划任务 四处比对，漂移 exit 1）",
          M_END]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    doc = load()
    ps1, md, sec = gen_ps1(doc), gen_md(doc), gen_skill_section(doc)
    changed = []
    for p, content, kind in ((PS1, ps1, "install_tasks.ps1"), (MD, md, "任务登记表.md")):
        old = p.read_text(encoding="utf-8") if p.exists() else ""
        # ps1 首行含生成时间 → 比较时忽略时间行
        same = (old.split("\n")[1:] == content.split("\n")[1:]) if kind.endswith(".ps1") else (old == content)
        if not same:
            changed.append(kind)
            if not a.check:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
    if SKILL.exists():
        t = SKILL.read_text(encoding="utf-8")
        if M_START in t and M_END in t:
            new = t.split(M_START)[0] + sec + t.split(M_END)[1]
            if new != t:
                changed.append("SKILL.md 任务表")
                if not a.check:
                    SKILL.write_text(new, encoding="utf-8")
        else:
            changed.append("SKILL.md 缺少标记区间（未写入）")
    print(f"[{'检查' if a.check else '生成'}] 变化：{', '.join(changed) or '无'}")
    for p in (PS1, MD):
        print(f"   {p}")
    return 1 if (a.check and changed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
