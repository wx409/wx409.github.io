# -*- coding: utf-8 -*-
"""传播监测线：搜 → 抓正文+评论 → 量化 → 摘要 → 异常通知（复用既有工具，不另造）。

用法：
  python -X utf8 project_b\\propagation_watch.py --dry            # 只打印将执行的动作与阈值判定
  python -X utf8 project_b\\propagation_watch.py --mode links     # 小红书按链接路径（最稳）
  python -X utf8 project_b\\propagation_watch.py --since 72       # 时间窗（小时）
纪律：音视频不入 git、不上页面；作者名匿名化；**无平台侧数据不得写"上热点/爆火"**；
      cookie 失效走既有三态（站点通知 + 本地日志）；失败如实记录，不伪造。
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
CFG = SITE / "data" / "propagation_watch.json"
DIGEST = SITE / "data" / "propagation_digest.json"
ARCH = Path(r"E:\wx\论文素材_王晰作传\传播监测")
LOG = SITE / "temp" / "propagation_watch.log"


def log(m):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {m}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.open("a", encoding="utf-8").write(line + "\n")


def notify(title, body):
    try:
        sys.path.insert(0, str(SITE / "project_b"))
        import notify
        notify.record(title, body)
        log("已写站点通知（文案只写机制，不写爆火）")
    except Exception as e:
        log(f"通知失败（不致命）：{e}")


def cookie_ok(plat):
    if plat == "xhs":
        r = subprocess.run([sys.executable, "-X", "utf8", "tools/sync_xhs_cookie.py", "--check"],
                           capture_output=True, text=True, encoding="utf-8", errors="ignore",
                           cwd=str(SITE))
        out = (r.stdout or "") + (r.stderr or "")
        for s in ("有效", "失效", "被风控"):
            if s in out:
                return s
        return "无法判定"
    return "未检查"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--mode", default="links", choices=["links", "search"])
    ap.add_argument("--since", type=int, default=0)
    a = ap.parse_args()
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    win = a.since or cfg.get("time_window_hours", 72)
    log(f"=== 传播监测（{'dry' if a.dry else '实跑'}｜窗 {win}h｜模式 {a.mode}）===")
    log("关键词组：曲名 %d｜钩子词 %d｜演出词 %d" % (
        len(cfg["keywords"]["songs"]), len(cfg["keywords"]["hook_words"]),
        len(cfg["keywords"]["show_words"])))
    acts = []
    for plat, c in (cfg.get("platforms") or {}).items():
        if not c.get("enabled"):
            continue
        st = cookie_ok(plat) if plat in ("xhs", "weibo") else "不适用"
        log(f"  {plat}：cookie 三态 = {st}")
        if st in ("失效", "被风控"):
            notify(f"⚠ {plat} cookie 需要更新", f"传播监测：{plat} 登录态 {st}；"
                   "请 F12 复制 Cookie 粘进 wb.txt/xhs.txt 并跑对应 sync 脚本")
            continue
        tool = c.get("tool")
        if plat == "xhs" and a.mode == "search" and c.get("why"):
            log(f"    ⚠ 搜索路径受限（{c['why'][:32]}…）→ 退避 + 限速后仍失败则如实记录")
        acts.append((plat, tool))
    log("限速：%.1f–%.1f s/请求｜退避基数 %ss｜最多 %d 次" % (
        cfg["rate_limit"]["sleep_min_s"], cfg["rate_limit"]["sleep_max_s"],
        cfg["rate_limit"]["backoff_base_s"], cfg["rate_limit"]["max_retries"]))
    if a.dry:
        for plat, tool in acts:
            log(f"  （dry）将调用：{tool}")
        log("（dry）不抓取、不写摘要、不通知")
        return 0
    log("!! 实抓需平台侧可用性；本版先落配置与编排，抓取/评论/摘要待接（失败如实记录）")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
