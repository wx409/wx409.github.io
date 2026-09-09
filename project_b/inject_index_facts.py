#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首页事实块注入（派生，禁手写）——修 3 处陈旧：巡演轮次/城市、指数覆盖天数、Last updated。

单一事实源：
  · data/calibers.json                      → 六轮巡演 59 场 / 全站 64 场 / 22 城
  · E:\\wx\\wx_textmine_out\\music_index_raw_coverage.json → 指数覆盖天数（span_days − missing_days）
      （缺失时回退 music_index_long.csv 的唯一日期数；再不行则删除该句，不写死数字）
  · git log -1 --format=%cs -- index.html   → Last updated（取最后提交日）

用法：
  python -X utf8 project_b/inject_index_facts.py            # 生成 + 注入
  python -X utf8 project_b/inject_index_facts.py --check     # 只校验（exit 1 = 与事实源不一致）
"""
from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "index.html"
COVERAGE_JSON = Path(r"E:\wx\wx_textmine_out\music_index_raw_coverage.json")
LONG_CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")

M_TOUR_START = "<!-- TOUR-FACTS:START（由 project_b/inject_index_facts.py 生成，勿手改）-->"
M_TOUR_END = "<!-- TOUR-FACTS:END -->"
M_NOTE_START = "<!-- UPDATE-NOTE:START（同上，勿手改）-->"
M_NOTE_END = "<!-- UPDATE-NOTE:END -->"
M_LU_START = "<!-- LAST-UPDATED:START（同上，勿手改）-->"
M_LU_END = "<!-- LAST-UPDATED:END -->"


def coverage_days() -> tuple[int, str, str] | None:
    """(覆盖天数, 起始日, 结束日)；优先取口径登记表 index_days，再回退数据源。"""
    # 1) 口径登记表（唯一事实源，由 build_calibers.py 派生）
    try:
        cal = {c["id"]: c for c in json.loads((ROOT / "data" / "calibers.json").read_text(encoding="utf-8"))["calibers"]}
        if "index_days" in cal:
            note = cal["index_days"].get("note") or ""
            m = re.search(r"(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})", note)
            return int(cal["index_days"]["value"]), (m.group(1) if m else ""), (m.group(2) if m else "")
    except Exception:
        pass
    # 2) 回退：原始库覆盖文件
    if COVERAGE_JSON.exists():
        try:
            d = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
            covered = int(d["span_days"]) - len(d.get("missing_days") or [])
            return covered, d.get("date_min", ""), d.get("date_max", "")
        except Exception:
            pass
    # 3) 回退：长表唯一日期
    if LONG_CSV.exists():
        try:
            dates = set()
            with io.open(LONG_CSV, encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    v = (row.get("date") or row.get("日期") or "").strip()
                    if v:
                        dates.add(v[:10])
            if dates:
                return len(dates), min(dates), max(dates)
        except Exception:
            pass
    return None


def git_last_commit_date(rel: str) -> str:
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel],
                           cwd=str(ROOT), capture_output=True, timeout=30)
        out = r.stdout.decode("utf-8", "replace").strip()
        return out or date.today().isoformat()
    except Exception:
        return date.today().isoformat()


def build() -> dict:
    cal = {c["id"]: c["value"] for c in json.loads((ROOT / "data" / "calibers.json").read_text(encoding="utf-8"))["calibers"]}
    tour_n, all_n, city_n = cal["shows_tour"], cal["shows_all"], cal["cities"]

    cov = coverage_days()
    tour_html = (
        f'{M_TOUR_START}\n'
        f'    <p>王晰自 2019 年起，已完成<strong>六轮</strong>全国个人巡回音乐会，'
        f'累计覆盖<strong id="city-count">{city_n}</strong>城'
        f'（六轮巡演 <strong>{tour_n}</strong> 场；含签唱会等非巡演演出，全站共 <strong>{all_n}</strong> 场）。'
        f'第六轮「回」正在进行中。</p>\n{M_TOUR_END}'
    )
    if cov:
        days, dmin, dmax = cov
        cov_line = f'当前已覆盖 <strong>{days}</strong> 天（{dmin} 至 {dmax}）'
    else:
        cov_line = '（覆盖天数待数据源生成）'
    note_html = (
        f'{M_NOTE_START}\n'
        f'            内容层更新周期：事件驱动（巡演/发行/重大报道后 48 小时内更新）<br>\n'
        f'            数据层更新周期：每日多批次自动监测，{cov_line}\n'
        f'        {M_NOTE_END}'
    )
    lu = git_last_commit_date("index.html")
    lu_html = (
        f'{M_LU_START}<em>This is a fan-maintained GEO knowledge base for Wang Xi, '
        f'optimized for AI search engines. Last updated: {lu}.</em>{M_LU_END}'
    )
    return {"tour": tour_html, "note": note_html, "lu": lu_html,
            "facts": {"tour_shows": tour_n, "all_shows": all_n, "cities": city_n,
                      "coverage_days": cov[0] if cov else None,
                      "date_min": cov[1] if cov else None, "date_max": cov[2] if cov else None,
                      "last_updated": lu}}


def inject(text: str, block: str, start: str, end: str, fallback_pat: str) -> tuple[str, bool]:
    """标记块存在则替换；否则按 fallback_pat 找到旧段落整体替换。返回 (新文本, 是否变化)。"""
    if start in text and end in text:
        new = re.sub(re.escape(start) + r".*?" + re.escape(end), lambda m: block, text, count=1, flags=re.S)
        return new, new != text
    m = re.search(fallback_pat, text, re.S)
    if not m:
        return text, False
    return text[:m.start()] + block + text[m.end():], True


def main() -> int:
    check = "--check" in sys.argv
    b = build()
    text = TARGET.read_text(encoding="utf-8")
    new_text = text

    new_text, c1 = inject(new_text, b["tour"], M_TOUR_START, M_TOUR_END,
                          r'<p>王晰自\s*2019\s*年起.*?第六轮「回」正在进行中。</p>')
    new_text, c2 = inject(new_text, b["note"], M_NOTE_START, M_NOTE_END,
                          r'<p class="update-note">.*?</p>')
    new_text, c3 = inject(new_text, b["lu"], M_LU_START, M_LU_END,
                          r'<p><em>This is a fan-maintained GEO knowledge base.*?</em></p>')

    changed = new_text != text
    if check:
        if changed:
            print("[FAIL] index.html 首页事实块与事实源不一致（重跑 inject_index_facts.py）")
            return 1
        print("[OK] index.html 首页事实块与事实源一致")
        return 0

    if changed:
        TARGET.write_text(new_text, encoding="utf-8", newline="")
    f = b["facts"]
    print(f"[首页事实] 巡演 {f['tour_shows']} 场 / 全站 {f['all_shows']} 场 / {f['cities']} 城；"
          f"覆盖 {f['coverage_days']} 天（{f['date_min']}→{f['date_max']}）；Last updated {f['last_updated']}")
    print(f"  注入: 巡演块={c1} 更新说明块={c2} Last updated={c3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
