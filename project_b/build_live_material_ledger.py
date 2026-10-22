# -*- coding: utf-8 -*-
"""build_live_material_ledger.py —— 现场素材台账（机器 + 人读 + 站内页）

数据源（全部现算，不手写数字）：
  · 候选池 `E:\wx\论文素材_王晰作传\音域分析\轨迹\轨迹素材库.json`（songs[].items[]）
  · 来源台账 `E:\wx\论文素材_王晰作传\音域分析\场次音频\来源台账.json`（items[]）
  · 现场层 `D:\wx409.github.io\data\archive_stage_tour.json`（rows[]，逐素材实测）
输出：
  · data/live_material_ledger.json（机器）
  · data/live_material_ledger.md（人读）
  · live-materials.html（站内页，可筛选；进 sitemap/底部索引，不进主导航）
风险/失败/跳过也落台账（不只记成功）。
"""
from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
POOL = Path(r"E:\wx\论文素材_王晰作传\音域分析\轨迹\轨迹素材库.json")
LEDGER = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频\来源台账.json")
STAGE = D / "archive_stage_tour.json"
OUT_JSON = D / "live_material_ledger.json"
OUT_MD = D / "live_material_ledger.md"
OUT_HTML = SITE / "live-materials.html"
SEARCH = D / "site_search_index.json"


