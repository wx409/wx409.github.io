# -*- coding: utf-8 -*-
"""add_show.py —— 新演出/巡演「一次登记，全站生效」（幂等）

解决「每来一个新演出都要手写一串操作」的问题。一条命令走完登记 + 派生 + 发布：

  1. 本地演出长表 E:\\wx\\index_records\\王晰演出活动.xlsx 追加一行（写前自动备份；
     关键字命中已有行则跳过，不重复登记）
  2. 站点 data/timeline.json upsert（生涯时间轴；timeline.html / data-timeline.html 客户端直读）
  3. 站点 data/event_lifecycle.json upsert（活动生命周期；--held-date 追加「开演」里程碑）
  4. 派生重算：build_activity_master.py → track_event_lifecycle.py（指数前后窗口）
  5. --publish：deploy_all.py（全站页面重建 + 全部审计 + git commit + IndexNow）

用法：
  python -X utf8 project_b\\add_show.py --date 2026-10-09 --name "《沉响与长歌》演唱会 北京首场" \\
      --city 北京 --venue 北京天桥艺术中心·大剧场 --stage 东演 --match 沉响 \\
      --note "制作人：王晰、陈梦帆；主演：王晰 × 傲日其愣" --source "中国东方演艺集团官宣" \\
      --held-date 2026-10-09 --publish

  只登记不发布：去掉 --publish   只预演：加 --dry   自检：--selftest
  演唱曲目：--setlist "曲1、曲2"（留空则该行不进大屏辐射带动分析）
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XLSX = Path(r"E:\wx\index_records\王晰演出活动.xlsx")
TIMELINE = ROOT / "data" / "timeline.json"
LIFECYCLE = ROOT / "data" / "event_lifecycle.json"


def slug(name: str, date: str) -> str:
    """书名号/空格/标点去掉 → ascii 拼音不可得，用日期 + 关键词做稳定 id。"""
    key = re.sub(r"[《》\s·、「」（）()]", "", name)[:12]
    return "%s-%s" % (re.sub(r"[^\w]", "", key) or "show", date)


def match_key(name: str, override: str | None) -> str:
    if override:
        return override
    core = re.sub(r"[《》\s·、「」（）()]", "", name)
    return core[:4] or name


def hit(text: str, key: str) -> bool:
    return bool(key) and key in (text or "")


def norm_setlist(s: str) -> str:
    """按长表口径规整歌单：、分隔 + canon()，丢弃 <2 或 >24 字的片段（标签不是歌名）。"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from song_names import canon
    out = []
    for x in re.split(r"[、,，;；/\n]+", s or ""):
        x = x.strip()
        if 2 <= len(x) <= 24 and not x.isdigit() and x not in out:
            out.append(canon(x))
    return "、".join(out)


def upsert_xlsx(a, log) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(XLSX)
    ws = wb.active
    hdr = [c.value for c in ws[1]]
    col = {n: hdr.index(n) + 1 for n in hdr if n}

    def backup():
        bak = XLSX.with_name("%s.bak_%s" % (XLSX.stem, dt.datetime.now().strftime("%Y%m%d_%H%M")))
        shutil.copy2(XLSX, bak)
        return bak.name

    for row in ws.iter_rows(min_row=2):
        if not hit(str(row[col["演出名称"] - 1].value or ""), a.key):
            continue
        cell = row[col["演唱曲目"] - 1]
        old = str(cell.value or "").strip()
        if not a.setlist:
            return "xlsx: 已存在同名行，跳过（无新歌单）"
        if not old:
            bak = backup()
            cell.value = a.setlist
            wb.save(XLSX)
            return "xlsx: 回填空的「演唱曲目」（备份 %s）" % bak
        if a.append_setlist:
            have = [x for x in old.split("、") if x]
            add = [x for x in a.setlist.split("、") if x and x not in have]
            if not add:
                return "xlsx: 歌单无新增，未改动"
            cell.value = old + "、" + "、".join(add)
            wb.save(XLSX)
            return "xlsx: 并入 %d 首新歌（%s）" % (len(add), "、".join(add[:6]))
        return "xlsx: 已有「演唱曲目」，未覆盖（第二场加歌请加 --append-setlist）"

    bak = backup()
    seq = max([r[0] for r in ws.iter_rows(min_row=2, max_col=1, values_only=True) if isinstance(r[0], int)] or [0]) + 1
    ws.append([seq, a.name, dt.datetime.fromisoformat(a.date), a.city, a.note or "", a.setlist or ""])
    wb.save(XLSX)
    return "xlsx: 追加一行（序号 %d），备份 %s" % (seq, bak)


