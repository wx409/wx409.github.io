# -*- coding: utf-8 -*-
"""rebuild_after_backfill.py —— 补录后的全链路重建与验收（一条命令，逐步验真）

背景
----
2026-09-09 夜间批次停摆 → 日档案缺 `2026.09.09.xlsx`。用户从备份拷回后，
需要按顺序重跑数据链与站点链，**每一步都要验真**，不能"跑完就算"。

步骤（可用 --only 选择子集，全部幂等）：
    1. matrix   重建指数长表      python E:\\wx\\wx_textmine\\00_build_matrix.py
    2. baseline 基线/年度表/效应   python 基线口径\\compute_baseline_v1.py（内含自动同步站点 data/archive_baseline.json）
    3. cards    年度卡 20 张       python 基线口径\\generate_year_cards.py
    4. deploy   全流水线           python project_b\\deploy_all.py（内含 build_calibers/generate_llms/build_nav + 七道把关）
    5. audit    收尾把关           audit_caliber / audit_nav / audit_bat / audit_ops_coverage

用法：
    python project_b\\rebuild_after_backfill.py --dry-run                 # 只列步骤与命令
    python project_b\\rebuild_after_backfill.py --only matrix,baseline    # 只跑数据层（演练）
    python project_b\\rebuild_after_backfill.py                           # 全链路（含部署）
    python project_b\\rebuild_after_backfill.py --skip-deploy             # 除部署外全跑

输出：logs/rebuild_after_backfill_YYYYMMDD_HHMM.log + temp/全链路重建_<日期>.md
退出码：0 = 所选步骤全部通过；1 = 有步骤失败。
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
TEMP = ROOT / "temp"

BM = Path(r"E:\wx\wx_textmine\00_build_matrix.py")
BASELINE_DIR = Path(r"E:\wx\论文素材_王晰作传\基线口径")
COMPUTE = BASELINE_DIR / "compute_baseline_v1.py"
CARDS = BASELINE_DIR / "generate_year_cards.py"
DEPLOY = ROOT / "project_b" / "deploy_all.py"
AUDITS = ["audit_caliber.py", "audit_nav.py", "audit_bat.py", "audit_ops_coverage.py"]

STEPS: dict[str, dict] = {
    "matrix": {"title": "重建指数长表", "cmd": [sys.executable, "-X", "utf8", str(BM)], "cwd": BM.parent,
               "timeout": 2400},
    "baseline": {"title": "基线/年度表/事件效应 + 同步站点", "cmd": [sys.executable, "-X", "utf8", str(COMPUTE)],
                 "cwd": BASELINE_DIR, "timeout": 900},
    "cards": {"title": "年度卡 20 张", "cmd": [sys.executable, "-X", "utf8", str(CARDS)],
              "cwd": BASELINE_DIR, "timeout": 1800},
    "deploy": {"title": "全流水线部署（含七道把关）", "cmd": [sys.executable, "-X", "utf8", str(DEPLOY)],
               "cwd": ROOT, "timeout": 3600},
    "audit": {"title": "收尾把关（口径/导航/批处理/菜单覆盖）", "cmd": None, "cwd": ROOT, "timeout": 600},
}
ORDER = ["matrix", "baseline", "cards", "deploy", "audit"]

_RUNLOG: list[str] = []

# 步骤 → 该步必须可写的目录（用于预检；受限会话/权限不足会在第一步就暴露）
WRITE_DIRS: dict[str, list[Path]] = {
    "matrix": [Path(r"E:\wx\wx_textmine_out")],
    "baseline": [BASELINE_DIR, ROOT / "data"],
    "cards": [BASELINE_DIR, ROOT / "data"],
    "deploy": [ROOT, ROOT / "dashboard", ROOT / "data"],
    "audit": [],
}


def preflight(steps: list[str]) -> list[tuple[str, bool, str]]:
    """逐目录试写临时文件，返回 [(目录, 可写, 说明)]。"""
    out = []
    for s in steps:
        for d in WRITE_DIRS.get(s, []):
            if not d.exists():
                out.append((str(d), False, "目录不存在"))
                continue
            probe = d / ("._write_probe_%d.tmp" % dt.datetime.now().microsecond)
            try:
                probe.write_text("probe", encoding="utf-8")
                probe.unlink()
                out.append((str(d), True, "可写"))
            except Exception as e:
                out.append((str(d), False, "%s: %s" % (type(e).__name__, e)))
    return out


def log(msg: str) -> None:
    line = "[%s] %s" % (dt.datetime.now().strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    _RUNLOG.append(line)


def run_step(key: str, dry: bool) -> dict:
    st = STEPS[key]
    log("=== %s：%s ===" % (key, st["title"]))
    if dry:
        log("  (dry-run) 命令: %s" % (st["cmd"] if st["cmd"] else "内置四项审计"))
        return {"step": key, "title": st["title"], "ok": True, "detail": "dry-run"}

    if key == "audit":
        results = []
        for a in AUDITS:
            r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "project_b" / a)],
                               cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                               errors="ignore", timeout=st["timeout"])
            tail = [x for x in (r.stdout or "").splitlines() if x.strip()]
            tail = tail[-1] if tail else ""
            results.append((a, r.returncode, tail))
            log("  [%s] %-22s %s" % ("OK " if r.returncode == 0 else "!! ", a, tail[:90]))
        ok = all(rc == 0 for _a, rc, _t in results)
        return {"step": key, "title": st["title"], "ok": ok,
                "detail": "；".join("%s=%d" % (a, rc) for a, rc, _t in results)}

    r = subprocess.run(st["cmd"], cwd=str(st["cwd"]), capture_output=True, text=True,
                       encoding="utf-8", errors="ignore", timeout=st["timeout"])
    tail = [x for x in (r.stdout or "").splitlines() if x.strip()][-5:]
    for x in tail:
        log("  " + x[:150])
    if r.returncode != 0 and (r.stderr or "").strip():
        log("  stderr: " + (r.stderr or "").strip()[:300])
    return {"step": key, "title": st["title"], "ok": r.returncode == 0,
            "detail": "returncode=%s | %s" % (r.returncode, " / ".join(tail)[:300])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="逗号分隔的步骤子集（默认全部）：%s" % ",".join(ORDER))
    ap.add_argument("--skip-deploy", action="store_true", help="跳过 deploy 步骤")
    ap.add_argument("--dry-run", action="store_true", help="只列命令不执行")
    args = ap.parse_args()

    steps = [s.strip() for s in args.only.split(",") if s.strip()] or list(ORDER)
    for s in steps:
        if s not in STEPS:
            print("[X] 未知步骤: %s（可选：%s）" % (s, ",".join(ORDER)))
            return 2
    if args.skip_deploy and "deploy" in steps:
        steps.remove("deploy")

    log("=" * 72)
    log("补录后全链路重建：%s" % " → ".join(steps))
    log("=" * 72)

    if not args.dry_run:
        checks = preflight(steps)
        bad = [c for c in checks if not c[1]]
        for d, ok, why in checks:
            log("  [%s] 写权限 %s — %s" % ("OK " if ok else "!! ", d, why))
        if bad:
            log("")
            log("[X] 有目录不可写，已中止（未执行任何步骤）。常见原因：")
            log("    · 在受限会话/沙箱里运行（例如 DSH 的文件沙箱只允许写工作区）")
            log("    · 权限不足（请用管理员或该目录的属主账户运行）")
            log("    → 请在普通 PowerShell 里手动运行本脚本，或用操作中心「104 补录后全链路重建」")
            return 1

    results = [run_step(s, args.dry_run) for s in steps]

    LOGS.mkdir(exist_ok=True)
    TEMP.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    (LOGS / ("rebuild_after_backfill_%s.log" % stamp)).write_text("\n".join(_RUNLOG) + "\n", encoding="utf-8")

    allok = all(r["ok"] for r in results)
    out = TEMP / ("全链路重建_%s.md" % dt.date.today().strftime("%Y%m%d"))
    with open(out, "w", encoding="utf-8") as f:
        f.write("# 补录后全链路重建验收\n\n生成：%s\n\n| 步骤 | 说明 | 结果 | 详情 |\n|---|---|---|---|\n"
                % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        for r in results:
            f.write("| %s | %s | %s | %s |\n" % (r["step"], r["title"], "✅" if r["ok"] else "❌", r["detail"]))
        f.write("\n总结论：**%s**\n" % ("全部通过 ✅" if allok else "有步骤失败 ❌"))
    log("汇总报告：%s" % out)
    log("总结论：%s" % ("全部通过 ✅" if allok else "有步骤失败 ❌"))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
