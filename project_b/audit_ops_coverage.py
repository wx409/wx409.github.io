#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""操作中心覆盖审计（audit_ops_coverage.py）：确保「每个需要手动触发的功能」都有菜单入口。

第一性原理：
  自动化流水线（deploy_all.py）覆盖的是"每次部署都要跑"的步骤；
  而人工按需触发的功能（口径审计、登记表、llms.txt、音域、事件效应修正…）
  必须在 `操作中心.bat` 里有稳定入口，否则下次要翻备忘找命令——这就是"知识没留下"。

本脚本检查三类：
  A. deploy_all.py 的关键步骤脚本 → 必须能被操作中心调用（直接引用，或由 39 号一键部署覆盖）
  B. 明确列为"人工功能"的脚本清单 → 必须在操作中心里有独立菜单项
  C. **反向检查（2026-09-15 新增）**：扫描 project_b/ · tools/ · 根目录下所有
     **带 `if __name__ == "__main__"` 的可运行脚本**，凡不属于
     「菜单 ∪ 部署链 ∪ 计划任务 ∪ 被其他脚本引用」的就报警。
     —— 起因：2026-09-14/15 新增 15 个声音素材脚本，**一个都没进菜单**，
     而 A/B 两类只校验"已登记项"，查不出"脚本在盘上却没入口"。

C 类分三档（默认全部只报警、不影响退出码，避免阻断每日发布）：
  · ALLOWLIST  —— 永久豁免（一次性修复脚本 / 被 import 的库 / 已被取代的迁移脚本）
  · BACKLOG    —— 已知应接入但尚未接入（显式登记，便于排期）
  · UNREGISTERED —— 既不在上面两档、也未登记的新脚本（**这才是真正要警觉的**）
加 `--strict` 时，只要三档里出现 UNREGISTERED 就退出码 1。

用法：
  python project_b/audit_ops_coverage.py
退出码：0=覆盖完整；1=有缺口。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BAT = ROOT / "操作中心.bat"

# 需要独立菜单入口的人工功能（脚本路径片段 → 说明）
MANUAL_FEATURES = {
    "project_b\\deploy_all.py": "完整部署（25 步）",
    "project_b\\audit_caliber.py": "口径审计",
    "project_b\\build_calibers.py": "口径登记表",
    "project_b\\build_facts.py": "事实登记表生成",
    "project_b\\check_facts_preflight.py": "事实预检（生成前）",
    "project_b\\build_nav.py": "导航统一",
    "project_b\\audit_nav.py": "导航与内链审计",
    "project_b\\audit_bat.py": "批处理体检",
    "基线口径\\generate_llms.py": "llms.txt 生成",
    "基线口径\\generate_vocal.py": "音域谱生成",
    "基线口径\\generate_voice_page.py": "voice.html 更新",
    "基线口径\\generate_propositions.py": "命题卡摘要",
    "基线口径\\compute_baseline_v1.py": "口径基线重算",
    "基线口径\\事件效应口径修正.py": "事件效应口径修正",
    "基线口径\\矛盾扫描器.py": "矛盾扫描",
    "wx_textmine\\00_build_matrix.py": "重建指数长表（含千分位修复）",
    "基线口径\\build_index_raw_long.py": "重建原始库长表",
    "基线口径\\指数数据源诊断.py": "指数数据源诊断",
    "project_b\\check_index_integrity.py": "指数数据源完整性守卫",
    "project_b\\build_academic.py": "学术研究页生成",
    "project_b\\build_stage_page.py": "舞台实测页生成",
    "音域分析\\生成他人主导报告.py": "他人主导详细报告",
    "音域分析\\批量下载专辑.py": "专辑音频下载",
    "音域分析\\批量专辑音域.py": "专辑音域实测",
    "音域分析\\生成专辑音域报告.py": "专辑音域报告",
    "音域分析\\添加待测曲目.py": "添加待测曲目",
    "音域分析\\一键音域实测.py": "一键音域实测",
    "音域分析\\抓取B站收藏夹.py": "抓取B站收藏夹清单",
    "音域分析\\下载他人主导音频.py": "下载他人主导音频",
    "音域分析\\对比情境分析.py": "情境对比分析",
    "音域分析\\复核十曲严格口径.py": "十曲严格口径复核",
    "音域分析\\匹配QQ官方版本.py": "匹配QQ官方版本",
    "音域分析\\双重校验舞台vsQQ.py": "双重校验舞台vsQQ",
    "音域分析\\重绘十曲图.py": "重绘十曲图",
    "音域分析\\轨迹\\搜索B站轨迹素材.py": "B站轨迹素材采集",
    "音域分析\\轨迹\\导出素材清单.py": "导出轨迹素材清单",
    "音域分析\\轨迹\\场次音域一键.py": "场次音域实测一键",
    "音域分析\\轨迹\\下载场次音频.py": "场次音轨下载",
    "音域分析\\轨迹\\场次音频准备.py": "音轨转wav与串烧切分",
    "音域分析\\轨迹\\场次音域报告.py": "场次双标准报告",
    "音域分析\\轨迹\\复核低音读数.py": "低音读数复核",
    "音域分析\\轨迹\\CREPE复核窗口.py": "CREPE 单窗复核",
    "音域分析\\轨迹\\诊断_低音归属.py": "低音归属四轨诊断",
    "音域分析\\轨迹\\CREPE全量复核.py": "CREPE 全量复核",
    "音域分析\\轨迹\\引擎稳健性复核.py": "引擎稳健性复核（多配置）",
    "音域分析\\轨迹\\A3终裁.py": "A3 终裁（谱列解释度）",
    "音域分析\\轨迹\\低音仲裁.py": "低音仲裁",
    "音域分析\\轨迹\\谱图取证.py": "谱图取证",
    "音域分析\\轨迹\\伴奏调性闭合.py": "伴奏调性闭合",
}

