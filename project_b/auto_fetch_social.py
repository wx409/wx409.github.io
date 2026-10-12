# -*- coding: utf-8 -*-
"""开机自启：自动抓一遍 王晰本人微博 + 工作室微博 + 王晰小红书（官方账号）。

设计（最小可行）：
- **先验 cookie 三态**：微博（GET /api/config 判 login）/ 小红书（tools\\sync_xhs_cookie.py --check）
- **有效** → 按配置依次跑既有脚本（复用，不另起一套）
- **无效/风控** → **不硬跑**，写站点通知（notify.record）+ 本地日志（含"需要用户做什么"）
- **幂等 + 容错**：单平台失败不影响其它；退出码 0（除非配置缺失）；日志落 temp/

用法：python -X utf8 project_b\\auto_fetch_social.py [--dry] [--platform weibo|xhs]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import urllib.request
import sys
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
CFG = SITE / "data" / "social_fetch_config.json"
LOG = SITE / "temp" / "auto_fetch_social.log"
# 微博登录态判定端点（**必须带 cookie** 请求，否则会误判为失效）
ENDPOINT = "https://m.weibo.cn/api/config"
WB_COOKIE = Path(r"E:\\wx\\私有工具\\weibo_proxy\\weibo_cookie.json")
HINT = ("F12 → Network → 复制请求头 Cookie → 粘进 wb.txt / xhs.txt → 跑 tools\\sync_weibo_cookie.py "
        "或 tools\\sync_xhs_cookie.py")


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def notify(title, body):
    try:
        sys.path.insert(0, str(SITE / "project_b"))
        import notify  # noqa
        notify.record(title, body)
        log("已写站点通知")
    except Exception as e:
        log(f"站点通知失败（不致命）：{e}")


def check_weibo(cfg):
    """微博登录态三态。

    判定用文件与端点（2026-10-12 实测修正）：
      ① 首选 `tools/sync_weibo_cookie.py --check`（与操作中心同口径），若存在且给出三态则采用；
      ② 否则读 `E:\wx\私有工具\weibo_proxy\weibo_cookie.json` 的 cookie，
         **带 Cookie 头** GET `https://m.weibo.cn/api/config`，取 data.login。
    注意：**必须带 cookie**——不带 cookie 请求 /api/config 会返回 login=false，会造成"失效"误报。
    """
    try:
        r = subprocess.run([sys.executable, "-X", "utf8", "tools/sync_weibo_cookie.py", "--check"],
                           capture_output=True, text=True, encoding="utf-8", errors="ignore",
                           cwd=str(SITE))
        out = (r.stdout or "") + (r.stderr or "")
        for s2 in ("有效", "失效", "被风控"):
            if s2 in out:
                return s2
    except Exception:
        pass
    try:
        raw = json.loads(Path(r"E:\\wx\\私有工具\\weibo_proxy\\weibo_cookie.json")
                         .read_text(encoding="utf-8"))
        ck = raw if isinstance(raw, str) else (raw.get("cookie") or raw.get("Cookie") or "")
        if isinstance(ck, dict):
            ck = "; ".join(f"{k}={v}" for k, v in ck.items())
        req = urllib.request.Request(ENDPOINT, headers={
            "Cookie": ck, "User-Agent": "Mozilla/5.0", "Referer": "https://m.weibo.cn/"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            d = json.loads(resp.read().decode("utf-8", "ignore"))
        return "有效" if (d.get("data") or {}).get("login") else "失效"
    except Exception as e:
        return f"无法判定（网络/风控：{type(e).__name__}）"


def check_xhs():
    r = subprocess.run([sys.executable, "-X", "utf8", "tools/sync_xhs_cookie.py", "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore", cwd=str(SITE))
    out = (r.stdout or "") + (r.stderr or "")
    for s in ("有效", "失效", "被风控"):
        if s in out:
            return s
    return "无法判定"


def run(cmd, cwd):
    r = subprocess.run(cmd, shell=False, capture_output=True, text=True,
                       encoding="utf-8", errors="ignore", cwd=cwd)
    tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    return r.returncode, (tail[-1][:160] if tail else "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--platform", default="", help="weibo|xhs，留空=全部")
    a = ap.parse_args()
    if not CFG.exists():
        log("!! 缺配置文件 data/social_fetch_config.json → 退出码 2")
        return 2
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    log(f"=== 开机自启抓取{'（dry）' if a.dry else ''} ===")

    if a.platform in ("", "weibo"):
        st = check_weibo(cfg)
        log(f"微博 cookie 三态：{st}")
        if st != "有效":
            notify("⚠ 微博 cookie 需要更新", f"微博登录态：{st}。请{F['weibo'] if False else HINT}")
        elif a.dry:
            log("（dry）将执行：" + "；".join(w["cmd"] for w in cfg.get("weibo", []))
                + "；" + (cfg.get("weibo_snapshot") or {}).get("cmd", ""))
        else:
            for w in cfg.get("weibo", []):
                # ★ 参数列表化 + 各自 cwd（weibo_proxy*.py 在 E:\wx\私有工具\weibo_proxy）
                args = w.get("args") or (w.get("cmd") or "").split()
                rc, t = run([sys.executable, "-X", "utf8"] + args,
                            cwd=Path(w.get("cwd") or SITE))
                log(f"  {w['label']}：rc={rc}｜{t}")
            snap = cfg.get("weibo_snapshot") or {}
            sargs = snap.get("args") or (snap.get("cmd") or "").split()
            if sargs:
                rc, t = run([sys.executable, "-X", "utf8"] + sargs,
                            cwd=Path(snap.get("cwd") or SITE))
                log(f"  微博快照：rc={rc}｜{t}")

    if a.platform in ("", "xhs"):
        st = check_xhs()
        log(f"小红书 cookie 三态：{st}")
        if st != "有效":
            notify("⚠ 小红书 cookie 需要更新", f"小红书登录态：{st}。请{HINT}")
        else:
            for x in cfg.get("xiaohongshu", []):
                url = x.get("url") or ""
                if a.dry:
                    log(f"（dry）将执行：{x['script']} --url <{x['label']} profile>"
                        f"（user_id={x.get('user_id')}，url 模板={url[:60]}…）")
                else:
                    rc, t = run([sys.executable, "-X", "utf8", x["script"], "--url", url],
                                cwd=str(Path(x["script"]).parent))
                    log(f"  {x['label']}：rc={rc}｜{t}")
    log("=== 完成（单平台失败不影响其它）===")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
