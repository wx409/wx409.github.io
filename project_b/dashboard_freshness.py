# -*- coding: utf-8 -*-
"""dashboard_freshness.py —— 大屏新鲜度哨兵 + 自动补建（零 LLM、零新依赖）

背景（2026-10-14 查明）：`dashboard/` 的「💡 数据洞察」不是独立产物，而是大屏页面内的 JS
现算，数据来自 `dashboard/dashboard_data.json`；页面与数据由常驻 daemon
（`E:\\wx\\QQ音乐大屏生成器_GEO优化版_源码.py`，计划任务 `QQMusicDashboardAutoStart`）定时重建。
daemon 若静默死掉，页面会无声过期——本脚本补这个缺口。

用法：
  python -X utf8 project_b/dashboard_freshness.py --check          # 巡检；过期则告警并 exit 1
  python -X utf8 project_b/dashboard_freshness.py --ensure         # 过期才重建（兜底）
  python -X utf8 project_b/dashboard_freshness.py --ensure --max-age 0   # 强制重建（演示/自愈）
  python -X utf8 project_b/dashboard_freshness.py --json           # 机器可读输出

设计：
- 新鲜度＝`dashboard_data.json` 与 `dashboard/index.html` 两个 mtime 里**较旧**的那个的年龄。
- 告警去重：同一状态 12 小时内只写一次通知（写 `temp/dashboard_freshness.json` 记 state）。
- 重建走生成器自带的 `--rebuild`（只用已有 Excel 重建网页，**不采集**，因此不需要 DrissionPage）。
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(r"D:\wx409.github.io")
DASH = ROOT / "dashboard"
DATA = DASH / "dashboard_data.json"
PAGE = DASH / "index.html"
GEN = Path(r"E:\wx\QQ音乐大屏生成器_GEO优化版_源码.py")
STATE = ROOT / "temp" / "dashboard_freshness.json"
DEFAULT_MAX_AGE_H = 26.0


def age_h(p: Path) -> float | None:
    if not p.exists():
        return None
    return (time.time() - p.stat().st_mtime) / 3600.0


def survey() -> dict:
    a_data, a_page = age_h(DATA), age_h(PAGE)
    ages = [x for x in (a_data, a_page) if x is not None]
    worst = max(ages) if ages else None
    return {
        "data_path_exists": DATA.exists(), "page_path_exists": PAGE.exists(),
        "data_age_h": round(a_data, 2) if a_data is not None else None,
        "page_age_h": round(a_page, 2) if a_page is not None else None,
        "worst_age_h": round(worst, 2) if worst is not None else None,
        "data_mtime": datetime.fromtimestamp(DATA.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if DATA.exists() else None,
        "page_mtime": datetime.fromtimestamp(PAGE.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if PAGE.exists() else None,
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def alert(info: dict, max_age: float, dry: bool = False) -> bool:
    """过期告警；同一状态 12 小时内只写一次。返回是否真的写了通知。"""
    st = load_state()
    last = st.get("last_alert_ts", 0)
    same = st.get("last_state") == "stale"
    if same and (time.time() - last) < 12 * 3600:
        return False
    if dry:
        return False
    msg = (f"大屏数据已过期：数据文件 {info['data_age_h']} 小时未更新"
           f"（阈值 {max_age:g} 小时）。\n"
           f"数据文件时间：{info['data_mtime']}｜页面时间：{info['page_mtime']}\n"
           f"可能原因：常驻 daemon（计划任务 QQMusicDashboardAutoStart）未运行或已退出。\n"
           f"自愈：每日任务 wx409_music_index_daily 会调用 dashboard_freshness --ensure 自动补建；"
           f"若当日仍未补上，请手动重启 daemon。")
    try:
        sys.path.insert(0, str(ROOT / "project_b"))
        import notify as nf                                    # noqa: WPS433
        nf.record("大屏数据过期（自动补建未生效）", msg, category="运维",
                  source="dashboard_freshness.py")
        wrote = True
    except Exception as e:                                     # 通知失败不致命
        print(f"[warn] 写通知失败：{e!r}"[:160])
        wrote = False
    st.update({"last_alert_ts": time.time(), "last_state": "stale"})
    save_state(st)
    return wrote


def rebuild(timeout: int = 1800) -> dict:
    if not GEN.exists():
        return {"ok": False, "why": "生成器不存在（外部路径）"}
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "-X", "utf8", str(GEN), "--rebuild"],
                           cwd=str(GEN.parent), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return {"ok": r.returncode == 0, "rc": r.returncode, "sec": round(time.time() - t0, 1),
                "tail": ((r.stdout or "") + (r.stderr or ""))[-400:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "why": f"超时（>{timeout}s）"}
    except Exception as e:
        return {"ok": False, "why": repr(e)[:160]}


def main() -> int:
    ap = argparse.ArgumentParser(description="大屏新鲜度哨兵 + 自动补建")
    ap.add_argument("--check", action="store_true", help="只巡检（过期 exit 1）")
    ap.add_argument("--ensure", action="store_true", help="过期则自动重建（兜底）")
    ap.add_argument("--max-age", type=float, default=DEFAULT_MAX_AGE_H, help="阈值小时数，默认 26")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--no-alert", action="store_true", help="不写通知（调试）")
    a = ap.parse_args()
    if not (a.check or a.ensure):
        a.check = True

    before = survey()
    stale_before = before["worst_age_h"] is None or before["worst_age_h"] > a.max_age
    stale = stale_before
    result = {"before": before, "max_age_h": a.max_age, "stale_before": stale_before,
              "stale": stale, "rebuilt": None, "alerted": False}

    if stale and a.ensure:
        result["rebuilt"] = rebuild()
        result["after"] = survey()
        stale = result["after"]["worst_age_h"] is None or result["after"]["worst_age_h"] > a.max_age
        result["stale"] = stale

    if stale and not a.no_alert:
        result["alerted"] = alert(before, a.max_age)
    if not stale:
        st = load_state()
        st.update({"last_state": "fresh"})
        save_state(st)

    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        b = before
        print(f"[大屏新鲜度] 数据 {b['data_age_h']}h（{b['data_mtime']}）｜"
              f"页面 {b['page_age_h']}h（{b['page_mtime']}）｜阈值 {a.max_age:g}h → "
              + ("**过期**" if result["stale_before"] else "新鲜 ✅"))
        if result["rebuilt"] is not None:
            rb = result["rebuilt"]
            print("[自动补建] " + ("成功 ✅ %.1fs" % rb["sec"] if rb.get("ok")
                                   else f"失败：{rb.get('why') or rb.get('tail', '')[-160:]}"))
            if "after" in result:
                print(f"[补建后] 数据 {result['after']['data_age_h']}h｜页面 {result['after']['page_age_h']}h → "
                      + ("仍过期 ❌" if result["stale"] else "已恢复 ✅"))
        if result["alerted"]:
            print("[告警] 已写站内通知（data/notifications.json）")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
