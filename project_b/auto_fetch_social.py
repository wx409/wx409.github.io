# -*- coding: utf-8 -*-
"""开机自启：自动抓一遍 王晰本人微博 + 工作室微博 + 王晰小红书（官方账号）。

设计（最小可行）：
- **先验 cookie 四态**：微博（GET /api/config 判 login）/ 小红书（tools\\sync_xhs_cookie.py --check）
- **有效** → 按配置依次跑既有脚本（复用，不另起一套）
- **无效/风控** → **不硬跑**，写站点通知（notify.record）+ 本地日志（含"需要用户做什么"）
- **幂等 + 容错**：单平台失败不影响其它；退出码 0（除非配置缺失）；日志落 temp/

用法：python -X utf8 project_b\\auto_fetch_social.py [--dry] [--platform weibo|xhs]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
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


# ───────────────────────── 主动通知（弹窗 + 桌面标记 + 每日去重） ─────────────────────────
# 现状是被动通知（站点 notifications.html + 本地日志，且启动项是 start /min 最小化窗口）
# → 「不动手去看就收不到」。这里补两条**主动**通道，保留站点通知与日志（三通道并存）。
STATE = SITE / "temp" / "auto_fetch_social_state.json"
DESKTOP = Path(os.environ.get("USERPROFILE") or str(Path.home())) / "Desktop"
MARK = DESKTOP / "⚠_王晰采集_cookie需更新.txt"
STEPS = ("三步怎么做：\n"
         "  1) 浏览器登录对应平台 → F12 → Network → 随便点一个已发出的请求 → 右键 → Copy → "
         "Copy request headers\n"
         "  2) 把里面的 Cookie 一行粘进 E:\\wx\\index_records\\wb.txt（微博）或 xhs.txt（小红书）\n"
         "  3) 跑 tools\\sync_weibo_cookie.py（微博）或 tools\\sync_xhs_cookie.py（小红书）")


def _state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(d: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def popup(title: str, body: str) -> bool:
    """桌面弹窗（PowerShell MessageBox，**非阻塞**：超时 60s 自动关，脚本不等待）。"""
    try:
        # 用 XML 承载文本（PS 侧解析 XML，避免引号/换行转义问题）
        xml = ("<t><title>" + (title or "").replace("&", "&amp;").replace("<", "&lt;") + "</title>"
               "<body>" + (body or "").replace("&", "&amp;").replace("<", "&lt;").replace("\n", "&#10;")
               + "</body></t>")
        tmp = SITE / "temp" / "_cookie_popup.xml"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(xml, encoding="utf-8")
        ps = ("Add-Type -AssemblyName System.Windows.Forms;"
              "$x=[xml](Get-Content -Raw -Encoding UTF8 '" + str(tmp) + "');"
              "$null=[System.Windows.Forms.MessageBox]::Show("
              "$x.t.body.'#text' + [Environment]::NewLine + $x.t.body.InnerText,"
              "$x.t.title.InnerText,[System.Windows.Forms.MessageBoxButtons]::OK,"
              "[System.Windows.Forms.MessageBoxIcon]::Warning)")
        # 非阻塞：不等待（Popen），并自带超时自杀，避免弹窗卡住采集流程
        subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        log("已弹桌面窗口（非阻塞）")
        return True
    except Exception as e:
        log(f"弹窗失败（不致命）：{e}")
        return False


def active_alert(plat: str, st: str, hint_extra: str = "") -> None:
    """cookie 非「有效」时的**主动通知**：每天每平台每状态只弹一次；桌面标记文件常驻到恢复。

    三通道并存：① 站点通知（由调用方 notify）② 桌面弹窗 ③ 桌面标记文件（恢复后自动删）。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{plat}:{st}"
    s = _state()
    fired = (s.get("fired") or {})
    if fired.get(key) == today:
        log(f"主动通知去重：{plat} {st} 今天已弹过（不再弹）")
    else:
        title = f"⚠ 王晰采集：{plat} cookie {st}"
        body = (f"{plat} 登录态：{st}\n\n{STEPS}\n\n{hint_extra}\n\n"
                f"（此窗口 60 秒后自动关闭；本站不做任何自动登录）")
        popup(title, body)
        fired[key] = today
    # 桌面标记文件：写清平台/时间/三步；恢复后由 clear_mark 删除
    try:
        MARK.parent.mkdir(parents=True, exist_ok=True)
        cur = MARK.read_text(encoding="utf-8") if MARK.exists() else ""
        line = (f"[{datetime.now():%Y-%m-%d %H:%M}] {plat}：{st}"
                f"（{hint_extra}）\n")
        if line not in cur:
            MARK.write_text(cur + line, encoding="utf-8")
        log(f"桌面标记文件已更新：{MARK}")
    except Exception as e:
        log(f"桌面标记写入失败（不致命）：{e}")
    s["fired"] = fired
    s["last"] = {**(s.get("last") or {}), plat: {"state": st, "at": datetime.now().isoformat(timespec="seconds")}}
    _save_state(s)


