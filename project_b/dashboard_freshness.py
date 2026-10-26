# -*- coding: utf-8 -*-
"""freshness sentinel —— 多目标新鲜度哨兵 + 自动补建（零 LLM、零新依赖）

两个目标（同一套模式，不另写一套）：
  ① `dashboard`：`dashboard/dashboard_data.json` 与 `dashboard/index.html` 较旧的年龄 > 阈值（默认 26h）→ 告警；
     补建 = 大屏生成器自带 `--rebuild`（只用已有 Excel 重建网页，不采集）。
  ② `insight`：`insight.html` **比它的输入新不了**——只要
     `data/share/conclusion_copy.json` / `data/text_profile.json` / `data/share/hook_candidates.json`
     / `data/share/insight_charts.json` 中有任何一个的 mtime 晚于页面（容差 60s），即视为「未随输入更新」；
     补建 = 依次跑 deploy_all 登记的那 6 个生成器 + build_nav（失败不致命）。

背景：洞察链在 `deploy_all` 里是 **non-fatal** 步骤，某步静默失败时页面会停在上一版而不报警——本哨兵补这个缺口。
（大屏侧背景：页面与数据由常驻 daemon `QQMusicDashboardAutoStart` 重建，daemon 静默退出时同理无声。）

用法：
  python -X utf8 project_b/dashboard_freshness.py --check                    # 两个目标都巡检
  python -X utf8 project_b/dashboard_freshness.py --check --target insight   # 只巡检洞察页
  python -X utf8 project_b/dashboard_freshness.py --ensure                   # 未随输入更新则补跑
  python -X utf8 project_b/dashboard_freshness.py --json

设计：
- 告警去重：**每个目标各自**记录状态，同一状态 12h 内只写一次站内通知（`temp/dashboard_freshness.json`）。
- 通知文案只写机制与文件（走 notify 的既有通道，写入处自动净化本机路径），不用过程稿措辞。
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
D = ROOT / "data"
STATE = ROOT / "temp" / "dashboard_freshness.json"
DASH_GEN = Path(r"E:\wx\QQ音乐大屏生成器_GEO优化版_源码.py")
DEFAULT_MAX_AGE_H = 26.0
TOLERANCE_S = 60.0          # mtime 比较容差：避免同一次部署里先后写入造成的假告警

# 洞察链（与 deploy_all.STEPS 登记的顺序一致；失败不致命）
INSIGHT_CHAIN = ["build_language_profile.py", "build_cross_wording.py", "build_conclusion_copy.py",
                 "build_hook_candidates.py", "build_insight_charts.py", "build_insight_page.py",
                 "build_nav.py"]

WATCHES = {
    "dashboard": {
        "label": "数据大屏",
        "page": ROOT / "dashboard" / "index.html",
        "inputs": [ROOT / "dashboard" / "dashboard_data.json",
                   Path(r"E:\wx\wx_textmine_out\music_index_long.csv"),
                   ROOT / "data" / "archive_baseline.json"],
        "mode": "input_newer",               # ★ 2026-10-26：长表/基线比页面新即需重建（原 age 判据看不到“数据已更新、页面还没重建”）
        "why": "大屏由常驻 daemon（计划任务 QQMusicDashboardAutoStart）定时重建；daemon 未运行时会停在上一版",
        "fix": "每日任务 wx409_music_index_daily 会调用本哨兵 --ensure，用生成器 --rebuild 补建",
    },
    "insight": {
        "label": "洞察页",
        "page": ROOT / "insight.html",
        "inputs": [D / "share" / "conclusion_copy.json", D / "text_profile.json",
                   D / "share" / "hook_candidates.json", D / "share" / "insight_charts.json"],
        "mode": "input_newer",               # 输入比页面新 → 未随输入更新
        "why": "洞察页由 deploy_all 里的 6 个非致命步骤生成；某步未运行或失败时，页面会停在上一版",
        "fix": "本哨兵 --ensure 会依次补跑这 6 个生成器与 build_nav（失败不致命）",
    },
}


def mtime(p: Path):
    return p.stat().st_mtime if p.exists() else None


def fmt(ts) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "—"


def survey(name: str) -> dict:
    w = WATCHES[name]
    page, inputs = w["page"], w["inputs"]
    tp = mtime(page)
    ip = [(str(p.relative_to(ROOT)) if str(p).startswith(str(ROOT)) else p.name, mtime(p)) for p in inputs]
    newest = max([t for _n, t in ip if t] or [None]) if any(t for _n, t in ip) else None
    info = {
        "target": name, "label": w["label"], "mode": w["mode"],
        "page": str(page.relative_to(ROOT)), "page_mtime": fmt(tp),
        "page_age_h": round((time.time() - tp) / 3600.0, 2) if tp else None,
        "inputs": [{"file": n, "mtime": fmt(t), "age_h": round((time.time() - t) / 3600.0, 2) if t else None}
                   for n, t in ip],
        "newest_input": fmt(newest), "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if w["mode"] == "age":
        ages = [x for x in (info["page_age_h"], *(i["age_h"] for i in info["inputs"])) if x is not None]
        info["worst_age_h"] = round(max(ages), 2) if ages else None
        info["stale"] = (info["worst_age_h"] is None) or (info["worst_age_h"] > DEFAULT_MAX_AGE_H)
    else:
        lag = (newest - tp) if (tp and newest) else None
        info["input_lag_s"] = round(lag, 1) if lag is not None else None
        info["stale"] = (tp is None) or (lag is not None and lag > TOLERANCE_S)
    return info


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def alert(info: dict, dry: bool = False) -> bool:
    """过期告警；**每个目标各自** 12h 去重。返回是否真的写了通知。"""
    name = info["target"]
    st = load_state()
    per = (st.get("watches") or {}).get(name) or {}
    if per.get("last_state") == "stale" and (time.time() - (per.get("last_alert_ts") or 0)) < 12 * 3600:
        return False
    if dry:
        return False
    w = WATCHES[name]
    lines = [f"{w['label']}未随输入更新。",
             f"页面：{info['page']}（时间 {info['page_mtime']}）"]
    for i in info["inputs"]:
        lines.append(f"输入：{i['file']}（时间 {i['mtime']}）")
    if info.get("input_lag_s") is not None:
        lines.append(f"输入比页面新 {info['input_lag_s']} 秒。")
    lines += [f"机制：{w['why']}。", f"自愈：{w['fix']}。"]
    try:
        sys.path.insert(0, str(ROOT / "project_b"))
        import notify as nf                                     # noqa: W433
        nf.record(f"{w['label']}未随输入更新", "\n".join(lines), category="运维",
                  source="dashboard_freshness.py")
        wrote = True
    except Exception as e:                                      # 通知失败不致命
        print(f"[warn] 写通知失败：{e!r}"[:160])
        wrote = False
    st.setdefault("watches", {})[name] = {"last_alert_ts": time.time(), "last_state": "stale"}
    save_state(st)
    return wrote


def rebuild_dashboard(timeout: int = 1800) -> dict:
    if not DASH_GEN.exists():
        return {"ok": False, "why": "生成器不存在（外部路径）"}
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "-X", "utf8", str(DASH_GEN), "--rebuild"],
                           cwd=str(DASH_GEN.parent), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return {"ok": r.returncode == 0, "rc": r.returncode, "sec": round(time.time() - t0, 1),
                "tail": ((r.stdout or "") + (r.stderr or ""))[-300:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "why": f"超时（>{timeout}s）"}
    except Exception as e:
        return {"ok": False, "why": repr(e)[:160]}


def rebuild_insight(timeout: int = 2400) -> dict:
    """按 deploy_all 登记的顺序补跑洞察链；任何一步失败都记录但不中断（失败不致命）。"""
    t0, results = time.time(), []
    for s in INSIGHT_CHAIN:
        p = ROOT / "project_b" / s
        try:
            r = subprocess.run([sys.executable, "-X", "utf8", str(p)], cwd=str(ROOT),
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout)
            results.append({"step": s, "rc": r.returncode})
        except Exception as e:
            results.append({"step": s, "rc": None, "why": repr(e)[:120]})
    ok = all(x.get("rc") == 0 for x in results)
    return {"ok": ok, "sec": round(time.time() - t0, 1), "steps": results}


def main() -> int:
    ap = argparse.ArgumentParser(description="多目标新鲜度哨兵 + 自动补建（dashboard / insight）")
    ap.add_argument("--check", action="store_true", help="只巡检（有目标过期则 exit 1）")
    ap.add_argument("--ensure", action="store_true", help="过期则自动补建（兜底）")
    ap.add_argument("--target", choices=["all", *WATCHES.keys()], default="all")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-alert", action="store_true", help="不写通知（调试）")
    a = ap.parse_args()
    if not (a.check or a.ensure):
        a.check = True
    names = list(WATCHES) if a.target == "all" else [a.target]

    out, any_stale = {}, False
    for name in names:
        before = survey(name)
        entry = {"before": before, "rebuilt": None, "alerted": False}
        stale = before["stale"]
        if stale and a.ensure:
            entry["rebuilt"] = rebuild_dashboard() if name == "dashboard" else rebuild_insight()
            entry["after"] = survey(name)
            stale = entry["after"]["stale"]
        entry["stale"] = stale
        if stale and not a.no_alert:
            entry["alerted"] = alert(before)
        if not stale:
            st = load_state()
            st.setdefault("watches", {})[name] = {"last_state": "fresh"}
            save_state(st)
        any_stale = any_stale or stale
        out[name] = entry

        b = before
        if not a.json:
            if b["mode"] == "age":
                head = (f"[{b['label']}] 页面 {b['page']} {b['page_age_h']}h｜"
                        f"数据 {b['inputs'][0]['age_h']}h → ")
            else:
                head = (f"[{b['label']}] 页面 {b['page_mtime']}｜最新输入 {b['newest_input']}"
                        f"（滞后 {b.get('input_lag_s')}s）→ ")
            print(head + ("需补建" if b["stale"] else "已随输入更新 ✅"))
            rb = entry["rebuilt"]
            if rb is not None:
                if name == "dashboard":
                    print("   [补建] " + ("成功 ✅ %.1fs" % rb["sec"] if rb.get("ok")
                                        else f"失败：{rb.get('why') or rb.get('tail', '')[-160:]}"))
                else:
                    bad = [x["step"] for x in rb["steps"] if x.get("rc") != 0]
                    print("   [补跑洞察链] " + ("成功 ✅ %.1fs" % rb["sec"] if rb["ok"]
                                              else f"有步骤未成功：{bad}"))
                if "after" in entry:
                    print("   [补后] " + ("已随输入更新 ✅" if not entry["stale"] else "仍未更新 ❌"))
            if entry["alerted"]:
                print("   [告警] 已写站内通知（data/notifications.json）")
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    return 1 if any_stale else 0


if __name__ == "__main__":
    sys.exit(main())