# ── C 类反向检查：永久豁免（脚本可运行，但按设计不需要菜单入口） ─────────────
ORPHAN_ALLOWLIST = {
    "dsh_llm.py": "被 import 的库（DSH 本地模型调用助手），__main__ 仅自测",
    "project_b\\data_pipeline.py": "遗留原型（自建 01_原始数据/02_清洗数据 旧目录），已被现行流水线取代",
    "project_b\\build_legacy_notes.py": "一次性迁移脚本 —— 页面生成器（generate_voice_page 等）已原生包含 NOTE 块",
    "project_b\\fix_songs_meta.py": "一次性数据修复（补 21 首歌词+班底），已执行完毕",
    "tools\\fix_activity_table_corrections.py": "一次性数据修复（按 2026-09-04 校对结果修正活动表），已执行完毕",
}

# ── C 类反向检查：已知应接入但尚未接入（显式登记，便于排期） ────────────────
ORPHAN_BACKLOG = {}   # 2026-09-15：原 6 项已全部接入（见 CHANGELOG）


def _under_git(p: Path) -> bool:
    """判断是否落在 .git 内。

    ⚠️ 只能对**相对路径**判断 —— 本仓库根目录叫 `wx409.github.io`，
    它本身含 `.git` 子串；若写成 `'.git' in str(绝对路径)` 会把**每个文件**都跳过
    （2026-09-15 踩过：扫描文件数恒为 0）。
    """
    try:
        parts = p.relative_to(ROOT).parts
    except ValueError:
        return True
    return any(x == ".git" for x in parts)


def _collect_runnable() -> list:
    """可运行脚本 = project_b/ · tools/ · 根目录下带 __main__ 入口的 .py。"""
    entry = re.compile(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]')
    out = []
    for d in ("project_b", "tools", ""):
        base = ROOT / d if d else ROOT
        if not base.is_dir():
            continue
        for f in sorted(base.glob("*.py")):
            if _under_git(f):
                continue
            try:
                if entry.search(f.read_text(encoding="utf-8", errors="replace")):
                    out.append(f)
            except Exception:
                continue
    return out


def _registered_names() -> set:
    """pipeline_registry（菜单 ∪ 部署 ∪ 计划任务）里的脚本名/路径。"""
    reg_p = ROOT / "project_b" / "pipeline_registry.json"
    names = set()
    try:
        reg = json.loads(reg_p.read_text(encoding="utf-8"))
    except Exception:
        return names
    for t in reg.get("tasks") or []:
        for k in ("script", "path", "file", "cmd"):
            v = t.get(k)
            if isinstance(v, str) and v.endswith(".py"):
                names.add(Path(v).name.lower())
                names.add(v.replace("/", "\\").lower())
    return names


