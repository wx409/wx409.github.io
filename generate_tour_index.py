#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""演出详情目录生成器：以巡演歌单长表（单一事实源）为唯一场次输入，生成 live/index.html。

- 场次列表：长表（一至六巡全量场次），按轮次分组，替代手写维护
- 「数据效应*」列：从 dashboard/dashboard_data.json 读取 tour_song_effects
  （全站 / 歌单内 / 辐射带动 三口径），无数据场次留白「—」
- 每行详情链接：扫描 live/*.html 的 meta 标签建立「日期 → live 页」映射，已有 live 页的可跳转

用法：
  python generate_tour_index.py
  python generate_tour_index.py --setlist <长表.xlsx>
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

from update_index_table import build_effect_cell, load_effects

ROOT = Path(__file__).resolve().parent
DEFAULT_SETLIST = r"E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx"

# 轮次顺序与主题短名（长表「巡次」列含长名称，主题短名静态映射）
TOUR_ORDER = ["一巡", "二巡", "三巡", "四巡", "五巡", "六巡"]
TOUR_THEME = {
    "一巡": "Cherish珍晰",
    "二巡": "2020-2021 个人巡回",
    "三巡": "图景",
    "四巡": "肆益",
    "五巡": "吾",
    "六巡": "回",
}
ONGOING = {"六巡"}


def load_setlists(path: str) -> list[dict]:
    """读取长表 → 场次列表（日期/场次名/城市/轮次），唯一场次来源"""
    df = pd.read_excel(path, sheet_name="合并长表")
    df = df[df["曲目"].notna() & (df["曲目"].astype(str).str.strip() != "")]
    out = []
    for (date, scene, tour), _ in df.groupby(["日期", "场次", "巡次"]):
        d = str(date)[:10]
        m = re.match(r"^(一巡|二巡|三巡|四巡|五巡|六巡)", str(tour).strip())
        out.append(
            {
                "date": d,
                "date_display": d.replace("-", "."),
                "scene": str(scene).strip(),
                "city": re.split(r"[（(]", str(scene))[0].strip(),
                "lun": m.group(1) if m else "其他",
            }
        )
    out.sort(key=lambda x: (TOUR_ORDER.index(x["lun"]) if x["lun"] in TOUR_ORDER else 99, x["date"]))
    return out


def scan_live_pages(live_dir: Path) -> dict:
    """扫描 live/*.html 的 meta 标签 → {date: {filename, venue}}"""
    out = {}
    for f in sorted(live_dir.glob("*.html")):
        if f.name == "index.html":
            continue
        text = f.read_text(encoding="utf-8")

        def meta(name: str) -> str:
            m = re.search(rf'<meta name="{re.escape(name)}" content="([^"]*)"', text)
            return m.group(1) if m else ""

        d = meta("live-date")
        if d:
            out[d] = {"filename": f.name, "venue": meta("live-venue")}
    return out


def build_overview(by_lun: dict) -> str:
    rows = []
    for lun in TOUR_ORDER:
        items = by_lun.get(lun, [])
        if not items:
            continue
        dates = sorted(s["date"] for s in items)
        span = f'{dates[0][:7].replace("-", ".")} - {dates[-1][:7].replace("-", ".")}'
        ongoing = lun in ONGOING
        cls = "status-ongoing" if ongoing else "status-done"
        rows.append(
            f'<tr><td>{lun}</td><td>{TOUR_THEME.get(lun, "")}</td>'
            f'<td>{span}</td><td>{len(dates)}场</td>'
            f'<td class="{cls}">{"进行中" if ongoing else "已结束"}</td></tr>'
        )
    return "\n        ".join(rows)


def build_sections(by_lun: dict, effects: dict, live_pages: dict) -> str:
    blocks = []
    for lun in TOUR_ORDER:
        items = by_lun.get(lun, [])
        if not items:
            continue
        rows = []
        for s in items:
            lp = live_pages.get(s["date"])
            venue = lp["venue"] if lp and lp["venue"] else "—"
            if lp:
                detail = f'<td class="has-detail"><a href="live/{lp["filename"]}">完整实录 →</a></td>'
            else:
                detail = '<td class="no-detail">详情页待补充</td>'
            rows.append(
                f"<tr><td>{s['date_display']}</td><td>{s['scene']}</td>"
                f"<td>{venue}</td>{build_effect_cell(effects.get(s['date']))}"
                f"{detail}</tr>"
            )
        blocks.append(
            f"    <h2>{lun} · {TOUR_THEME.get(lun, '')}（{len(items)}场）</h2>\n"
            f"    <table>\n"
            f"        <tr><th>日期</th><th>场次</th><th>场馆</th><th>数据效应*</th><th>详情</th></tr>\n"
            f"        {chr(10).join('        ' + r for r in rows)}\n"
            f"    </table>"
        )
    return "\n\n".join(blocks)


def build_page(setlists: list[dict], effects: dict, live_pages: dict) -> str:
    by_lun = {}
    for s in setlists:
        by_lun.setdefault(s["lun"], []).append(s)
    has_detail = len(live_pages)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>演出详情目录 | 王晰个人巡回音乐会 2019-2026</title>
    <meta name="description" content="王晰2019-2026六轮全国个人巡回音乐会全部场次索引，含城市、日期、场馆、数据效应与详情页链接。">
    <link rel="canonical" href="https://wx409.github.io/live/">
    <meta property="og:title" content="演出详情目录 | 王晰个人巡回音乐会 2019-2026">
    <meta property="og:description" content="王晰六轮巡演全部场次索引，50+城市60+场次，含每场数据效应。">
    <meta property="og:url" content="https://wx409.github.io/live/">
    <meta property="og:image" content="https://wx409.github.io/cover.png">
    <meta name="twitter:image" content="https://wx409.github.io/cover.png">
    <meta property="og:type" content="website">
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      "name": "王晰个人巡回音乐会演出详情目录",
      "description": "王晰2019-2026六轮全国个人巡回音乐会全部场次索引，含城市、日期、场馆、数据效应与详情页链接。",
      "url": "https://wx409.github.io/live/",
      "isPartOf": {{
        "@type": "WebSite",
        "name": "王晰 GEO 资料站",
        "url": "https://wx409.github.io/"
      }}
    }}
    </script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; line-height: 1.8; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; }}
        h1 {{ color: #1a1a1a; border-bottom: 3px solid #c41e3a; padding-bottom: 10px; }}
        h2 {{ color: #2c2c2c; margin-top: 30px; border-left: 4px solid #c41e3a; padding-left: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px 10px; text-align: left; font-size: 14px; }}
        th {{ background: #f5f5f5; }}
        .nav {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .nav a {{ margin-right: 20px; font-weight: 500; color: #c41e3a; text-decoration: none; }}
        .status-ongoing {{ background: #fff3cd; padding: 2px 6px; border-radius: 3px; font-weight: bold; }}
        .status-done {{ color: #666; }}
        .notice {{ background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 20px 0; font-size: 14px; color: #555; }}
        .has-detail a {{ color: #c41e3a; font-weight: 500; }}
        .no-detail {{ color: #999; }}
        .footnote {{ color: #888; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">首页</a>
        <a href="/live-reviews.html">现场实录</a>
        <a href="/live/">演出详情</a>
        <a href="/discography.html">作品百科</a>
        <a href="/academic.html">学术研究</a>
        <a href="/gallery.html">视觉记录</a>
        <a href="/dashboard/">数据大屏</a>
        <a href="/map/">🗺️ 巡演地图</a>
    </div>

    <h1>演出详情目录</h1>
    <p>王晰 2019-2026 六轮全国个人巡回音乐会全部场次索引。场次清单以巡演歌单长表为唯一事实源自动生成；有独立详情页的场次可点击查看完整歌单、现场亮点与 FAQ。</p>

    <div class="notice">
        <strong>数据效应*</strong>：该场演出后 7 日平台指数，相对演出前（21~7 日）基线的变化（全站 / 歌单内 / 辐射带动三口径），数据来源 <a href="../dashboard/dashboard_data.json">dashboard_data.json</a>，随监测数据自动更新；无数据场次显示「—」。目前 {has_detail} 场已有独立详情页，其余将陆续补充。
    </div>

    <h2>巡演总览</h2>
    <table>
        <tr><th>轮次</th><th>主题</th><th>时间跨度</th><th>场次</th><th>状态</th></tr>
        {build_overview(by_lun)}
    </table>

{build_sections(by_lun, effects, live_pages)}

    <p class="footnote">场次清单数据来源：<a href="../dashboard/dashboard_data.json">数据大屏 dashboard_data.json</a> 与巡演歌单长表，随监测数据自动更新。详情页内容基于现场 repo 交叉验证与工作室官方发布，不收录未核实信息。</p>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="生成演出详情目录页 live/index.html")
    parser.add_argument("--setlist", default=DEFAULT_SETLIST, help="巡演歌单长表 xlsx 路径")
    parser.add_argument("--output", default="./live/index.html")
    args = parser.parse_args()

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    setlists = load_setlists(args.setlist)
    if not setlists:
        print(f"[X] 长表无场次数据: {args.setlist}")
        sys.exit(1)

    effects = load_effects(ROOT / "dashboard")
    live_pages = scan_live_pages(ROOT / "live")
    html = build_page(setlists, effects, live_pages)
    out_path.write_text(html, encoding="utf-8")

    matched = len({s["date"] for s in setlists} & set(effects.keys()))
    print(
        f"[OK] 已生成 {len(setlists)} 场目录 -> {out_path} "
        f"（数据效应 {matched} 场，详情页 {len(live_pages)} 场）"
    )


if __name__ == "__main__":
    main()
