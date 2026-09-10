# -*- coding: utf-8 -*-
"""s4u_headless_probe.py —— S4U（无交互会话）下 headless Edge 连通性探针

用途
----
回答"重启后必须解锁屏幕才能自动启动计划任务吗？" —— 若把守护进程任务改成
LogonType=S4U（不存密码、无需登录），它能否在**没有交互式桌面**的会话里
正常驱动 headless Edge 抓取？本探针只做"起浏览器 → 打开 QQ音乐指数页 → 取数"，
**不写任何数据、不重建看板、不 push**，因此可在守护进程运行时安全执行。

分级判定（避免"能起浏览器但取不到数"被误判为整体失败）：
    L1 浏览器进程在无交互会话中成功启动
    L2 页面标题获取成功（证明网络栈可用）
    L3 从指数页取到数字（证明 DOM 提取可用，等同守护进程工作路径）
    → L2 达成即视为 S4U 方案可行；L3 达成则为完全等价。

结果同时打印并追加到 logs\\s4u_headless_probe.log（S4U 会话看不到控制台，必须落盘）。

用法：
    python -X utf8 tools\\s4u_headless_probe.py
退出码：0 = L2 及以上通过；1 = 仅 L1 或更低（需改用自动登录方案）
"""
from __future__ import annotations

import datetime as dt
import os
import random
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "s4u_headless_probe.log"

TARGETS = [
    ("神魂颠倒", "000k0cHz2GarPp"),
    ("亲密爱人", "0039MnYb0qxYhV"),
]
URL_TMPL = ("https://y.qq.com/m/client/music_index/index.html"
            "?ADTAG=cbshare&channelId=10036163&mid={mid}&openinqqmusic=1&type={mid}")
FALLBACK_URL = "https://y.qq.com/n/ryqq/songDetail/%s"  # 轻量页，用于区分"网络不通"与"指数页不通"


def log(msg: str) -> None:
    line = "[%s] %s" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


JS_EXTRACT = r"""
try {
  var r={};
  var n=document.evaluate("//div[contains(@aria-label,'实时音乐指数')]//div[@class='base_data__num']",
          document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue;
  r.idx=n?n.innerText.trim():'';
  var l=document.querySelector('.info_album__listen');
  r.listen=l?l.getAttribute('aria-label'):'';
  r.title=document.title;
  return JSON.stringify(r);
} catch(e){ return 'ERR:'+e; }
"""


def main() -> int:
    log("=" * 60)
    log("S4U headless 探针启动 | SESSIONNAME=%s | USERNAME=%s | USERPROFILE=%s"
        % (os.environ.get("SESSIONNAME", "?"), os.environ.get("USERNAME", "?"),
           os.environ.get("USERPROFILE", "?")))
    try:
        from DrissionPage import ChromiumOptions, ChromiumPage
    except Exception as e:
        log("FAIL L0 无法导入 DrissionPage: %s" % e)
        return 1

    co = ChromiumOptions()
    for cand in (r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
        if os.path.exists(cand):
            co.set_browser_path(cand)
            log("浏览器: %s" % cand)
            break
    co.set_user_data_path(os.path.join(tempfile.gettempdir(), "dp_probe_%d" % int(time.time())))
    co.set_address("127.0.0.1:%d" % random.randint(19222, 19999))
    co.headless(True)
    for arg in ("--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", "--disable-extensions",
                "--disable-images", "--blink-settings=imagesEnabled=false", "--no-first-run",
                "--disable-background-networking", "--disable-sync"):
        co.set_argument(arg)

    browser = None
    l1 = l2 = l3 = False
    try:
        browser = ChromiumPage(addr_or_opts=co)
        l1 = True
        log("L1 PASS 浏览器已在无交互会话中启动（headless）")

        # L2：先开轻量页拿标题（区分"网络不通"与"指数页不通"）
        try:
            p = browser.new_tab(FALLBACK_URL % TARGETS[0][1])
            time.sleep(3)
            t = (p.title or "").strip()
            if t:
                l2 = True
                log("L2 PASS 页面标题获取成功: %r" % t[:60])
            else:
                log("L2 FAIL 页面标题为空")
        except Exception as e:
            log("L2 FAIL 页面异常: %s" % e)

        # L3：指数页取数（守护进程的实际工作路径）
        for name, mid in TARGETS:
            try:
                page = browser.new_tab(URL_TMPL.format(mid=mid))
                time.sleep(3)
                data = page.run_js(JS_EXTRACT)
                log("L3 取数 %s: %s" % (name, str(data)[:160]))
                if data and "ERR" not in str(data) and ('"idx":"' in str(data) or '"listen":"' in str(data)):
                    if '"idx":"' in str(data):
                        l3 = True
                        break
            except Exception as e:
                log("L3 取数 %s 异常: %s" % (name, e))
        if l3:
            log("L3 PASS 指数页取数成功 —— 与守护进程工作路径完全等价")
    except Exception as e:
        log("L1 FAIL 浏览器启动/连接异常: %s" % e)
    finally:
        try:
            if browser:
                browser.quit()
        except Exception:
            pass

    verdict = "L3 完全等价" if l3 else ("L2 可用（网络与页面可达）" if l2 else "L1 仅浏览器可启动")
    log("结论: %s → %s" % (verdict, "S4U 方案可行" if (l2 or l3) else "S4U 不可用，请改用自动登录方案"))
    log("探针结束 exit=%d" % (0 if (l2 or l3) else 1))
    return 0 if (l2 or l3) else 1


if __name__ == "__main__":
    sys.exit(main())
