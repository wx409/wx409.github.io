# -*- coding: utf-8 -*-
"""事实登记表生成器（与 calibers.json 并列的第二张"字典"）。

为什么需要它：同一类事实错误已经犯过多次——
  · 专辑发行年份（v2 指令、综合评估报告两次写错/被质疑）
  · 求学履历（早已核实仍被重新挂「待核」）
  · 赛事/机构归属细节
本表把这类**反复出错的事实字段**登记为机读字典：正确值 + 出处 + 核实日期 + **已知错误写法**，
配套 `check_facts_preflight.py` 在文稿/报告/指令生成前强制过一遍。

数据来源优先级（自动派生部分）：
  1. `data/albums.json` 的 release
  2. 站点搜索索引/大屏里各曲 release（取该专辑最早与最晚）
人工核实部分（curated）来源见每条 source。

用法：python -X utf8 project_b/build_facts.py
输出：data/facts_registry.json、data/facts_registry.md
"""
from __future__ import annotations

import argparse
import io
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALBUMS = ROOT / "data" / "albums.json"
SEARCH_IDX = ROOT / "data" / "site_search_index.json"
DASH = ROOT / "dashboard" / "dashboard_data.json"
OUT_JSON = ROOT / "data" / "facts_registry.json"
OUT_MD = ROOT / "data" / "facts_registry.md"

# ── 人工核实的事实（每条必须带 source 与 checked 日期）────────────────
CURATED = [
    {
        "id": "education", "label": "求学履历",
        "value": "2004 年考入辽宁艺术职业学院（流行演唱专业）→ 2014 年毕业于沈阳音乐学院",
        "source": "档案卡\\核实记录_求学履历_20260909.md（两家媒体 + 百科三源一致）；已写入 index.html 与论文初稿 1.1 节",
        "checked": "2026-09-09",
        "wrong": ["仅写「沈阳音乐学院毕业」而不提辽宁艺术职业学院",
                  "仅写「辽宁艺术职业学院」而不提沈阳音乐学院",
                  "把两校写成同一时期就读"],
    },
    {
        "id": "institution_line", "label": "机构归属时间线",
        "value": "海政文工团（2011→2018-09 撤编）→ 乐华娱乐（2019-04-09→2024）→ 中国东方演艺集团（2025→今）",
        "source": "kb_digest.md 里程碑（含 2018-09 国防部撤编、2019-04-09 生日官宣签约）",
        "checked": "2026-09-10",
        "wrong": ["写「2018 年仍在海政文工团在职演出」而不注明撤编",
                  "把乐华签约定在 2018 年"],
    },
    {
        "id": "awards", "label": "赛事与奖项",
        "value": "2011 第八届中国音乐金钟奖男子组金奖；2013 第十五届 CCTV 青年歌手电视大奖赛流行唱法总冠军；2016《我是歌手》第四季踢馆夺冠",
        "source": "百度百科 + 新华网 2016-02-20（《我是歌手》逆袭的低音炮）",
        "checked": "2026-09-10",
        "wrong": ["把「踢馆夺冠」写成「补位夺冠」",
                  "把金钟奖写成「金奖第一名（终身）」等加码说法"],
    },
    {
        "id": "interval_semitone_rule", "label": "音程换算（自测纪律）",
        "value": "F#2(midi 42) → B1(midi 35) = 7 个半音；B1(约 61.7Hz) 比 Low C(C2 65.4Hz) 低 1 个半音",
        "source": "本项目实测（numeral 由 midi 差值计算，禁用「感觉像五个半音」类估计）",
        "checked": "2026-09-10",
        "wrong": ["F#2 到 B1 说成五个半音", "B1 比 Low C 说成低两个半音"],
    },
    {
        "id": "index_cutoff", "label": "指数数据截止日",
        "value": "本年度（2026）指数数据截至 2026-09-08；年度值：2023=1011.5 / 2024=881.1 / 2025=861.5 / 2026=685.6",
        "source": "data/archive_baseline.json（compute_baseline_v1.py 追踪池日均口径）",
        "checked": "2026-09-10",
        "wrong": ["引用年度指数时不注明截止日期", "沿用 1013/880/862/686 旧值（千分位缺陷版）"],
    },
    {
        "id": "moscow_2025", "label": "2025 莫斯科相关",
        "value": "2025-09-17 赴莫斯科格涅辛音乐学院参加中国流行音乐艺术交流；2025-09-20 代表中国参加「国际视界」国际音乐大赛（23 国参赛）",
        "source": "新华社/中新网报道（见 kb_digest.md 里程碑）；具体名次未在本地核实 → 不写名次",
        "checked": "2026-09-10",
        "wrong": ["写「获得冠军/亚军」等名次（本地无核实）"],
    },
    {
        "id": "medal_2013", "label": "2013 随海军赴俄联演",
        "value": "2013 年随中国海军赴俄罗斯参加中俄海上联演，荣立个人三等功",
        "source": "kb_digest.md 里程碑（履历条目）；论文初稿沿用",
        "checked": "2026-09-10",
        "wrong": ["写成「二等功」或「集体三等功」"],
    },
]


