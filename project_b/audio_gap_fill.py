#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audio_gap_fill.py —— 一到六巡音频缺口自动补全（可定时，无人值守）

一条命令做完：
  1 逐曲核对（song_coverage_audit）→ data/song_coverage_status.json
  2 缺口场次 ↔ 未收录 B站 视频（temp/up_missing.json）按「城市 + 全场/半场优先」配对
  3 音频-only 抓取（bili_best_fetch --video none）→ FLAC 入最优音频 + 追加 Excel
  4 再核对一遍，写 data/audio_gap_report.md（还缺哪些场/哪些歌）
  5 仍有缺口 → 推送通知（notify.py），避免忘了补

用法：
  python -X utf8 project_b/audio_gap_fill.py --max-shows 10
  python -X utf8 project_b/audio_gap_fill.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
PY = sys.executable
WHOLE = ("全场", "整场", "上半场", "下半场", "完整", "全程")


def run(script, *args):
    cmd = [PY, "-X", "utf8", str(ROOT / "project_b" / script), *args]
    print("  $", " ".join(cmd[2:]), flush=True)
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-shows", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-scan", action="store_true")
    ap.add_argument("--mode", default="auto", choices=["auto", "fill", "supplement"],
                    help="auto=缺口多则补全、缺口少先做质量补充")
    args = ap.parse_args()

    if not args.skip_scan:
        print("[1/5] 扫描 9 个 UP 的未收录视频（3 页）", flush=True)
        run("bili_scan_missing.py", "--pages", "3")

    print("[2/5] 逐曲核对覆盖", flush=True)
    run("song_coverage_audit.py")
    cov = json.loads((DATA / "song_coverage_status.json").read_text(encoding="utf-8"))
    miss = cov.get("missing") or []
    by_show = defaultdict(list)
    for m in miss:
        by_show[(m["tour"], m["date"], m["city"])].append(m["song"])
    print(f"      缺口场次 {len(by_show)}，缺口曲目 {len(miss)}", flush=True)

    if not miss:
        print("      已全覆盖，无需补全", flush=True)
        return 0

    # 3+4：两阶段策略
    #   fill（缺口多）：60 分钟以上整场优先，先把"每首都有"补齐
    #   supplement（缺口少）：质量优先，收 ≥200kbps 但当时没选中的音轨作补充
    mode = args.mode
    if mode == "auto":
        mode = "fill" if len(miss) > 60 else "supplement"
    print(f"      模式判定：{mode}（缺口 {len(miss)} 首）", flush=True)
    if not args.dry_run:
        if mode == "fill":
            print(f"[3/5] 补全：60min+ 整场优先，最多 {args.max_shows} 场", flush=True)
            run("bili_show_fill.py", "--from-gaps", "--limit", str(args.max_shows), "--top", "6")
        else:
            print(f"[3/5] 质量补充：≥200kbps 未选中的音轨，最多 {args.max_shows} 场", flush=True)
            run("bili_supplement.py", "--limit", str(args.max_shows), "--min-kbps", "200")
    else:
        print("[3/5] dry-run：跳过", flush=True)

    print("[5/5] 重新核对并写报告", flush=True)
    run("song_coverage_audit.py")
    cov = json.loads((DATA / "song_coverage_status.json").read_text(encoding="utf-8"))
    miss2 = cov.get("missing") or []
    by2 = defaultdict(int)
    for m in miss2:
        by2[f"{m['tour']} {m['date']} {m['city']}"] += 1
    rep = ["# 一到六巡音频缺口报告", "", f"> {datetime.now():%Y-%m-%d %H:%M}｜缺口曲目 {len(miss2)} 首 / 场次 {len(by2)}", ""]
    rep.append("| 场次 | 缺口曲目 |")
    rep.append("|---|---|")
    for k, v in sorted(by2.items(), key=lambda kv: -kv[1]):
        rep.append(f"| {k} | {v} |")
    (DATA / "audio_gap_report.md").write_text("\n".join(rep), encoding="utf-8")

    (DATA / "audio_gap_status.json").write_text(json.dumps(
        {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
         "missing_songs": len(miss2), "missing_shows": len(by2),
         "shows": dict(by2)}, ensure_ascii=False, indent=1), encoding="utf-8")

    if miss2 and not args.dry_run:
        try:
            sys.path.insert(0, str(ROOT / "project_b"))
            import notify
            notify.record("音频补全仍有缺口",
                          f"一到六巡还剩 {len(miss2)} 首 / {len(by2)} 场没有音频，详见 data/audio_gap_report.md",
                          category="运维告警", source="audio_gap_fill")
        except Exception as e:
            print("通知失败:", e)
    print(f"      剩余缺口 {len(miss2)} 首 / {len(by2)} 场", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
