#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""操作中心覆盖审计（audit_ops_coverage.py）：确保「每个需要手动触发的功能」都有菜单入口。

第一性原理：
  自动化流水线（deploy_all.py）覆盖的是"每次部署都要跑"的步骤；
  而人工按需触发的功能（口径审计、登记表、llms.txt、音域、事件效应修正…）
  必须在 `操作中心.bat` 里有稳定入口，否则下次要翻备忘找命令——这就是"知识没留下"。

本脚本检查两类：
  A. deploy_all.py 的关键步骤脚本 → 必须能被操作中心调用（直接引用，或由 39 号一键部署覆盖）
  B. 明确列为"人工功能"的脚本清单 → 必须在操作中心里有独立菜单项

用法：
  python project_b/audit_ops_coverage.py
退出码：0=覆盖完整；1=有缺口。
"""
from __future__ import annotations

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


def main() -> None:
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


if __name__ == "__main__":
    main()