def _reference_blob() -> list:
    """全仓库 .py/.bat/.md 文本（用于判断"是否被别的脚本调用/提到"）。

    ⚠️ 只在开头调用**一次**并复用 —— 若放进候选循环里就变成
    「候选数 × 全仓文件数」次读取（150 × 830 ≈ 12 万次），白拖慢每日部署。
    """
    blob = []
    for pat in ("**/*.py", "**/*.bat", "*.md", "docs/*.md"):
        for f in ROOT.glob(pat):
            if _under_git(f):
                continue
            enc = "gbk" if f.suffix.lower() == ".bat" else "utf-8"
            try:
                blob.append((f.resolve(), f.read_text(encoding=enc, errors="replace")))
            except Exception:
                continue
    return blob


def reverse_check(strict: bool) -> list:
    """C 类反向检查：可运行脚本是否可达。返回"真正未登记"的清单。"""
    print("-" * 68)
    print("反向检查：可运行脚本是否都有去处（菜单/部署/计划任务/被引用）")
    registered = _registered_names()
    cands = _collect_runnable()
    blob = _reference_blob()          # ← 只读一次，循环内复用
    allow = {k.lower() for k in ORPHAN_ALLOWLIST}
    back = {k.lower() for k in ORPHAN_BACKLOG}
    unreg, n_allow, n_back, n_ref = [], 0, 0, 0
    for f in cands:
        rel = str(f.relative_to(ROOT)).replace("/", "\\")
        low = rel.lower()
        if Path(rel).name.lower() in registered or low in registered:
            continue
        if low in allow:
            n_allow += 1
            continue
        if low in back:
            n_back += 1
            continue
        name, stem, me = f.name, f.stem, f.resolve()
        hit = False
        for gpath, txt in blob:
            if gpath == me:
                continue
            if name in txt or (len(stem) > 6 and stem in txt):
                hit = True
                break
        if hit:
            n_ref += 1
            continue
        unreg.append(rel)
    print(f"  可运行脚本 {len(cands)} 个｜豁免 {n_allow}｜待接入 {n_back}"
          f"｜被引用 {n_ref}｜**未登记 {len(unreg)}**")
    if ORPHAN_BACKLOG:
        print("  [待接入清单]（已知、待排期，见脚本内 ORPHAN_BACKLOG）")
        for k, why in ORPHAN_BACKLOG.items():
            print(f"    · {k} —— {why}")
    if unreg:
        print("  [未登记] 这些脚本可运行却没有任何入口，请补菜单/部署链或登记豁免：")
        for u in unreg:
            print(f"    ✗ {u}")
    else:
        print("  [未登记] 无 ✅")
    if strict and unreg:
        return [f"可运行脚本未登记 {len(unreg)} 个：{', '.join(unreg)}"]
    return []


def main() -> None:
    strict = "--strict" in sys.argv
    if not BAT.exists():
        print(f"[FAIL] 找不到 {BAT}")
        sys.exit(1)
    try:
        bat = BAT.read_text(encoding="gbk", errors="replace")
    except Exception:
        bat = BAT.read_text(encoding="utf-8", errors="replace")

    print("=" * 68)
    print("操作中心覆盖审计")
    print("=" * 68)

    missing = []
    for frag, label in MANUAL_FEATURES.items():
        # 同时接受反斜杠/正斜杠与仅文件名两种写法
        name = frag.split("\\")[-1]
        hit = (frag in bat) or (frag.replace("\\", "/") in bat) or (name in bat)
        flag = "OK  " if hit else "FAIL"
        print(f"[{flag}] {label:14s} {frag}")
        if not hit:
            missing.append(f"{label}（{frag}）")

    # 菜单项计数
    menu_items = re.findall(r"^\s*echo\s+(\d+)\.\s*(.+)$", bat, re.M)
    labels = set(re.findall(r"^\s*:([A-Za-z_][\w]*)", bat, re.M))
    gotos = set(re.findall(r"^\s*goto\s+:?([A-Za-z_][\w]*)", bat, re.M))
    print("-" * 68)
    print(f"菜单项：{len(menu_items)} 个｜标签：{len(labels)} 个｜goto 引用：{len(gotos)} 个")
    print(f"goto 目标缺失：{sorted(gotos - labels) or '无'}")
    if gotos - labels:
        missing.append(f"goto 目标缺失 {sorted(gotos - labels)}")

    print("-" * 68)
    if missing:
        print(f"结论：{len(missing)} 项功能没有菜单入口 —— 请补进操作中心.bat：")
        for m in missing:
            print("  -", m)
        sys.exit(1)
    print("结论：全部人工功能均有菜单入口 ✅")

    # ── C 类反向检查（默认只报警，不阻断每日发布；--strict 时才算失败）──
    extra = reverse_check(strict)
    if extra:
        sys.exit(1)


if __name__ == "__main__":
    main()
