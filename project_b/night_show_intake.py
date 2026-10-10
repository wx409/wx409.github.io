# -*- coding: utf-8 -*-
"""night_show_intake.py —— 演出夜自动入库（计划任务 wx409_show_intake，每晚 23:30）

做什么
------
1. 读 `data/event_lifecycle.json`，判断**今天是否有已登记的演出**（支持多场次：`show_dates` 或
   备注里的「M月D-D日」写法，如《沉响与长歌》的 10月9-10日 两场）。
2. 命中 → 调 `add_show.py`：补「开演」里程碑 + 重算活动总表/生命周期（幂等，重复跑安全）。
3. 若存在待填歌单 `E:\\wx\\index_records\\setlist_pending.txt` → 作为 `--setlist --append-setlist`
   并入（第二场加歌用），处理完改名为 `.done_<日期>`。
4. 默认接着跑 `deploy_all.py` + `git push origin main`（`--no-publish` 可关）。
5. 没演出 → 静默退出 0（不产生任何改动）。

用户只需做一件事（可选）：把当晚歌单按「顿号/逗号」分隔粘进 `setlist_pending.txt`。

用法：python -X utf8 project_b\\night_show_intake.py [--date 2026-10-10] [--no-publish] [--dry]
日志：temp\\night_show_intake.log
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
LIFECYCLE = ROOT / "data" / "event_lifecycle.json"
PENDING = Path(r"E:\wx\index_records\setlist_pending.txt")
LOG = ROOT / "temp" / "night_show_intake.log"
TEMPLATE = ("# 演出夜待填歌单 —— 每晚 23:30 由计划任务 wx409_show_intake 读取\n"
            "# 用法：把当晚歌单粘到本文件末尾即可（曲名用「、」或逗号分隔，多行也行）\n"
            "# 「#」开头的行会被忽略；处理完本文件会归档为 setlist_pending.txt.done_<日期>，并重建本模板\n"
            "# 例：嘎达梅林、忘不了、Your Man\n")


def read_pending() -> str:
    """只取非注释行（# 开头忽略），别的都不管。"""
    if not PENDING.exists():
        return ""
    lines = [x for x in PENDING.read_text(encoding="utf-8").splitlines()
             if x.strip() and not x.lstrip().startswith("#")]
    return "\n".join(lines).strip()


def ensure_pending() -> None:
    if not PENDING.exists():
        PENDING.parent.mkdir(parents=True, exist_ok=True)
        PENDING.write_text(TEMPLATE, encoding="utf-8")


def log(msg: str) -> None:
    line = "[%s] %s" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def event_dates(ev: dict) -> set[str]:
    """该事件的所有演出日：显式 show_dates ∪ show_date ∪ 备注/标题里的「M月D-D日」（跨年取 show_date 的年份）。"""
    out = set(ev.get("show_dates") or [])
    if ev.get("show_date"):
        out.add(ev["show_date"])
    year = (ev.get("show_date") or "")[:4] or str(dt.date.today().year)
    for src in (ev.get("show_date_note"), ev.get("note"), ev.get("title")):
        for m in re.finditer(r"(\d{1,2})月(\d{1,2})[-–~至](\d{1,2})日", src or ""):
            mo, d1, d2 = (int(x) for x in m.groups())
            for d in range(d1, d2 + 1):
                try:
                    out.add(dt.date(int(year), mo, d).isoformat())
                except ValueError:
                    pass
    return out


def selftest() -> int:
    ev = {"show_date": "2026-10-09", "show_date_note": "2026年10月9-10日 两场（官宣文案）"}
    ds = event_dates(ev)
    assert "2026-10-09" in ds and "2026-10-10" in ds, ds
    assert "2026-10-11" not in ds
    assert event_dates({"show_date": "2026-05-20"}) == {"2026-05-20"}
    assert event_dates({"show_date": "2026-05-20", "show_dates": ["2026-05-20", "2026-05-21"]}) == {"2026-05-20", "2026-05-21"}
    print("selftest OK")
    return 0


def run(cmd: list[str], desc: str) -> int:
    log("-- %s --" % desc)
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="ignore")
    for line in [x for x in (r.stdout or "").splitlines() if x.strip()][-4:]:
        log("   " + line[:160])
    if r.returncode != 0:
        log("[X] %s 失败 rc=%d %s" % (desc, r.returncode, (r.stderr or "")[-200:]))
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--no-publish", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    today = a.date
    events = json.loads(LIFECYCLE.read_text(encoding="utf-8")).get("events", [])
    hits = [e for e in events if today in event_dates(e)]
    log("=== 演出夜入库 %s ｜ 登记事件 %d 个 ｜ 命中 %d 个 ===" % (today, len(events), len(hits)))
    for e in hits:
        log("   命中：%s（%s）" % (e.get("title", "")[:40], e.get("venue", "")))
    if not hits:
        log("今天没有已登记的演出，退出（无改动）")
        return 0
    if a.dry:
        log("[dry] 不改任何文件")
        return 0
    ensure_pending()

    rc = 0
    for e in hits:
        title = e.get("title") or ""
        key = re.sub(r"[《》\s·、（()）]", "", title)[:4]
        cmd = [sys.executable, "-X", "utf8", str(ROOT / "project_b" / "add_show.py"),
               "--date", today, "--name", title, "--city", e.get("city") or "",
               "--venue", e.get("venue") or "", "--match", key, "--held-date", today]
        pending = read_pending()
        if pending:
            cmd += ["--setlist", pending, "--append-setlist"]
            log("   待填歌单已读取（%d 字符）" % len(pending))
        rc |= run(cmd, "演出登记：%s" % title[:24])
        if pending:
            PENDING.rename(PENDING.with_name(PENDING.name + ".done_" + today))
            ensure_pending()
            log("   待填歌单已归档为 .done_%s，并重建空模板" % today)

    if not a.no_publish:
        rc |= run([sys.executable, "-X", "utf8", str(ROOT / "project_b" / "deploy_all.py")], "全站发布 deploy_all")
        rc |= run(["git", "push", "origin", "main"], "git push")
    log("=== 完成 rc=%d ===" % rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