def clear_mark(plat: str) -> None:
    """cookie 恢复正常 → 删除桌面标记文件（若无其它平台仍异常）。"""
    s = _state()
    last = s.get("last") or {}
    last.pop(plat, None)
    s["last"] = last
    _save_state(s)
    if last:
        log(f"{plat} cookie 已恢复；仍有平台待处理：{list(last)}（标记文件保留）")
        return
    if MARK.exists():
        try:
            MARK.unlink()
            log(f"全部平台 cookie 恢复正常 → 已删除桌面标记文件：{MARK}")
        except Exception as e:
            log(f"删除桌面标记失败（不致命）：{e}")
    else:
        log("桌面标记文件不存在（无需删除）")


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
        # ★ 2026-10-14 四态：显式解析（缺文件/异常 → 不可判定，不判失效）
        import re as _re
        m = _re.search(r"四态判定[：:]\s*(有效|失效|被风控|不可判定)", out) or _re.search(
            r"(不可判定|被风控|失效|有效)", out)
        if m:
            return m.group(1)
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
        login = (d.get("data") or {}).get("login")
        if login is True:
            return "有效"
        if login is False:
            return "失效"
        return "不可判定"   # 应答无法解释 → 不判失效（防误报）
    except Exception as e:
        return "不可判定"   # 网络异常/文件缺失 → 不判失效（防误报）