def load(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d


def kind_of(title: str) -> str:
    t = str(title)
    if "4K" in t or "字幕" in t:
        return "4K字幕"
    if "串烧" in t or "组曲" in t or "合集" in t:
        return "串烧"
    if "剪辑" in t or "混剪" in t:
        return "剪辑"
    if "直拍" in t or "近景" in t:
        return "直拍"
    return "其他"


def main() -> int:
    pool = load(POOL, {}) or {}
    led = load(LEDGER, {}) or {}
    stage = load(STAGE, {}) or {}
    rows_out = stage.get("rows") or []

    # 现场层按 BV/标题索引
    by_bv = defaultdict(list)
    for r in rows_out:
        bv = re.search(r"(BV[0-9A-Za-z]{10})", str(r.get("bv") or r.get("tag") or ""))
        if bv:
            by_bv[bv.group(1)].append(r)
    led_by_bv = {}
    for it in led.get("items") or []:
        m = re.search(r"(BV[0-9A-Za-z]{10})", str(it.get("bv") or ""))
        if m:
            led_by_bv[m.group(1)] = it

    rows = []
    for song, v in (pool.get("songs") or {}).items():
        for it in (v.get("items") or []):
            bv = str(it.get("bv") or "")
            title = str(it.get("title") or "")
            st = by_bv.get(bv) or []
            l = led_by_bv.get(bv) or {}
            status = "已完成" if st else ("跳过-串烧需人工切分" if kind_of(title) == "串烧"
                                          else "候选")
            metrics = []
            if st:
                for k, lab in (("low_hz", "低音"), ("span_octaves", "跨度")):
                    if any(x.get(k) for x in st):
                        metrics.append(lab)
                if any(x.get("vibrato_rate_hz_median") for x in st):
                    metrics.append("颤音")
                if any(x.get("stability_cents_median") for x in st):
                    metrics.append("稳定性")
            rows.append({
                "bv": bv, "title": title, "song": song,
                "tour": (st[0].get("tour") if st else "") or "",
                "city": (st[0].get("city") if st else "") or "",
                "date": (st[0].get("date") if st else "") or str(it.get("pubdate") or "")[:10],
                "kind": kind_of(title), "fetched_at": str(it.get("pubdate") or "")[:10],
                "audio": bool(l), "separated": bool(st),
                "has_f0": bool(st), "metrics": metrics,
                "grade": ("实测" if st else "待复核" if l else "需人耳"),
                "status": status,
            })

    # 覆盖：候选按 (song) 计；已处理按 stage 行的 (song) 计
    cand_songs = {r["song"] for r in rows if r["song"]}
    done_songs = {r.get("song") for r in rows_out if r.get("song")}
    gaps = sorted(cand_songs - done_songs)
    doc = {
        "schema": 1, "generated_at": datetime.now().isoformat(timespec="seconds"),
        "as_of": max([r.get("date") or "" for r in rows_out] or [""]),
        "note": "候选来自轨迹素材池；已处理以现场层逐素材实测（archive_stage_tour）为准；失败/跳过同样落账",
        "summary": {"candidates": len(rows), "songs": len(cand_songs),
                    "processed_materials": len(rows_out), "processed_songs": len(done_songs),
                    "gap_songs": len(gaps),
                    "coverage_pct": round(100 * len(done_songs) / len(cand_songs), 1) if cand_songs else 0,
                    "status": dict(Counter(r["status"] for r in rows))},
        "gap_songs": gaps,
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    # 人读 md
    s = doc["summary"]
    md = [f"# 现场素材台账（as_of {doc['as_of']}）", "",
          f"- 候选素材 **{s['candidates']}** 条（{s['songs']} 首）",
          f"- 已处理素材 **{s['processed_materials']}** 条（{s['processed_songs']} 首）",
          f"- 缺口曲目 **{s['gap_songs']}** 首｜覆盖率 **{s['coverage_pct']}%**",
          f"- 状态分布：{json.dumps(s['status'], ensure_ascii=False)}", "",
          "| BV | 曲目 | 巡次 | 城市 | 日期 | 来源类型 | 指标 | 等级 | 状态 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows[:400]:
        md.append(f"| {r['bv']} | {r['song']} | {r['tour']} | {r['city']} | {r['date']} | "
                  f"{r['kind']} | {'/'.join(r['metrics']) or '—'} | {r['grade']} | {r['status']} |")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    # 站内页
    color = {"已完成": "#1f7a3d", "跳过-串烧需人工切分": "#b8860b", "候选": "#666", "失败": "#a8323d"}
    H = ["<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
         "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
         "<title>现场素材台账｜王晰数字档案</title>",
         "<meta name=\"description\" content=\"现场素材台账：候选、已处理、缺口与每类素材能产出的指标。\">",
         "<style>body{font:15px/1.7 -apple-system,Segoe UI,Microsoft YaHei,sans-serif;max-width:1100px;"
         "margin:24px auto;padding:0 16px;color:#222}table{border-collapse:collapse;width:100%;font-size:13px}"
         "th,td{border:1px solid #e6e6e6;padding:4px 6px;text-align:left}th{background:#faf7f7;position:sticky;top:0}"
         ".meta{color:#666;font-size:.9em}.b{display:inline-block;padding:1px 6px;border-radius:3px;color:#fff;font-size:12px}"
         "</style></head><body>", "<!-- NAV_START --><!-- NAV_END -->",
         "<h1>现场素材台账</h1>",
         f"<p class=\"meta\">候选 {s['candidates']}｜已处理素材 {s['processed_materials']}｜"
         f"缺口曲目 {s['gap_songs']}｜覆盖率 {s['coverage_pct']}%｜最近更新 {doc['as_of']}</p>",
         "<h2>每类素材能做到什么</h2><ul>",
         "<li>4K 字幕／直拍单曲 → 可测：低音读数、跨度、颤音、稳定性、长声（极值音归属未定）</li>",
         "<li>剪辑／混剪 → 仅作一致性旁证，不进主读数</li>",
         "<li>串烧／组曲 → 必须人工切分后才能测，当前跳过</li>",
         "<li>观众侧手机录像 → 可测形态，不作能力结论（除非过三指标门槛）</li></ul>",
         "<p class=\"meta\">说明：候选来自轨迹素材池；已处理以现场层逐素材实测为准；失败与跳过同样落账。</p>",
         "<p><label>巡次 <input id=\"f-tour\" placeholder=\"如 三巡\" size=\"8\"></label> "
         "<label>曲目 <input id=\"f-song\" placeholder=\"曲名\" size=\"10\"></label> "
         "<label>状态 <select id=\"f-status\"><option value=\"\">全部</option>"
         "<option>已完成</option><option>跳过-串烧需人工切分</option><option>候选</option></select></label></p>",
         "<table id=\"tbl\"><thead><tr><th>BV</th><th>曲目</th><th>巡次</th><th>城市</th><th>日期</th>"
         "<th>来源类型</th><th>指标</th><th>等级</th><th>状态</th></tr></thead><tbody>"]
    shown = ([r for r in rows if r["status"] != "候选"]
             + [r for r in rows if r["status"] == "候选"][:800])
    for r in shown:
        c = color.get(r["status"], "#666")
        H.append(f"<tr data-tour=\"{html.escape(r['tour'])}\" data-song=\"{html.escape(r['song'])}\" "
                 f"data-status=\"{html.escape(r['status'])}\"><td>{html.escape(r['bv'])}</td>"
                 f"<td>{html.escape(r['song'])}</td><td>{html.escape(r['tour'])}</td>"
                 f"<td>{html.escape(r['city'])}</td><td>{html.escape(r['date'])}</td>"
                 f"<td>{html.escape(r['kind'])}</td><td>{html.escape('/'.join(r['metrics']) or '—')}</td>"
                 f"<td>{html.escape(r['grade'])}</td>"
                 f"<td><span class=\"b\" style=\"background:{c}\">{html.escape(r['status'])}</span></td></tr>")
    H.append("</tbody></table>")
    H.append("<script>(function(){var t=document.getElementById('tbl');"
             "function f(){var tour=document.getElementById('f-tour').value.trim();"
             "var song=document.getElementById('f-song').value.trim();"
             "var st=document.getElementById('f-status').value;"
             "Array.prototype.forEach.call(t.tBodies[0].rows,function(r){"
             "r.style.display=(!tour||r.dataset.tour.indexOf(tour)>=0)&&(!song||r.dataset.song.indexOf(song)>=0)"
             "&&(!st||r.dataset.status===st)?'':'none'})}"
             "['f-tour','f-song','f-status'].forEach(function(i){document.getElementById(i).addEventListener('input',f)})})();</script>")
    H.append("<p class=\"meta\">数据：<code>data/live_material_ledger.json</code>｜"
             "生成：<code>project_b/build_live_material_ledger.py</code></p></body></html>")
    OUT_HTML.write_text("\n".join(H), encoding="utf-8")

    # 搜索索引：upsert 本页
    try:
        idx = load(SEARCH, []) or []
        idx = [x for x in idx if x.get("url") != "https://wx409.github.io/live-materials.html"]
        idx.append({"type": "page", "title": "现场素材台账",
                    "url": "https://wx409.github.io/live-materials.html",
                    "text": f"现场素材台账：候选 {s['candidates']}，已处理 {s['processed_materials']}，"
                            f"缺口 {s['gap_songs']}，覆盖率 {s['coverage_pct']}%",
                    "keywords": ["现场素材", "台账", "候选", "覆盖", "指标"]})
        SEARCH.write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")
        print("[OK] 搜索索引已 upsert")
    except Exception as e:
        print("[warn] 搜索索引更新失败:", e)

    print(f"[ok] {OUT_JSON.name}｜候选 {s['candidates']}｜已处理 {s['processed_materials']}｜"
          f"缺口 {s['gap_songs']}｜覆盖 {s['coverage_pct']}%")
    print(f"[ok] {OUT_MD.name}｜{OUT_HTML.name}（{OUT_HTML.stat().st_size} B）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