def upsert_timeline(a, log) -> str:
    data = json.loads(TIMELINE.read_text(encoding="utf-8"))
    events = data if isinstance(data, list) else data.get("events", [])
    for e in events:
        if hit(e.get("title", ""), a.key):
            if a.held_dates:
                tag = "（%s 首场已开演）" % a.held_dates[0][5:] if len(a.held_dates) == 1 else "（已开演 %s）" % "、".join(d[5:] for d in a.held_dates)
                e["title"] = re.sub(r"（[^）]*已开演[^）]*）", "", e["title"]) + tag
                e["source"] = re.sub(r"；已开演核实.*$", "", e.get("source") or "") + "；已开演核实"
            return "timeline: 命中已有条目，已更新标题/出处"
    events.append({"date": a.date, "type": a.type, "title": a.name,
                   "source": a.source or "", "stage": a.stage})
    events.sort(key=lambda e: e.get("date", ""))
    if isinstance(data, list):
        data[:] = events
    else:
        data["events"] = events
    TIMELINE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return "timeline: 新追加 1 条（%s %s）" % (a.date, a.name[:20])


def upsert_lifecycle(a, log) -> str:
    data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    evs = data.setdefault("events", [])
    ev = next((e for e in evs if hit(e.get("title", ""), a.key)), None)
    created = False
    if ev is None:
        ev = {"id": slug(a.name, a.date), "title": a.name, "organizer": a.organizer or "",
              "venue": a.venue or "", "city": a.city, "show_date": a.date,
              "note": a.note or "", "source_url": a.source or "", "milestones": []}
        evs.append(ev)
        created = True
    if a.held_dates:
        have = {(m.get("kind"), m.get("date")) for m in ev.get("milestones", [])}
        for d in a.held_dates:
            if ("开演", d) not in have:
                ev.setdefault("milestones", []).append(
                    {"kind": "开演", "date": d, "source": a.source or "", "source_label": "已开演核实"})
                created = True
    LIFECYCLE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return "lifecycle: %s%s" % ("新登记" if created else "已更新", ev["title"][:24])


def run(script: Path, log) -> None:
    r = subprocess.run([sys.executable, "-X", "utf8", str(script)], cwd=str(ROOT),
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    tail = [x for x in (r.stdout or "").splitlines() if x.strip()][-2:]
    log("  %s → rc=%d %s" % (script.name, r.returncode, " | ".join(tail)[:120]))


def selftest() -> int:
    assert match_key("《沉响与长歌》演唱会 北京首场", None) == "沉响与长"
    assert match_key("《沉响与长歌》演唱会", "沉响") == "沉响"
    assert hit("中国东方演艺集团《沉响与长歌》演唱会·王晰 × 傲日其愣", "沉响")
    assert not hit("六巡「回」广州站", "沉响")
    assert slug("《沉响与长歌》演唱会", "2026-10-09").endswith("2026-10-09")
    print("selftest OK")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="新演出/巡演一次登记，全站生效")
    p.add_argument("--date", required=False)
    p.add_argument("--name")
    p.add_argument("--city", default="北京")
    p.add_argument("--venue", default="")
    p.add_argument("--organizer", default="")
    p.add_argument("--stage", default="东演")
    p.add_argument("--type", default="concert", choices=["concert", "tour", "career", "variety"])
    p.add_argument("--note", default="")
    p.add_argument("--source", default="")
    p.add_argument("--setlist", default="")
    p.add_argument("--match", default=None, help="命中已有条目的关键字（默认取名称前 4 字）")
    p.add_argument("--held-date", default=None, help="已开演日期（可逗号分隔多场；追加「开演」里程碑，时间轴标题标已开演）")
    p.add_argument("--append-setlist", action="store_true",
                   help="把 --setlist 并入已有「演唱曲目」（默认：已有内容则跳过，用于第二场加歌）")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--publish", action="store_true", help="登记后跑 deploy_all.py 全站发布")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        return selftest()
    if not a.date or not a.name:
        p.error("--date 与 --name 必填")
    dt.date.fromisoformat(a.date)
    a.key = match_key(a.name, a.match)
    a.held_dates = [d.strip() for d in (a.held_date or "").split(",") if d.strip()]
    for d in a.held_dates:
        dt.date.fromisoformat(d)
    a.setlist = norm_setlist(a.setlist)

    log = lambda s: print(s, flush=True)
    log("登记：%s ｜ %s ｜ 关键字命中「%s」%s" % (a.date, a.name, a.key,
        "｜已开演 %s" % "、".join(a.held_dates) if a.held_dates else ""))
    if a.setlist:
        log("歌单规整为 %d 首：%s" % (len(a.setlist.split("、")), a.setlist[:80]))
    if a.dry:
        log("[dry] 不改任何文件")
        return 0

    log(upsert_xlsx(a, log))
    log(upsert_timeline(a, log))
    log(upsert_lifecycle(a, log))

    log("派生重算：")
    run(ROOT / "project_b" / "build_activity_master.py", log)
    run(ROOT / "project_b" / "track_event_lifecycle.py", log)
    if a.publish:
        log("全站发布 deploy_all.py（页面重建 + 审计 + 提交 + IndexNow）…")
        run(ROOT / "project_b" / "deploy_all.py", log)
        log("下一步：git push origin main（沙箱外手动）→ audit_live.py --wait 180")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
