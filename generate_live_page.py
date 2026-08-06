#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 YAML 素材 → 渲染 live_template.html → 输出独立演出页面。"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
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
        tour_effect=config.get("tour_effect"),  # 数据效应区块（无数据为 None，模板留白）
    )


def _fmt_pct(v) -> str:
    if v is None:
        return ""
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%"


def _norm_name(name: str) -> str:
    """名称规范化（与数据层一致）：全半角统一 + 去空白，仅用于匹配，不改变展示名"""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(name)).strip())


def build_song_uplift(raw: dict | None) -> dict:
    """从该场次 tour_song_effects["songs"] 构建 归一名 → 涨幅 映射。

    仅收录歌单内（on_setlist=True）且有数据的曲目；歌单外辐射带动曲目
    不注入歌单表，保持「完整歌单」表格纯净（无数据显示 —）。
    """
    if not raw:
        return {}
    out = {}
    for s in raw.get("songs") or []:
        if not s.get("on_setlist"):
            continue
        n = _norm_name(s.get("name", ""))
        if n:
            out[n] = _fmt_pct(s.get("uplift"))
    return out


def inject_song_uplift(config: dict, raw: dict | None) -> None:
    """把该场逐曲涨幅写入 first_half/second_half 每首 song.uplift。

    组合曲目（如「女人花 + 水中花」）按 + 拆分匹配；匹配到歌单内曲目才显示，
    否则留空由模板渲染为 —。
    """
    uplift_map = build_song_uplift(raw)
    if not uplift_map:
        return
    for half in ("first_half", "second_half"):
        for song in config.get(half, []):
            parts = [p for p in _norm_name(song.get("title", "")).split("+") if p]
            matched = ""
            for p in parts:
                if p in uplift_map:
                    matched = uplift_map[p]
                    break
            song["uplift"] = matched


def check_setlist_gaps(config: dict, raw: dict | None) -> None:
    """一致性校验：长表标记 on_setlist=True 但 YAML 歌单缺失的曲目 → 输出警告。

    长表（王晰巡演歌单长表_单一事实源.xlsx）是歌单唯一事实源，YAML 为人工整理。
    若长表认为某曲在该场歌单内（数据层按「歌单内」口径统计），而 YAML 未收录，
    live 页「完整歌单」表将不显示该曲，与数据效应区块的归属口径不一致——打印警告
    便于人工核对「唱了哪首」与「涨了多少」是否对齐。仅警告，不修改任何输出。
    匹配规则与注入一致：全半角统一 + 去空白 + 组合曲目按 + 拆分；YAML 标题带
    括号注解（如「再见我的爱人（Goodbye My Love）」）时按包含关系匹配。
    """
    if not raw:
        return
    yaml_norms = set()
    for half in ("first_half", "second_half"):
        for song in config.get(half, []):
            for p in _norm_name(song.get("title", "")).split("+"):
                if p:
                    yaml_norms.add(p)
    missing = []
    for s in raw.get("songs") or []:
        if not s.get("on_setlist"):
            continue
        n = _norm_name(s.get("name", ""))
        if not n:
            continue
        parts = [p for p in n.split("+") if p]
        matched = any(p in yaml_norms for p in parts)
        if not matched:
            matched = any(n in yn or yn in n for yn in yaml_norms)
        if not matched:
            missing.append(s.get("name"))
    if missing:
        print(
            f"[!] 一致性警告：{config.get('meta', {}).get('date', '')} 场，"
            f"以下歌曲在长表中标记为「歌单内」但 YAML 歌单未收录"
            f"（数据层按歌单内统计，live 页歌单表将不显示）：{'、'.join(missing)}"
        )


def build_tour_effect(raw: dict | None) -> dict | None:
    """把数据层的场次后歌曲级效应转成模板可直接渲染的展示结构（动态数值，不写死）"""
    if not raw:
        return None
    total = raw.get("total_uplift")
    setlist = raw.get("setlist_uplift")
    radiance = raw.get("radiance_uplift")
    tops = [
        {
            "name": t["name"],
            "uplift": _fmt_pct(t.get("uplift")),
            "on_setlist": bool(t.get("on_setlist")),
        }
        for t in (raw.get("top_songs") or [])
    ]
    if total is None:
        return None
    note = f"演出后 7 日，全站指数较演出前（21~7 日）基线{_fmt_pct(total)}"
    if setlist is not None:
        note += f"；歌单内曲目平均{_fmt_pct(setlist)}"
    if radiance is not None:
        note += f"；歌单外作品平均{_fmt_pct(radiance)}，巡演的辐射带动同样带来积极影响"
    return {
        "date": raw.get("date"),
        "scene": raw.get("scene"),
        "city": raw.get("city"),
        "tour": raw.get("tour"),
        "total_text": _fmt_pct(total),
        "setlist_text": _fmt_pct(setlist) if setlist is not None else None,
        "radiance_text": _fmt_pct(radiance) if radiance is not None else None,
        "top_songs": tops,
        "note": note,
    }


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
    # 数据效应：从数据大屏 dashboard_data.json 匹配当前场次（按日期），无数据则留白不渲染
    from update_index_table import load_effects

    effect_raw = load_effects(ROOT / "dashboard").get(config["meta"]["date"])
    effect = build_tour_effect(effect_raw)
    if effect:
        config["tour_effect"] = effect
    # 逐曲场后涨幅：注入「完整歌单」表（仅歌单内且有数据的曲目显示，其余留白 —）
    inject_song_uplift(config, effect_raw)
    # 一致性校验：长表标记歌单内但 YAML 缺失的曲目 → 警告（长表为单一事实源）
    check_setlist_gaps(config, effect_raw)
    html = render_page(config, ROOT, args.template)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / config["meta"]["filename"]
    out_file.write_text(html, encoding="utf-8")
    write_manifest(output_dir, config)

    if not args.no_index:
        from update_index_table import load_effects, load_manifest, update_index

        entries = load_manifest(output_dir)
        update_index(index_path, entries, load_effects(ROOT / "dashboard"))

    if not args.no_sitemap:
        update_sitemap(sitemap_path, output_dir / "manifest.json")

    print(f"[OK] 已生成: {out_file}")
    if not args.no_index:
        print(f"[OK] 已更新首页表格 ({len(entries)} 条): {index_path}")
    if not args.no_sitemap:
        print(f"[OK] 已更新 sitemap: {sitemap_path}")


if __name__ == "__main__":
    main()
