# -*- coding: utf-8 -*-
"""音域三页数据同步器 —— 输入有变化才跑生产脚本，无变化秒退（幂等、可每日自动跑）。

背景：voice.html / skill.html / stage.html 三个页面本身有生成器，但它们的**输入数据**
（data/archive_vocal*.json、archive_stage.json、archive_context_compare.json、
archive_crosscheck.json、archive_stage_tour.json、skill_cards.json）只在手工跑
`音域分析/` 那批生产脚本时才会变。本脚本把这一步接进每日自动链路：

  1) 逐条判断「生产脚本的输出是否比全部输入旧」→ 只跑过期的；
  2) 跑完生产脚本后，页面重建交给 deploy_all 的既有步骤（build_stage_page /
     generate_voice_page / build_skill_page），本脚本不重复造页面。

用法：
  python -X utf8 project_b/refresh_vocal_pages.py            # 仅补过期数据
  python -X utf8 project_b/refresh_vocal_pages.py --force    # 强制全跑
  python -X utf8 project_b/refresh_vocal_pages.py --check    # 只报告不执行
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ANA = Path(r"E:\wx\论文素材_王晰作传\音域分析")
BASE = Path(r"E:\wx\论文素材_王晰作传\基线口径")
PY = sys.executable

# (生产脚本, 说明, [输入 glob...], 输出 JSON)
# ⚠ 2026-09-11 事故后纪律：录音室层（archive_vocal_albums.json）**不进自动重算**。
#   原因：批量专辑音域.py 的默认 out_root 指向 v22 实验目录（分析结果_专辑），
#   自动重跑会把实验值并入汇总（曾把《知晓》B1 61.9 变成 C2 65.8、B1 由 4 首变 3 首）。
#   录音室层的重测必须人工确认后显式执行（操作中心 73 一键音域实测 / 71 专辑音域报告）。
PRODUCERS: list[tuple[Path, str, list[str], Path]] = [
    (ANA / "生成他人主导报告.py", "他人主导舞台汇总",
     [str(ANA / "他人主导" / "音频_汇总.json"), str(ANA / "他人主导" / "清单.json")], DATA / "archive_stage.json"),
    (ANA / "对比情境分析.py", "专辑 vs 舞台情境对比",
     [str(ANA / "专辑音域汇总.json"), str(ANA / "他人主导_汇总.json")], DATA / "archive_context_compare.json"),
    (ANA / "双重校验舞台vsQQ.py", "舞台版 vs QQ 官方版双重校验",
     [str(ANA / "他人主导" / "音频_汇总.json"), str(ANA / "舞台对照QQ_汇总.json")], DATA / "archive_crosscheck.json"),
    (ANA / "轨迹" / "生成巡演现场报告.py", "王晰主导巡演现场层",
     [str(ANA / "场次音频" / "wav_分析" / "**" / "*_stats.json"), str(ANA / "轨迹" / "A3复核交付表.json"),
      str(DATA / "albums.json"), str(DATA / "setlists.json")], DATA / "archive_stage_tour.json"),
    (BASE / "generate_vocal.py", "十曲精测音域谱",
     [str(ANA / "复核_十曲严格口径.json"), str(ANA / "轨迹" / "A3复核交付表.json")], DATA / "archive_vocal.json"),
]

# 明确不自动重算的生产脚本（人工显式执行，见文件头事故说明）
MANUAL_ONLY = {
    "生成专辑音域报告.py": "录音室层（72 曲）——须人工确认后跑 操作中心 71/73，避免 v22 实验目录污染",
}


def newest_mtime(patterns: list[str]) -> float:
    newest = 0.0
    for pat in patterns:
        for f in glob.glob(pat, recursive=True):
            try:
                newest = max(newest, os.path.getmtime(f))
            except OSError:
                pass
    return newest


def stale(inputs: list[str], output: Path) -> tuple[bool, str]:
    if not output.exists():
        return True, "输出缺失"
    src = newest_mtime(inputs)
    if src == 0.0:
        return False, "无输入（跳过，避免用缺失源重建）"
    return (src > output.stat().st_mtime), ("输入更新" if src > output.stat().st_mtime else "已最新")


def run(script: Path, desc: str) -> bool:
    if not script.exists():
        print(f"  [SKIP] {desc}：脚本不存在 {script}")
        return False
    r = subprocess.run([PY, "-X", "utf8", str(script)], cwd=str(script.parent),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode == 0:
        print(f"  [OK  ] {desc}")
        return True
    print(f"  [FAIL] {desc}（退出码 {r.returncode}）")
    tail = (r.stderr or r.stdout or "").strip().splitlines()[-3:]
    for line in tail:
        print(f"         {line}")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    print("=" * 64)
    print("音域三页数据同步器（输入变化驱动，幂等）")
    ran = skipped = failed = 0
    for script, desc, inputs, output in PRODUCERS:
        if script.name in MANUAL_ONLY:
            print(f"  [MAN ] {desc}：人工执行（{MANUAL_ONLY[script.name]}）")
            skipped += 1
            continue
        need, why = (True, "--force") if args.force else stale(inputs, output)
        if not need:
            print(f"  [--  ] {desc}：{why}")
            skipped += 1
            continue
        print(f"  [RUN ] {desc}（{why}）")
        if args.check:
            ran += 1
            continue
        if run(script, desc):
            ran += 1
        else:
            failed += 1
    print("-" * 64)
    print(f"执行 {ran}｜跳过 {skipped}｜失败 {failed}（失败不阻塞主链路，页面沿用上一版数据）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
