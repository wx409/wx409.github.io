# -*- coding: utf-8 -*-
"""从三处现状派生 pipeline_registry.json（任务登记表）。

这不是"手写清单"，而是**派生 + 校验**模型：
  · 本脚本从 deploy_all STEPS / 操作中心.bat / Windows 计划任务 派生登记表（带人工字段保留）
  · audit_pipeline.py 再把四处描述放一起比对，任何漂移 exit 1
  · build_pipeline_views.py 由登记表生成 任务安装脚本 / 任务登记表.md / skill 表格

人工补充的字段（hand 段）在重派生时保留：`origin`（来源说明）、`layer`（层级语义）、`retire`（计划下线）。

用法：python -X utf8 project_b/seed_pipeline_registry.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "project_b" / "pipeline_registry.json"
BAT = ROOT / "操作中心.bat"

SEARCH = [
    ROOT, ROOT / "project_b", ROOT / "tools", ROOT / "tavern", ROOT / "temp",
    Path(r"E:\wx\论文素材_王晰作传\音域分析"), Path(r"E:\wx\论文素材_王晰作传\音域分析\轨迹"),
    Path(r"E:\wx\论文素材_王晰作传\基线口径"), Path(r"E:\wx\私有工具\weibo_proxy"),
    Path(r"E:\wx\私有工具\xhs_proxy"), Path(r"E:\wx\wx_textmine"), Path(r"E:\wx\私有工具"),
]
SCRIPT_RE = re.compile(r"^[\w\u4e00-\u9fa5\-]+\.py$")
_RECURSIVE: dict[str, str] = {}


def _recursive_index() -> dict[str, str]:
    """仓库内一次性建索引（只做一次，用于 temp/ 等散落脚本）。"""
    if not _RECURSIVE:
        for p in ROOT.rglob("*.py"):
            _RECURSIVE.setdefault(p.name, str(p))
    return _RECURSIVE


def resolve(name: str) -> str:
    """把脚本名解析成真实路径（找不到返回空）。"""
    if not SCRIPT_RE.match(name):
        return ""
    rel = name.lstrip("_")
    for d in SEARCH:
        for cand in (d / name, d / rel):
            if cand.exists():
                return str(cand)
    return _recursive_index().get(name) or _recursive_index().get(rel) or ""


def deploy_steps() -> list[dict]:
    t = (ROOT / "project_b" / "deploy_all.py").read_text(encoding="utf-8")
    block = t.split("STEPS = [", 1)[1].split("\n]", 1)[0]
    out = []
    for line in block.splitlines():
        line = line.strip().rstrip(",")
        if not line.startswith("("):
            continue
        m = re.search(r'"([^"]+\.py)"\s*,\s*"([^"]*)"\s*,\s*(True|False)', line)
        if m:
            out.append({"script": Path(m.group(1)).name, "desc": m.group(2),
                        "critical": m.group(3) == "True"})
    return out


def bat_state():
    raw = BAT.read_bytes().decode("gbk")
    menu = {int(m.group(1)): m.group(2).strip() for m in re.finditer(r'^echo\s+(\d+)\.\s*(.+?)\s*$', raw, re.M)}
    disp = {int(m.group(1)): m.group(2) for m in re.finditer(r'if "%op%"=="(\d+)" goto (\w+)', raw)}
    labels = {}
    for m in re.finditer(r'^:(\w+)\s*$(.*?)(?=^:\w+\s*$|\Z)', raw, re.M | re.S):
        body = m.group(2)
        scripts = []
        for s in re.findall(r'[\w\u4e00-\u9fa5\-]+\.py', body):
            if SCRIPT_RE.match(s) and s not in scripts:
                scripts.append(s)
        labels[m.group(1)] = scripts[:3]
    return menu, disp, labels


def scheduled() -> list[dict]:
    out = []
    r = subprocess.run(["schtasks", "/query", "/fo", "csv"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    for line in (r.stdout or "").splitlines()[1:]:
        if "wx409" not in line:
            continue
        name = line.split(",")[0].strip('"').lstrip("\\")
        q = subprocess.run(["schtasks", "/query", "/tn", name, "/fo", "list", "/v"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        info = {}
        for ln in q.stdout.splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                info[k.strip()] = v.strip()
        cmd = info.get("Task To Run", "")
        m = re.search(r'([\w\u4e00-\u9fa5\-]+\.py)', cmd)
        out.append({"name": name, "cmd": cmd, "next": info.get("Next Run Time", ""),
                    "schedule_type": info.get("Schedule Type", ""), "start": info.get("Start Time", ""),
                    "script": m.group(1) if m else ""})
    return out


def main() -> int:
    hand = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
            hand = {t.get("script") or t.get("id"): {k: v for k, v in t.items()
                                                    if k in ("origin", "layer", "retire", "notes")}
                    for t in old.get("tasks", [])}
        except Exception:
            hand = {}

    reg: dict[str, dict] = {}
    for s in deploy_steps():
        e = reg.setdefault(s["script"], {"script": s["script"]})
        e.update({"in_deploy": True, "deploy_desc": s["desc"], "critical": s["critical"]})
    menu, disp, labels = bat_state()
    for num, title in menu.items():
        lab = disp.get(num)
        scripts = labels.get(lab or "", [])
        key = scripts[0] if scripts else f"menu:{num}"
        e = reg.setdefault(key, {"script": key})
        e.update({"menu": num, "title": title, "menu_label": lab})
    for t in scheduled():
        key = t["script"] or f"task:{t['name']}"
        e = reg.setdefault(key, {"script": key})
        e.update({"schedule": {"name": t["name"], "script": t["script"], "cmd": t["cmd"],
                               "next": t["next"], "type": t["schedule_type"], "start": t["start"]}})

    for k, e in reg.items():
        e.setdefault("in_deploy", False)
        e["path"] = resolve(e["script"]) or e.get("path", "")
        e.update(hand.get(k, {}))

    doc = {
        "schema": 1,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "model": "派生 + 校验：seed 本表 ← 三处现状；audit_pipeline.py 四处比对；build_pipeline_views.py 生成视图",
        "sources": {"menu_items": len(menu), "dispatch": len(disp),
                    "deploy_steps": len(deploy_steps()), "scheduled_tasks": len(scheduled())},
        "tasks": sorted(reg.values(), key=lambda x: (x.get("menu") or 9999, x.get("script") or "")),
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    resolved = sum(1 for t in doc["tasks"] if t.get("path"))
    print(f"[OK] {OUT.name}｜任务 {len(doc['tasks'])} 条｜脚本定位成功 {resolved}")
    print(f"     来源：菜单 {len(menu)}｜分派 {len(disp)}｜部署步骤 {len(deploy_steps())}｜计划任务 {len(scheduled())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
