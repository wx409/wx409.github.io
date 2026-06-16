#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 YAML 素材 → 渲染 live_template.html → 输出独立演出页面。"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parent
SITE_BASE = "https://wx409.github.io"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


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


def _ns_tag(name: str) -> str:
    return f"{{{SITEMAP_NS}}}{name}"


def _read_sitemap_urls(sitemap_path: Path) -> list[dict[str, str]]:
    if not sitemap_path.exists():
        return []
    root = ET.parse(sitemap_path).getroot()
    urls: list[dict[str, str]] = []
    for url_el in root.findall(_ns_tag("url")):
        loc_el = url_el.find(_ns_tag("loc"))
        if loc_el is None or not loc_el.text:
            continue
        loc = loc_el.text.strip()
        if f"{SITE_BASE}/live/" in loc:
            continue
        entry = {"loc": loc}
        for field in ("lastmod", "changefreq", "priority"):
            node = url_el.find(_ns_tag(field))
            if node is not None and node.text:
                entry[field] = node.text.strip()
        urls.append(entry)
    return urls


def _render_sitemap(static_urls: list[dict[str, str]], live_urls: list[dict[str, str]]) -> str:
    ordered: list[dict[str, str]] = []
    pending_live = list(live_urls)
    for item in static_urls:
        ordered.append(item)
        if item["loc"].rstrip("/").endswith("/culture"):
            ordered.extend(pending_live)
            pending_live = []
    ordered.extend(pending_live)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<urlset xmlns="{SITEMAP_NS}">',
    ]
    for item in ordered:
        lines.append("  <url>")
        lines.append(f"    <loc>{item['loc']}</loc>")
        lines.append(f"    <lastmod>{item['lastmod']}</lastmod>")
        lines.append(f"    <changefreq>{item['changefreq']}</changefreq>")
        lines.append(f"    <priority>{item['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def update_sitemap(sitemap_path: Path, manifest_path: Path) -> None:
    if not manifest_path.exists():
        print(f"[!] manifest 不存在，跳过 sitemap: {manifest_path}")
        return

    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    lastmod = date.today().isoformat()
    live_urls = [
        {
            "loc": f"{SITE_BASE}/{entry['link'].lstrip('/')}",
            "lastmod": lastmod,
            "changefreq": "monthly",
            "priority": "0.9",
        }
        for entry in sorted(entries, key=lambda x: x["date"], reverse=True)
    ]
    static_urls = _read_sitemap_urls(sitemap_path)
    sitemap_path.write_text(_render_sitemap(static_urls, live_urls), encoding="utf-8")


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
    parser.add_argument("--sitemap", default="sitemap.xml", help="sitemap 路径")
    parser.add_argument("--no-sitemap", action="store_true", help="不更新 sitemap.xml")
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
    sitemap_path = Path(args.sitemap)
    if not sitemap_path.is_absolute():
        sitemap_path = ROOT / sitemap_path
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
        from update_index_table import load_manifest, update_index

        entries = load_manifest(output_dir)
        update_index(index_path, entries)

    if not args.no_sitemap:
        update_sitemap(sitemap_path, output_dir / "manifest.json")

    print(f"[OK] 已生成: {out_file}")
    if not args.no_index:
        print(f"[OK] 已更新首页表格 ({len(entries)} 条): {index_path}")
    if not args.no_sitemap:
        print(f"[OK] 已更新 sitemap: {sitemap_path}")


if __name__ == "__main__":
    main()