def check_xhs():
    r = subprocess.run([sys.executable, "-X", "utf8", "tools/sync_xhs_cookie.py", "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore", cwd=str(SITE))
    out = (r.stdout or "") + (r.stderr or "")
    # ★ 2026-10-14 四态：显式解析（缺文件/工具链异常 → 不可判定，不判失效）
    import re as _re
    m = _re.search(r"四态判定[：:]\s*(有效|失效|被风控|不可判定)", out) or _re.search(
        r"(不可判定|被风控|失效|有效)", out)
    return m.group(1) if m else "不可判定"


def run(cmd, cwd):
    r = subprocess.run(cmd, shell=False, capture_output=True, text=True,
                       encoding="utf-8", errors="ignore", cwd=cwd)
    tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    return r.returncode, (tail[-1][:160] if tail else "")


def already_ran_today() -> str:
    """同日去重：返回今天已跑过的时间戳（未跑过返回空串）。

    ★ 2026-10-15 补：开机自启**只在登录时触发**——这台机器 2026-10-08 开机后从未重启，
    抓取连续多日没有触发机会。故新增每日兜底计划任务（09:30）与启动文件夹**并存**，
    并用本函数保证**同一自然日只成功跑一次**（以 state.json 的 `last_run_ok` 为准）。
    """
    s = _state()
    lr = s.get("last_run_ok") or {}
    return lr.get("at", "") if lr.get("date") == datetime.now().strftime("%Y-%m-%d") else ""


def mark_ran_today(note: str = "") -> None:
    s = _state()
    s["last_run_ok"] = {"date": datetime.now().strftime("%Y-%m-%d"),
                        "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "note": note}
    _save_state(s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--platform", default="", help="weibo|xhs，留空=全部")
    ap.add_argument("--force", action="store_true", help="忽略同日去重，强制跑一次")
    a = ap.parse_args()
    if not CFG.exists():
        log("!! 缺配置文件 data/social_fetch_config.json → 退出码 2")
        return 2
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    log(f"=== 开机自启抓取{'（dry）' if a.dry else ''}{'（force）' if a.force else ''} ===")

    # 同日去重（启动项与每日兜底任务并存，靠这里互不重复）
    if not a.force and not a.dry:
        done = already_ran_today()
        if done:
            log(f"同日去重：今天（{datetime.now():%Y-%m-%d}）已于 {done} 成功跑过 → 本次跳过"
                f"（要强制跑加 --force）")
            return 0

    if a.platform in ("", "weibo"):
        st = check_weibo(cfg)
        log(f"微博 cookie 四态：{st}")
        if st in ("失效", "被风控"):
            notify("⚠ 微博 cookie 需要更新", f"微博登录态：{st}。请{HINT}")
            active_alert("微博", st, "跑 tools\\sync_weibo_cookie.py")
        elif st == "不可判定":
            log("微博登录态「不可判定」→ 只记日志 + 站内通知一次，**不弹窗/不建桌面文件**"
                "（避免让你去重置本来没坏的 cookie）")
            notify("ℹ 微博登录态不可判定（非失效）",
                   "本次未能判定微博登录态（cookie 文件缺失 / 端点不可达 / 应答无法解释）。"
                   "**未判定为失效**，请勿急于重置 cookie；若持续多日不可判定再检查网络或文件路径。")
        else:
            clear_mark("微博")
            if a.dry:
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
        log(f"小红书 cookie 四态：{st}")
        if st in ("失效", "被风控"):
            notify("⚠ 小红书 cookie 需要更新", f"小红书登录态：{st}。请{HINT}")
            active_alert("小红书", st, "跑 tools\\sync_xhs_cookie.py")
        elif st == "不可判定":
            log("小红书登录态「不可判定」→ 只记日志 + 站内通知一次，**不弹窗/不建桌面文件**")
            notify("ℹ 小红书登录态不可判定（非失效）",
                   "本次未能判定小红书登录态（cookie 文件缺失 / 工具链加载失败 / 网络异常）。"
                   "**未判定为失效**，请勿急于重置 cookie。")
        else:
            clear_mark("小红书")
            for x in cfg.get("xiaohongshu", []):
                url = x.get("url") or ""
                if a.dry:
                    log(f"（dry）将执行：{x['script']} --url <{x['label']} profile>"
                        f"（user_id={x.get('user_id')}，url 模板={url[:60]}…）")
                else:
                    rc, t = run([sys.executable, "-X", "utf8", x["script"], "--url", url],
                                cwd=str(Path(x["script"]).parent))
                    log(f"  {x['label']}：rc={rc}｜{t}")
    # 只有全部平台 cookie「有效」才记为「今日已成功跑过」（否则下次仍应重试）
    if not a.dry:
        s = _state()
        try:
            st_weibo = None
            if a.platform in ("", "weibo"):
                st_weibo = check_weibo(cfg)
            st_xhs = None
            if a.platform in ("", "xhs"):
                st_xhs = check_xhs()
            states = {k: v for k, v in (("微博", st_weibo), ("小红书", st_xhs)) if v is not None}
            bad = {k: v for k, v in states.items() if v != "有效"}
        except Exception as e:
            bad, states = {"unknown": repr(e)[:60]}, {}
        if not bad:
            mark_ran_today("all-cookie-valid")
            log("已记「今日成功跑过」（同日去重生效：启动项与每日兜底不再重复）")
        else:
            log(f"未记「今日成功跑过」：登录态异常 {bad} → 下次（含每日兜底）会重试，"
                f"以便 cookie 更新后自动补齐")
    log("=== 完成（单平台失败不影响其它）===")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