def album_dates() -> list[dict]:
    """专辑发行：albums.json 的 release + 索引里各曲 release 的最早/最晚。"""
    out = []
    alb = json.load(io.open(ALBUMS, encoding="utf-8"))
    rel_map: dict[str, str] = {}
    try:
        idx = json.load(io.open(SEARCH_IDX, encoding="utf-8"))

        def walk(o):
            if isinstance(o, dict):
                if o.get("name") and o.get("release"):
                    yield o
                for v in o.values():
                    yield from walk(v)
            elif isinstance(o, list):
                for v in o:
                    yield from walk(v)

        for r in walk(idx):
            nm = str(r.get("name")).split("\n")[0].strip()
            if re.match(r"^\d{4}-\d{2}", str(r.get("release") or "")):
                rel_map.setdefault(nm, r["release"][:10])
    except Exception:
        pass
    for a in alb.get("albums", []):
        titles = [s.get("title") for s in (a.get("songs") or [])]
        dates = sorted(d for d in (rel_map.get(t) for t in titles) if d)
        out.append({
            "key": a["name"],
            "value": (a.get("release") or "待补"),
            "earliest_track": dates[0] if dates else None,
            "latest_track": dates[-1] if dates else None,
            "tracks": len(titles),
            "source": "data/albums.json（release）+ data/site_search_index.json（逐曲 release）",
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="事实登记表生成器")
    ap.add_argument("--check", action="store_true", help="只读校验：与既有登记表比对差异")
    args = ap.parse_args()

    albums = album_dates()
    facts = CURATED + [{
        "id": "album_release", "label": "专辑发行年（逐张）",
        "value": "；".join(f'《{a["key"]}》{a["value"]}'
                          + (f'（首曲 {a["earliest_track"]}）' if a.get("earliest_track") else "")
                          for a in albums),
        "source": "data/albums.json + data/site_search_index.json（自动派生）",
        "checked": datetime.now().strftime("%Y-%m-%d"),
        # 已知错误写法：2026-09-10 一次报告/指令核对中出现的错位（把三张专辑相互错配）
        "wrong": ["《X自选集》2021", "《不说》2022", "《回望》2024",
                  "回望是 2024 年唯一发行"],
        "items": albums,
    }]

    payload = {
        "schema": 1,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": ("反复出错的事实字段登记表（与 calibers.json 并列）。生成文稿/报告/指令前"
                 "先跑 project_b/check_facts_preflight.py。每条含 value/source/checked/wrong。"),
        "facts": facts,
    }
    if args.check and OUT_JSON.exists():
        old = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        old_map = {f["id"]: f.get("value") for f in old.get("facts", [])}
        new_map = {f["id"]: f.get("value") for f in facts}
        diff = [k for k in set(old_map) | set(new_map) if old_map.get(k) != new_map.get(k)]
        print(f"比对：{len(facts)} 条事实，{len(diff)} 条有变化")
        for k in diff:
            print(f"  - {k}: {str(old_map.get(k))[:60]} → {str(new_map.get(k))[:60]}")
        return 0

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    md = ["# 事实登记表（反复出错的事实字段 · 数字字典第二张）", "",
          f"> 生成：{payload['generated_at']}｜与 `data/calibers.json`（口径字典）并列",
          "> 用法：写文稿/报告/指令前跑 `python -X utf8 project_b/check_facts_preflight.py <文件…>`", ""]
    for f in facts:
        md += [f"## {f['label']}（`{f['id']}`）", "", f"- **正确值**：{f['value']}",
               f"- **出处**：{f['source']}", f"- **核实日期**：{f['checked']}"]
        if f.get("wrong"):
            md.append("- **已知错误写法**：" + "；".join(f["wrong"]))
        if f.get("items"):
            md += ["", "| 专辑 | release | 首曲发行 | 尾曲发行 | 曲数 |", "|---|---|---|---|---|"]
            for a in f["items"]:
                md.append(f"| {a['key']} | {a['value']} | {a.get('earliest_track') or '—'} | "
                          f"{a.get('latest_track') or '—'} | {a['tracks']} |")
        md.append("")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[OK] {OUT_JSON}｜{OUT_MD}｜事实 {len(facts)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
