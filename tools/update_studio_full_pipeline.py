# -*- coding: utf-8 -*-
"""工作室微博全量爬取后的“一站式全站更新”入口。

适用：你已经用 weibo_proxy_studio.py fetch --all 跑完 E:\\wx\\私有工具\\weibo_archive_studio，
现在希望把所有文本、活动、事件、网站页面、知识库重新同步一遍。

用法（在普通 PowerShell 中运行，需要有 E:\\wx 写权限）：
  python -X utf8 D:\\wx409.github.io\\tools\\update_studio_full_pipeline.py

常用参数：
  --no-llm       跳过 DeepSeek 事件提取（只做规则分类/聚类，生成人工候选）
  --no-site      跳过网站页面重建（live-reviews / deploy_all）
  --no-events    跳过活动/事件提取与活动表更新
  --no-commit    最后不自动 git commit（默认也不自动 push）
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
PROXY = Path(r"E:\wx\私有工具\weibo_proxy")
PY = sys.executable

LOG = ROOT / "logs" / ("studio_full_%s.log" % datetime.now().strftime("%Y%m%d_%H%M%S"))


def log(msg: str) -> None:
    line = "[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(desc: str, script: str, cwd: Path | None = None) -> bool:
    log("-- %s --" % desc)
    log("   %s" % script)
    try:
        r = subprocess.run(
            [PY, "-X", "utf8", script],
            cwd=cwd or ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60 * 60 * 6,
        )
    except Exception as e:
        log("   [异常] %s" % e)
        return False
    tail = [x for x in (r.stdout or "").splitlines() if x.strip()][-8:]
    for t in tail:
        log("   " + t)
    if r.returncode != 0:
        err = (r.stderr or "").strip().splitlines()
        if err:
            log("   [stderr] " + err[-1][:300])
        log("   [失败] 退出码 %s" % r.returncode)
        return False
    log("   [完成]")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true", help="跳过 DeepSeek 事件提取")
    ap.add_argument("--no-site", action="store_true", help="跳过网站页面重建")
    ap.add_argument("--no-events", action="store_true", help="跳过活动/事件提取")
    ap.add_argument("--no-commit", action="store_true", help="不自动 git commit")
    a = ap.parse_args()

    log("========== 工作室微博全量同步开始 ==========")

    # 1) 归档为文本语料文件夹
    if not run("整理工作室微博 -> weibo_merged/工作室微博", str(PROXY / "整理工作室.py"), cwd=PROXY):
        log("整理工作室.py 失败，继续尝试完整归档")
    if not run("完整归档 -> weibo_merged/工作室微博_完整", str(PROXY / "archive_studio_full.py"), cwd=PROXY):
        log("archive_studio_full.py 失败，后续可能缺少文本语料")

    # 2) 网站场次微博匹配
    if not a.no_site:
        run("工作室微博巡演匹配 -> live_repos/tour_weibo_posts", str(PROXY / "工作室巡演匹配.py"), cwd=PROXY)

    # 3) 活动/事件提取（规则分类 -> 聚类 -> LLM -> 活动表）
    if not a.no_events:
        run("规则分类", str(PROXY / "classify_events.py"), cwd=PROXY)
        run("事件聚类", str(PROXY / "cluster_events.py"), cwd=PROXY)
        if not a.no_llm:
            run("DeepSeek 事件提取", str(PROXY / "extract_events_llm.py"), cwd=PROXY)
        run("生成活动 Excel / 大屏节点", str(PROXY / "build_events_excel.py"), cwd=PROXY)
        run("追加高置信演出到活动表", str(PROXY / "append_perf_to_table.py"), cwd=PROXY)

    # 4) 网站页面重建
    if not a.no_site:
        run("更新 live-reviews（tour_weibo 增量）", str(ROOT / "project_b" / "update_live_reviews_tourweibo.py"))
        run("重建 live-reviews（repo 全量）", str(ROOT / "project_b" / "build_live_reviews.py"))
        run("全站生成 deploy_all --no-git", str(ROOT / "project_b" / "deploy_all.py"), cwd=ROOT)

    # 5) 提交（不 push）
    if not a.no_commit:
        log("-- git add/commit --")
        subprocess.run(["git", "add", "-A"], cwd=ROOT)
        r = subprocess.run(
            ["git", "commit", "-m", "工作室微博全量同步: 文本/活动/网站更新"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        log((r.stdout or r.stderr or "").strip().splitlines()[-1] if (r.stdout or r.stderr).strip() else "no changes")
        log("提交完成。请手动 git push origin main")

    log("========== 同步结束 ==========")
    log("日志: %s" % LOG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
