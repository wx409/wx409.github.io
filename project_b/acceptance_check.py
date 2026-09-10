# -*- coding: utf-8 -*-
"""acceptance_check.py —— 2026-09-09 停摆事故「验收总检」（一条命令给出全貌）

把这次事故的所有处置项集中体检，输出 markdown 报告 + 退出码：

  A 根因消除：Windows 自动重启是否已抑制（活动时间/暂停更新/重启通知/服务）
  B 自愈与告警：看门狗自测 + 是否已接入 auto_update + 桌面告警通道
  C 口径修正：00_build_matrix 是否修正映射 + 归属自测（合成数据）
  D 数据状态：日档案最新 / 长表最新 / 内部空洞 / 9-08 与 9-09 是否已回补
  E 站点一致性：data/archive_baseline.json 与长表是否同口径同值
  F 任务形态：两个关键任务的登录类型与触发器（S4U 是否已应用）
  G 产物与工作区：报告是否齐全、git 是否干净

判定：FAIL 项会让退出码为 1；WARN 项（如"S4U 待执行""9/8 待补文件"）不影响退出码。

用法：
    python project_b\\acceptance_check.py            # 体检 + 出报告
    python project_b\\acceptance_check.py --json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
sys.path.insert(0, str(ROOT / "project_b"))

import watchdog_batches as w  # noqa: E402  复用长表扫描/日档案探测

BM_SRC = Path(r"E:\wx\wx_textmine\00_build_matrix.py")
SITE_BASELINE = ROOT / "data" / "archive_baseline.json"
REPORTS = ["更新重启停摆_诊断与加固_20260910.md", "指数长表日期偏移核查_20260910.md",
           "日期偏移影子验证_20260910.md", "运维备忘_20260907.md"]

OK, WARN, FAIL = "OK", "WARN", "FAIL"
rows: list[dict] = []


def add(section: str, name: str, status: str, evidence: str = "") -> None:
    rows.append({"section": section, "name": name, "status": status, "evidence": evidence[:400]})
    mark = {OK: "✅", WARN: "⚠️", FAIL: "❌"}[status]
    print("  %s [%s] %s%s" % (mark, section, name, (" — " + evidence[:150]) if evidence else ""))


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 600) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="ignore", timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 99, str(e)


def check_windows_update() -> None:
    ps = ("$ux=Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\WindowsUpdate\\UX\\Settings' -EA SilentlyContinue;"
          "$au=Get-ItemProperty 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU' -EA SilentlyContinue;"
          "[pscustomobject]@{ah_s=$ux.ActiveHoursStart; ah_e=$ux.ActiveHoursEnd;"
          "pause=$ux.PauseUpdatesExpiryTime; notify=$ux.RestartNotificationsAllowed2;"
          "au=$au.AUOptions; noreboot=$au.NoAutoRebootWithLoggedOnUsers} | ConvertTo-Json -Compress")
    rc, out = run(["powershell", "-NoProfile", "-Command", ps], timeout=60)
    try:
        d = json.loads(out.strip().splitlines()[-1])
    except Exception:
        add("A 根因", "读取 Windows 更新设置", WARN, "无法解析（%s）" % out[-120:])
        return
    ok_ah = d.get("ah_s") == 6 and d.get("ah_e") == 23
    add("A 根因", "活动时间已收窄到 06:00–23:00", OK if ok_ah else FAIL,
        "ActiveHours %s–%s" % (d.get("ah_s"), d.get("ah_e")))
    add("A 根因", "自动更新已暂停", OK if d.get("pause") else FAIL, "PauseUpdatesExpiryTime=%s" % d.get("pause"))
    add("A 根因", "重启前弹通知", OK if d.get("notify") == 1 else WARN, "RestartNotificationsAllowed2=%s" % d.get("notify"))
    add("A 根因", "已登录不自动重启策略", OK if d.get("noreboot") == 1 else WARN, "NoAutoRebootWithLoggedOnUsers=%s" % d.get("noreboot"))


def check_watchdog() -> None:
    rc, out = run([sys.executable, "-X", "utf8", str(ROOT / "project_b" / "watchdog_selftest.py")])
    tail = [x for x in out.splitlines() if "通过" in x]
    add("B 自愈", "看门狗自测", OK if rc == 0 else FAIL, tail[-1] if tail else "无输出")
    src = (ROOT / "project_b" / "auto_update.py").read_text(encoding="utf-8", errors="ignore")
    add("B 自愈", "看门狗已接入 auto_update", OK if "run_watchdog" in src else FAIL)
    src_w = (ROOT / "project_b" / "watchdog_batches.py").read_text(encoding="utf-8", errors="ignore")
    add("B 自愈", "桌面告警通道（站内通知之外）", OK if "desktop_alert" in src_w else WARN)
    add("B 自愈", "长表刷新已接入 auto_update", OK if "run_refresh_index" in src else FAIL)


def check_mapping() -> None:
    if not BM_SRC.exists():
        add("C 口径", "构建脚本可读", FAIL, str(BM_SRC))
        return
    txt = BM_SRC.read_text(encoding="utf-8", errors="ignore")
    ok = "昨日音乐指数属于前一天" in txt
    add("C 口径", "00_build_matrix 已修正日期映射", OK if ok else FAIL,
        "补丁标记%s" % ("存在" if ok else "缺失"))
    rc, out = run([sys.executable, "-X", "utf8", str(ROOT / "project_b" / "mapping_attribution_selftest.py")])
    tail = [x for x in out.splitlines() if "通过" in x]
    add("C 口径", "归属自测（合成数据）", OK if rc == 0 else FAIL, tail[-1] if tail else "无输出")


def check_data() -> dict:
    nf = w.newest_dayfile_date()
    scan = w.long_table_scan()
    lt = scan["max"]
    gaps = scan["gaps"]
    add("D 数据", "日档案最新日期", OK if nf else FAIL, str(nf))
    add("D 数据", "长表最新日期", OK if lt else FAIL, str(lt))
    lag = (nf - lt).days if (nf and lt) else None
    if lag is None:
        add("D 数据", "长表滞后", WARN, "无法判定")
    else:
        add("D 数据", "长表滞后 ≤1 天", OK if lag <= 1 else FAIL, "%s 天" % lag)
    add("D 数据", "最近窗口内无空洞", OK if not gaps else FAIL, "缺 " + "、".join(gaps) if gaps else "无")

    # 事故两天
    dates = set()
    import csv
    if w.LONG_CSV.exists():
        with open(w.LONG_CSV, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                d = (r.get("date") or "").strip()
                if d:
                    dates.add(d)
    for day in ("2026-09-08", "2026-09-09"):
        hit = day in dates
        add("D 数据", "事故日 %s 已回补" % day, OK if hit else WARN,
            "已在长表" if hit else "尚未（9/9 等今晚 23:55 批次；9/8 等文件或准终值备用）")
    return {"dates": sorted(dates)[-5:], "max": lt.isoformat() if lt else None}


def check_site() -> None:
    if not SITE_BASELINE.exists():
        add("E 站点", "站点基线 JSON 存在", FAIL, str(SITE_BASELINE))
        return
    try:
        site = json.loads(SITE_BASELINE.read_text(encoding="utf-8"))
    except Exception as e:
        add("E 站点", "站点基线 JSON 可解析", FAIL, str(e))
        return
    add("E 站点", "站点基线 JSON 可解析", OK,
        "区间 %s" % (site.get("区间"),))
    # 与长表算出的年度值比对
    import csv
    import statistics
    per: dict[str, list[float]] = {}
    with open(w.LONG_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            d = (r.get("date") or "").strip()
            if not d:
                continue
            try:
                per.setdefault(d[:4], []).append(float(r["index"]))
            except Exception:
                continue
    mism = []
    for a in site.get("annual", []):
        y = a["year"]
        ds = [d for d in per if d.startswith(y)]
        vals = [statistics.mean(per[d]) for d in ds if len(per[d]) >= 2]
        calc = round(statistics.mean(vals), 1) if len(vals) >= 30 else None
        if calc is not None and abs(calc - a["mean"]) > 0.15:
            mism.append("%s 站点%s≠长表%s" % (y, a["mean"], calc))
    add("E 站点", "站点年度值与长表一致", OK if not mism else FAIL, "；".join(mism) or "全部一致")
    add("E 站点", "覆盖不足年份已透明登记", OK if "覆盖不足年份" in site else WARN,
        str(site.get("覆盖不足年份")))

    # 年度卡摘要（archive_digest）——大屏档案层会把它和上面的年度表**并排渲染**，
    # 两者必须同源同值，否则同一个面板里会出现两套数字（2026-09-10 实际发生过）。
    dg_p = ROOT / "data" / "archive_digest.json"
    if not dg_p.exists():
        add("E 站点", "年度卡摘要存在", WARN, str(dg_p))
        return
    try:
        dg = json.loads(dg_p.read_text(encoding="utf-8"))
    except Exception as e:
        add("E 站点", "年度卡摘要可解析", FAIL, str(e))
        return
    bm = {a["year"]: a["mean"] for a in site.get("annual", [])}
    mism2, badmode = [], []
    for y in dg.get("years", []):
        k = str(y.get("year"))
        if k in bm:
            if y.get("index_mean") != bm[k]:
                mism2.append("%s 卡表%s≠基线%s" % (k, y.get("index_mean"), bm[k]))
        elif y.get("index_mean") is not None:
            badmode.append("%s 无基线却标定量(%s)" % (k, y.get("index_mean")))
    add("E 站点", "年度卡摘要与基线同值（同一面板两套数字=缺陷）",
        OK if not mism2 else FAIL, "；".join(mism2) or "全部一致")
    add("E 站点", "年度卡无「样本不足却定量」年份", OK if not badmode else FAIL,
        "；".join(badmode) or "无（2022 等单日样本已归为定性）")
    add("E 站点", "年度卡生成日期为派生值", OK if dg.get("generated") else WARN,
        "generated=%s ／ data_through=%s" % (dg.get("generated"), dg.get("data_through")))


def check_tasks() -> None:
    for name in ("QQMusicDashboardAutoStart", "WangXiArchiveAutoUpdate"):
        p = Path(r"C:\Windows\System32\Tasks") / name
        if not p.exists():
            add("F 任务", name, WARN, "任务 XML 不可读")
            continue
        try:
            x = p.read_text(encoding="utf-16", errors="ignore")
            lt = re.search(r"<LogonType>(\w+)</LogonType>", x)
            trg = re.findall(r"<(LogonTrigger|BootTrigger|CalendarTrigger)>", x)
            lt = lt.group(1) if lt else "?"
            add("F 任务", "%s 登录类型=%s" % (name, lt),
                OK if lt == "S4U" else WARN,
                "触发器 %s%s" % ("、".join(sorted(set(trg))),
                                 "" if lt == "S4U" else "（仍是 InteractiveToken：重启后需登录才会跑）"))
        except Exception as e:
            add("F 任务", name, WARN, str(e))


def check_artifacts() -> None:
    missing = [r for r in REPORTS if not (TEMP / r).exists()]
    add("G 产物", "诊断/核查报告齐全", OK if not missing else WARN, "缺 " + "、".join(missing) if missing else "齐全")
    rc, out = run(["git", "status", "--porcelain"], timeout=60)
    add("G 产物", "git 工作区干净", OK if not out.strip() else WARN, out.strip().splitlines()[0] if out.strip() else "干净")
    rc2, out2 = run(["git", "rev-list", "--count", "origin/main..HEAD"], timeout=60)
    n = out2.strip() if rc2 == 0 else "?"
    add("G 产物", "未推送提交数", OK if n == "0" else WARN, "%s 个" % n)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    print("=" * 72)
    print("2026-09-09 停摆事故 · 验收总检（%s）" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 72)
    check_windows_update()
    check_watchdog()
    check_mapping()
    data = check_data()
    check_site()
    check_tasks()
    check_artifacts()

    n_ok = sum(1 for r in rows if r["status"] == OK)
    n_warn = sum(1 for r in rows if r["status"] == WARN)
    n_fail = sum(1 for r in rows if r["status"] == FAIL)

    TEMP.mkdir(exist_ok=True)
    out_md = TEMP / ("事故验收_%s.md" % dt.date.today().strftime("%Y%m%d"))
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# 2026-09-09 停摆事故 · 验收总检\n\n生成：%s\n\n"
                % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        f.write("**结论：✅ %d 项通过 ｜ ⚠️ %d 项待观察/待执行 ｜ ❌ %d 项失败**\n\n" % (n_ok, n_warn, n_fail))
        f.write("| 分组 | 检查项 | 结果 | 证据 |\n|---|---|---|---|\n")
        for r in rows:
            f.write("| %s | %s | %s | %s |\n" % (r["section"], r["name"],
                                                {OK: "✅", WARN: "⚠️", FAIL: "❌"}[r["status"]], r["evidence"]))
        f.write("\n最近 5 个长表日期：%s\n" % "、".join(data.get("dates", [])))
    print("-" * 72)
    print("结论：✅ %d ｜ ⚠️ %d ｜ ❌ %d" % (n_ok, n_warn, n_fail))
    print("报告：%s" % out_md)
    if args.json:
        print(json.dumps({"ok": n_ok, "warn": n_warn, "fail": n_fail, "rows": rows},
                         ensure_ascii=False, indent=1))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
