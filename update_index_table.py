#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 live 目录 manifest → 按日期倒序重建首页「最新演出动态」表格。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TABLE_START = "<!-- LIVE_TABLE_START -->"
TABLE_END = "<!-- LIVE_TABLE_END -->"


def load_manifest(live_dir: Path) -> list[dict]:
    manifest_path = live_dir / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    entries = []
    for html_file in sorted(live_dir.glob("*.html")):
        text = html_file.read_text(encoding="utf-8")
        date = _meta(text, "live-date")
        if not date:
            continue
        entries.append(
            {
                "date": date,
                "date_display": date.replace("-", "."),
                "city": _meta(text, "live-city"),
                "venue": _meta(text, "live-venue"),
                "tour_display": _meta(text, "live-tour"),
                "status": _meta(text, "live-status"),
                "status_class": "highlight" if "首站" in _meta(text, "live-status") else "",
                "filename": html_file.name,
                "link": f"live/{html_file.name}",
                "link_text": "完整实录 →",
            }
        )
    entries.sort(key=lambda x: x["date"], reverse=True)
    return entries


def _meta(html: str, name: str) -> str:
    m = re.search(rf'<meta name="{re.escape(name)}" content="([^"]*)"', html)
    return m.group(1) if m else ""


def build_row(entry: dict) -> str:
    status_class = entry.get("status_class", "")
    status_td = (
        f'<td class="{status_class}">{entry["status"]}</td>'
        if status_class
        else f'<td>{entry["status"]}</td>'
    )
    return (
        f"<tr>"
        f"<td>{entry['date_display']}</td>"
        f"<td>{entry['city']}</td>"
        f"<td>{entry['venue']}</td>"
        f"<td>{entry['tour_display']}</td>"
        f"{status_td}"
        f'<td><a href="{entry["link"]}">{entry.get("link_text", "完整实录 →")}</a></td>'
        f"</tr>"
    )


def update_index(index_path: Path, entries: list[dict]) -> None:
    if not entries:
        print("[!] live 目录无演出记录，跳过")
        return

    rows = "\n        ".join(build_row(e) for e in entries)
    table_block = (
        f"{TABLE_START}\n"
        f"    <table>\n"
        f"        <tr><th>日期</th><th>城市</th><th>场馆</th><th>巡演主题</th><th>状态</th><th>详情</th></tr>\n"
        f"        {rows}\n"
        f"    </table>\n"
        f"    {TABLE_END}"
    )

    content = index_path.read_text(encoding="utf-8")
    if TABLE_START in content and TABLE_END in content:
        before, rest = content.split(TABLE_START, 1)
        _, after = rest.split(TABLE_END, 1)
        index_path.write_text(before + table_block + after, encoding="utf-8")
        return

    pattern = re.compile(
        r"(<h2>最新演出动态</h2>\s*<p>此板块实时更新.*?</p>\s*)<table>.*?</table>",
        re.S,
    )
    replacement = r"\1" + table_block
    new_content, count = pattern.subn(replacement, content, count=1)
    if count == 0:
        raise RuntimeError("未找到首页「最新演出动态」表格")
    index_path.write_text(new_content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="更新首页演出动态表格")
    parser.add_argument("--index", default="index.html")
    parser.add_argument("--live-dir", default="./live/")
    args = parser.parse_args()

    index_path = Path(args.index)
    if not index_path.is_absolute():
        index_path = ROOT / index_path
    live_dir = Path(args.live_dir)
    if not live_dir.is_absolute():
        live_dir = ROOT / live_dir

    if not index_path.exists():
        print(f"[X] 首页不存在: {index_path}")
        sys.exit(1)
    if not live_dir.exists():
        print(f"[X] live 目录不存在: {live_dir}")
        sys.exit(1)

    entries = load_manifest(live_dir)
    update_index(index_path, entries)
    print(f"[OK] 已更新 {len(entries)} 条演出记录 -> {index_path}")


if __name__ == "__main__":
    main()
