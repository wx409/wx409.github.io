#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 YAML 素材 → 渲染 live_template.html → 输出独立演出页面。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parent
TABLE_START = "<!-- LIVE_TABLE_START -->"
TABLE_END = "<!-- LIVE_TABLE_END -->"


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_faq_schema(faq: list[dict]) -> str:
    entities = []
    for item in faq:
        entities.append(
            {
                "@type": "Question",
                "name": item["question"],
                "acceptedAnswer": {"@type": "Answer", "text": item["answer"]},
            }
        )
    return json.dumps(
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": entities},
        ensure_ascii=False,
        indent=2,
    )


def render_page(config: dict, template_dir: Path, template_name: str) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_name)
    faq = config.get("faq", [])
    return template.render(
        meta=config["meta"],
        first_half=config.get("first_half", []),
        second_half=config.get("second_half", []),
        highlights=config.get("highlights", []),
        perspectives=config.get("perspectives", []),
        repo_excerpts=config.get("repo_excerpts", []),
        faq=faq,
        quotes=config.get("quotes", []),
        faq_schema_json=build_faq_schema(faq),
    )


def build_table_row(config: dict) -> str:
    meta = config["meta"]
    index_row = config.get("index_row", {})
    link = index_row.get("link", f"live/{meta['filename']}")
    link_text = index_row.get("link_text", "完整实录 →")
    status_class = meta.get("status_class", "")
    status_td = (
        f'<td class="{status_class}">{meta["status"]}</td>'
        if status_class
        else f"<td>{meta['status']}</td>"
    )
    return (
        f"<tr>"
        f"<td>{meta['date_display']}</td>"
        f"<td>{meta['city']}</td>"
        f"<td>{meta['venue']}</td>"
        f"<td>{meta['tour_display']}</td>"
        f"{status_td}"
        f'<td><a href="{link}">{link_text}</a></td>'
        f"</tr>"
    )


def update_index_table(index_path: Path, config: dict) -> None:
    content = index_path.read_text(encoding="utf-8")
    row = build_table_row(config)

    if TABLE_START in content and TABLE_END in content:
        before, rest = content.split(TABLE_START, 1)
        _, after = rest.split(TABLE_END, 1)
        table_block = (
            f"{TABLE_START}\n"
            f"    <table>\n"
            f"        <tr><th>日期</th><th>城市</th><th>场馆</th><th>巡演主题</th><th>状态</th><th>详情</th></tr>\n"
            f"        {row}\n"
            f"    </table>\n"
            f"    {TABLE_END}"
        )
        index_path.write_text(before + table_block + after, encoding="utf-8")
        return

    pattern = re.compile(
        r"(<h2>最新演出动态</h2>\s*<p>此板块实时更新.*?</p>\s*)<table>.*?</table>",
        re.S,
    )
    replacement = (
        r"\1" + TABLE_START + "\n"
        "    <table>\n"
        "        <tr><th>日期</th><th>城市</th><th>场馆</th><th>巡演主题</th><th>状态</th><th>详情</th></tr>\n"
        f"        {row}\n"
        "    </table>\n"
        f"    {TABLE_END}"
    )
    new_content, count = pattern.subn(replacement, content, count=1)
    if count == 0:
        raise RuntimeError("未找到首页「最新演出动态」表格，请检查 index.html")
    index_path.write_text(new_content, encoding="utf-8")


def write_manifest(output_dir: Path, config: dict) -> None:
    manifest_path = output_dir / "manifest.json"
    entries = []
    if manifest_path.exists():
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    meta = config["meta"]
    entry = {
        "date": meta["date"],
        "date_display": meta["date_display"],
        "city": meta["city"],
        "venue": meta["venue"],
        "tour_display": meta["tour_display"],
        "status": meta["status"],
        "status_class": meta.get("status_class", ""),
        "filename": meta["filename"],
        "link": config.get("index_row", {}).get("link", f"live/{meta['filename']}"),
        "link_text": config.get("index_row", {}).get("link_text", "完整实录 →"),
    }
    entries = [e for e in entries if e.get("filename") != meta["filename"]]
    entries.append(entry)
    entries.sort(key=lambda x: x["date"], reverse=True)
    manifest_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="生成演出独立页面")
    parser.add_argument("--config", required=True, help="YAML 配置文件")
    parser.add_argument("--output", default="./live/", help="输出目录")
    parser.add_argument("--template", default="live_template.html", help="Jinja2 模板")
    parser.add_argument("--index", default="index.html", help="首页路径")
    parser.add_argument("--no-index", action="store_true", help="不更新首页表格")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    index_path = Path(args.index)
    if not index_path.is_absolute():
        index_path = ROOT / index_path
    template_path = ROOT / args.template

    if not config_path.exists():
        print(f"[X] 配置文件不存在: {config_path}")
        sys.exit(1)
    if not template_path.exists():
        print(f"[X] 模板不存在: {template_path}")
        sys.exit(1)

    config = load_config(config_path)
    html = render_page(config, ROOT, args.template)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / config["meta"]["filename"]
    out_file.write_text(html, encoding="utf-8")
    write_manifest(output_dir, config)

    if not args.no_index:
        update_index_table(index_path, config)

    print(f"[OK] 已生成: {out_file}")
    if not args.no_index:
        print(f"[OK] 已更新首页表格: {index_path}")


if __name__ == "__main__":
    main()
