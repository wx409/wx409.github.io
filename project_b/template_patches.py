#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大屏生成器模板补丁 · 唯一入口（母版 E:\\wx → 仓库快照 project_b）

为什么要有这个脚本
  `dashboard/index.html` 是生成物，每次自动部署都会按母版重写；手工改仓库里的 index.html 会被覆盖。
  而母版（E:\\wx）与仓库快照（project_b）又是两份文件——两边各改各的，就会出现
  「补丁只在一份里、下一次同步被冲掉」的漂移。

本脚本做的事（一处改动，全局生效）
  1. 只对**母版**打补丁，补丁全部是「幂等 ensure」：已存在就跳过，不存在才插入/替换；
  2. 打完把母版复制成仓库快照 project_b，并校验 sha256 一致；
  3. 任何锚点找不到 → 退出码 1（部署链会红灯，不需要人盯着看）。

用法
  python -X utf8 project_b\\template_patches.py --check   # 只检查，不写
  python -X utf8 project_b\\template_patches.py           # 打补丁 + 同步快照
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = Path(r"E:\wx\QQ音乐大屏生成器_GEO优化版_源码.py")
SNAPSHOT = ROOT / "project_b" / "QQ音乐大屏生成器_GEO优化版_源码.py"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


# ── 补丁定义 ────────────────────────────────────────────────────────────
# 每条：(id, 说明, 存在性判据, 锚点, 插入内容, 是否替换锚点)
PATCHES = [
    ("story-link", "顶部「数据故事」入口",
     'href="story.html"',
     '<a class="open-data-link" href="monthly.html"',
     '<a class="open-data-link" href="story.html" title="数据故事：结构/描述/排序/预测/单曲">📖 数据故事 ↗</a>\n    ',
     False),
    ("monthly-link", "顶部「月度事件脉络」入口",
     'href="monthly.html"',
     '<a class="open-data-link" href="dashboard_data.json"',
     '<a class="open-data-link" href="monthly.html" title="月度事件脉络：热度曲线 + 异常月归因">📅 月度事件脉络 ↗</a>\n    ',
     False),
    ("monthly-mini", "首屏月度迷你图",
     "monthlyMini",
     '<div class="chart-box" id="esBox"',
     None,   # 见下方 MINI_BLOCK
     False),
]


MINI_BLOCK = '''<div class="chart-box" id="monthlyBox" style="margin-bottom:14px;">
    <h2 class="chart-title">📅 月度事件脉络 · 每月变化与异常月归因
      <a href="monthly.html" style="font-size:13px;font-weight:400;color:#7fb0ff;margin-left:10px;text-decoration:none">见完整页（含归因表）→</a></h2>
    <p class="chart-insight">按月看更稳：异常月（稳健 z≥2.5 或环比≥20%）自动标出，并列出同月/前一月的巡演、演出晚会、新歌发行作为候选解释。</p>
    <div id="monthlyMini" style="width:100%;height:230px"></div>
  </div>
  '''


def apply_patches(text: str, check_only: bool):
    applied, skipped, drift = [], [], []
    for pid, desc, probe, anchor, insert, replace in PATCHES:
        if probe in text:
            skipped.append(pid)
            continue
        if anchor not in text:
            drift.append((pid, desc))
            continue
        if pid == "monthly-mini":
            insert = MINI_BLOCK
        if check_only:
            applied.append((pid, desc))     # 只报告「需要补」
            continue
        text = text.replace(anchor, insert + anchor, 1)
        applied.append((pid, desc))
    return text, applied, skipped, drift


def external_checks(text: str):
    """别处维护的补丁：只检查在不在，不在就报漂移（由对应脚本负责补）。"""
    checks = [
        ("analysis-v2-link", "「重算」页链接（analysis 组维护）", "analysis-v2.html"),
        ("es-heading", "事件研究标题（analysis 组维护）", "仅 T+，缺前窗"),
        ("caliber-note", "巡演带动口径标注（analysis 组维护）", "非「同场对照」"),
    ]
    return [(cid, desc) for cid, desc, probe in checks if probe not in text]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not MASTER.exists():
        print("[FAIL] 母版不存在：", MASTER)
        return 1
    text = MASTER.read_text(encoding="utf-8")
    new, applied, skipped, drift = apply_patches(text, args.check)
    ext = external_checks(new)

    print("母版：%s（sha %s）" % (MASTER, sha(MASTER)))
    if skipped:
        print("  已存在，跳过：", "、".join(skipped))
    if applied:
        print("  %s：%s" % ("待补" if args.check else "已补",
                           "、".join(d for _, d in applied)))
    if drift:
        for pid, desc in drift:
            print("  [DRIFT] 锚点丢失：%s（%s）" % (desc, pid))
    if ext:
        print("  [DRIFT] 外维护补丁缺失：", "、".join(d for _, d in ext))

    if drift or ext:
        print("结论：存在漂移，退出码 1（部署链应红灯）")
        return 1

    if not args.check and applied:
        MASTER.write_text(new, encoding="utf-8", newline="")
        print("  母版已更新")
    elif not args.check:
        print("  母版无变化")

    if not args.check:
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MASTER, SNAPSHOT)
        same = sha(MASTER) == sha(SNAPSHOT)
        print("  快照同步：%s（sha %s）" % ("一致" if same else "不一致！", sha(SNAPSHOT)))
        if not same:
            return 1

    print("结论：一致 ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
