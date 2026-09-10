# -*- coding: utf-8 -*-
"""refresh_index_baseline.py —— 指数长表 + 基线 的每日自动刷新（补齐流水线缺口）

为什么需要它
------------
2026-09-10 排查发现：`project_b\\deploy_all.py` 的 30 个步骤里**没有**
`00_build_matrix.py`（指数长表）与 `compute_baseline_v1.py`（基线/年度表/效应/站点 JSON）。
也就是说：即使 daemon 每天 23:55 生成了新的日档案，**站点基线也不会自动跟着更新**，
必须有人手动跑 操作中心 64 → 45/44。9/9 停摆的次日就正好卡在这里。

本脚本把这一步接进每日流程（由 `auto_update.py` 调用，非致命）：
    1. 写权限预检（受限会话写不了 E:\\ 时干净跳过，不误报失败）
    2. 重建指数长表      python E:\\wx\\wx_textmine\\00_build_matrix.py
    3. 重跑基线          python 基线口径\\compute_baseline_v1.py（内含同步站点 data/archive_baseline.json）
    4. 新鲜度验收：长表最新日期 应 == 最新日档案日期 − 1（修正映射口径），并记录年度值

幂等与节流：默认**每天只真正跑一次**（状态写 logs/index_baseline_state.json），
`--force` 可强制；`--check-only` 只报告新鲜度不重建。

用法：
    python project_b\\refresh_index_baseline.py               # 每日一次（auto_update 调用）
    python project_b\\refresh_index_baseline.py --force        # 强制重跑
    python project_b\\refresh_index_baseline.py --check-only   # 只看新鲜度
退出码：0 = 已刷新或无需刷新（含干净跳过）；1 = 刷新失败。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
STATE = LOGS / "index_baseline_state.json"

BM = Path(r"E:\wx\wx_textmine\00_build_matrix.py")
BASELINE_DIR = Path(r"E:\wx\论文素材_王晰作传\基线口径")
COMPUTE = BASELINE_DIR / "compute_baseline_v1.py"
CARDS = BASELINE_DIR / "generate_year_cards.py"   # 年度卡 + data/archive_digest.json（读长表算 index_mean）
LONG_CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
ADDON = Path(r"E:\wx\指数数据库\增补数据库2025.2.22-")
SITE_BASELINE = ROOT / "data" / "archive_baseline.json"


def log(msg: str) -> None:
    ts = dt.datetime.now().strftime("%H:%M:%S")
    print("[%s] %s" % (ts, msg), flush=True)


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(d: dict) -> None:
    LOGS.mkdir(exist_ok=True)
    d["updated_at"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    STATE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def writable(p: Path) -> tuple[bool, str]:
    if not p.exists():
        return False, "目录不存在"
    probe = p / ("._wprobe_%d.tmp" % dt.datetime.now().microsecond)
    try:
        probe.write_text("x", encoding="utf-8")
        probe.unlink()
        return True, "可写"
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, e)


def newest_dayfile() -> dt.date | None:
    if not ADDON.is_dir():
        return None
    days = []
    for p in ADDON.glob("*.xlsx"):
        name = p.stem  # 2026.09.08
        try:
            days.append(dt.date(*[int(x) for x in name.split(".")[:3]]))
        except Exception:
            continue
    return max(days) if days else None


def long_table_max() -> tuple[dt.date | None, dict]:
    """读长表最新日期 + 年度池均值（不依赖 pandas：纯文本扫描尾部）。"""
    if not LONG_CSV.exists():
        return None, {}
    latest = None
    per_day: dict[str, list[float]] = {}
    import csv
    with open(LONG_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            d = (r.get("date") or "").strip()
            try:
                v = float(r["index"])
            except Exception:
                continue
            per_day.setdefault(d, []).append(v)
    if per_day:
        latest = dt.date.fromisoformat(max(per_day))
    annual = {}
    for y in sorted({d[:4] for d in per_day}):
        vals = [sum(v) / len(v) for d, v in per_day.items() if d.startswith(y) and len(v) >= 2]
        if len(vals) >= 30:
            annual[y] = round(sum(vals) / len(vals), 1)
    return latest, annual


def freshness() -> dict:
    nf = newest_dayfile()
    lm, annual = long_table_max()
    expect = (nf - dt.timedelta(days=1)) if nf else None
    lag = (nf - lm).days if (nf and lm) else None
    return {"newest_dayfile": nf.isoformat() if nf else None,
            "long_max": lm.isoformat() if lm else None,
            "expected_max": expect.isoformat() if expect else None,
            "lag_days": lag, "annual": annual}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="忽略每日一次节流")
    ap.add_argument("--check-only", action="store_true", help="只报告新鲜度")
    ap.add_argument("--timeout-matrix", type=int, default=2400)
    ap.add_argument("--timeout-baseline", type=int, default=900)
    ap.add_argument("--timeout-cards", type=int, default=900)
    ap.add_argument("--no-cards", action="store_true", help="跳过年度卡/摘要重跑")
    args = ap.parse_args()

    log("=" * 66)
    log("指数长表 + 基线 每日刷新")
    log("=" * 66)
    st = load_state()
    today = dt.date.today().isoformat()
    fr0 = freshness()
    log("刷新前：日档案最新 %s ｜ 长表最新 %s ｜ 期望 %s ｜ 滞后 %s 天"
        % (fr0["newest_dayfile"], fr0["long_max"], fr0["expected_max"], fr0["lag_days"]))
    if fr0["annual"]:
        log("现有年度值：" + " · ".join("%s=%s" % kv for kv in fr0["annual"].items()))

    if args.check_only:
        ok = (fr0["lag_days"] is not None and fr0["lag_days"] <= 1)
        log("结论：%s" % ("新鲜 ✅" if ok else "滞后 ❌（需刷新）"))
        return 0 if ok else 1

    if st.get("last_run_date") == today and not args.force:
        log("[skip] 今日已刷新过（%s）—— 加 --force 可强制" % st.get("last_run_at"))
        return 0

    for d in (LONG_CSV.parent, BASELINE_DIR):
        ok, why = writable(d)
        log("  [%s] 写权限 %s — %s" % ("OK " if ok else "!! ", d, why))
        if not ok:
            log("[skip] 写权限不足（受限会话/沙箱）→ 本次干净跳过，未改动任何数据")
            log("      请在普通 PowerShell 或操作中心里运行本脚本")
            return 0

    steps = [
        ("重建指数长表", [sys.executable, "-X", "utf8", str(BM)], BM.parent, args.timeout_matrix),
        ("重跑基线", [sys.executable, "-X", "utf8", str(COMPUTE)], BASELINE_DIR, args.timeout_baseline),
        ("重跑年度卡/摘要", [sys.executable, "-X", "utf8", str(CARDS)], BASELINE_DIR, args.timeout_cards),
    ]
    if args.no_cards:
        steps = steps[:2]
    for name, cmd, cwd, to in steps:
        log("-- %s --" % name)
        r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                           encoding="utf-8", errors="ignore", timeout=to)
        tail = [x for x in (r.stdout or "").splitlines() if x.strip()][-4:]
        for x in tail:
            log("   " + x[:150])
        if r.returncode != 0:
            log("[X] %s 失败 returncode=%s：%s" % (name, r.returncode, (r.stderr or "")[-300:]))
            save_state({**st, "last_attempt": today, "last_result": "fail:" + name})
            return 1

    fr1 = freshness()
    log("刷新后：长表最新 %s ｜ 期望 %s ｜ 滞后 %s 天"
        % (fr1["long_max"], fr1["expected_max"], fr1["lag_days"]))
    if fr1["annual"]:
        log("新年度值：" + " · ".join("%s=%s" % kv for kv in fr1["annual"].items()))
    site_ok = SITE_BASELINE.exists()
    if site_ok:
        try:
            s = json.loads(SITE_BASELINE.read_text(encoding="utf-8"))
            log("站点已同步：%s ｜ 年度 %s" % (s.get("区间"),
                " · ".join("%s=%s" % (a["year"], a["mean"]) for a in s.get("annual", []))))
        except Exception as e:
            log("[!] 站点 JSON 读取异常：%s" % e)

    ok = (fr1["lag_days"] is not None and fr1["lag_days"] <= 1)
    save_state({"last_run_date": today, "last_run_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_result": "ok" if ok else "ok-but-lag",
                "long_max": fr1["long_max"], "expected_max": fr1["expected_max"],
                "lag_days": fr1["lag_days"], "annual": fr1["annual"]})
    log("结论：%s" % ("已刷新且新鲜 ✅" if ok else "已刷新但仍有滞后 ⚠️（检查日档案是否齐全）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
