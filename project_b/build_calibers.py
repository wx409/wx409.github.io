#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""口径登记表生成器：把全站所有「歌曲数 / 场次数 / 规模数」登记成一份机读+人读的清单。

为什么需要它（第一性原理）：
  第一性原理总检（2026-09-08）发现"歌曲数六种口径并存"（748/586/435/383/325/302/289…），
  但**它们多数不是错误，而是不同范围的定义**——真正的病是"没人知道哪个数是什么"。
  因此正确做法不是强行合并成一个数，而是给每个数**登记名称、范围、来源、口径**，
  并规定"任何地方引用数字必须同时给出 id"。

输出：
  - data/calibers.json   机读（供网站/AI 引用，Schema.org Dataset 可挂）
  - data/calibers.md     人读（供论文/传记/宣传引用）
  - 站点底部索引与 llms.txt 会链接它

用法：
  python project_b/build_calibers.py
  python project_b/build_calibers.py --check   # 只校验登记表与数据是否一致（退出码 1 = 漂移）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_SETLIST = r"E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx"


def _load(rel: str):
    p = ROOT / rel
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _count(obj, *keys):
    """从 dict 里按候选键取一个计数"""
    if isinstance(obj, dict):
        for k in keys:
            if k in obj:
                v = obj[k]
                if isinstance(v, (int, float)):
                    return int(v)
                if hasattr(v, "__len__"):
                    return len(v)
    if isinstance(obj, list):
        return len(obj)
    return None


def collect() -> list[dict]:
    """登记每一条口径：id / 名称 / 数值 / 范围 / 来源文件 / 说明"""
    out: list[dict] = []

    def add(cid, label, value, scope, source, note):
        out.append({"id": cid, "label": label, "value": value, "scope": scope,
                    "source": source, "note": note})

    dash = _load("dashboard/dashboard_data.json") or {}
    add("tracked_songs", "追踪曲目池", _count(dash, "total_songs"),
        "主动追踪并采集指数的曲目清单（池内）", "dashboard/dashboard_data.json",
        "站内绝大多数'热度'结论的样本范围；池逐年缩小，跨年比较须注意")
    add("tracked_links", "追踪链接数", _count(dash, "tracked_links"),
        "同一首歌的多个平台链接（一首歌可有多条链接）", "dashboard/dashboard_data.json",
        "与曲目数不同：链接是采集单位，曲目是分析单位")

    ei = _load("entity_index.json") or {}
    add("entity_songs", "关系图谱曲目", _count(ei, "song_count"),
        "至少有一条关系（现场/小酒馆/专辑）的曲目", "entity_index.json",
        "歌曲↔城市↔场馆↔逐字稿的聚合图谱节点数")

    sm = _load("data/songs_meta.json") or {}
    add("songs_meta", "歌曲元数据条目", _count(sm, "song_count"),
        "含元信息（时长/专辑/发行等）的曲目", "data/songs_meta.json", "")

    sa = _load("data/song_archive.json") or {}
    add("song_archive", "歌曲档案条目", _count(sa, "count"),
        "档案库收录的全部曲目条目（含未追踪/无指数）", "data/song_archive.json",
        "站内最大口径，用于'作品总量'类表述")

    cf = _load("data/credits_full.json") or {}
    add("credits_songs", "署名/演职信息曲目", _count(cf, "songs"),
        "有公开演职/署名记录的曲目", "data/credits_full.json", "")

    ps = _load("data/playable_songs.json") or {}
    add("playable_songs", "可试听曲目", _count(ps, "total"),
        "站内提供试听入口的曲目", "data/playable_songs.json", "")

    nc = _load("data/netease_catalog.json") or {}
    add("netease_songs", "网易云曲库曲目", _count(nc, "songs"),
        "网易云音乐侧可核验曲目", "data/netease_catalog.json", "另一平台口径，不与 QQ 音乐池混用")

    # 场次口径（长表派生）
    st = _load("data/setlists.json") or {}
    cj = _load("data/cities.json") or {}
    add("shows_all", "全站场次", _count(cj, "show_count"),
        "六轮巡演 + 签唱会等非巡演演出", "data/cities.json（长表派生）",
        "对外表述'全站'时用此数，必须同时给出 shows_tour")
    add("shows_setlists", "有歌单记录的场次", _count(st, "show_count"),
        "长表中至少有 1 条曲目记录的场次", "data/setlists.json", "与全站场次应一致")
    add("cities", "巡演城市数", _count(cj, "city_count"), "去重城市", "data/cities.json", "")

    # 现场曲目
    live_songs = 0
    if isinstance(ei, dict):
        live_songs = sum(1 for v in (ei.get("songs") or {}).values() if v.get("live"))
    add("live_songs", "有现场记录的曲目", live_songs,
        "至少在一个场次歌单中出现过的曲目", "entity_index.json", "")

    # 知识库 / 语义层
    kb = _load("data/kb/manifest.json") or {}
    add("kb_facts", "知识库事实条数", _count(kb, "facts"), "结构化事实", "data/kb/manifest.json", "")
    ent_n = None
    if isinstance(kb.get("entities_by_type"), dict):
        ent_n = sum(kb["entities_by_type"].values())
    if ent_n is None:
        ent_n = _count(_load("data/kb/entities.json") or {}, "entity_count")
    add("kb_entities", "知识库实体数", ent_n, "人/歌/专辑/演出/城市等实体", "data/kb/manifest.json", "")
    add("kb_relations", "知识库关系数", _count(kb, "relations"), "实体间关系", "data/kb/manifest.json", "")

    sem = _load("data/kb/semantic/manifest.json") or _load("semantic/manifest.json")
    if sem:
        add("semantic_docs", "语义索引文档数", _count(sem, "doc_count", "documents", "count"),
            "可语义检索的文档块", "data/kb/semantic/manifest.json", "")

    qa = _load("data/qa_bank.json")
    qa_n = None
    if isinstance(qa, dict):
        qa_n = _count(qa, "count") or (len(qa.get("items") or []) or None)
    elif isinstance(qa, list):
        qa_n = len(qa)
    add("qa_pairs", "问答对数量", qa_n, "可引用问答（GEO 资产）", "data/qa_bank.json", "")

    # 长表原始行（真值校验用）
    try:
        import pandas as pd
        df = pd.read_excel(DEFAULT_SETLIST, sheet_name="合并长表")
        df = df[df["曲目"].notna() & (df["曲目"].astype(str).str.strip() != "")].copy()
        df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
        shows = df.groupby(["日期", "场次", "巡次"]).size().reset_index(name="n")
        tour = shows["巡次"].astype(str).str.match(r"^(一巡|二巡|三巡|四巡|五巡|六巡)")
        add("shows_tour", "六轮巡演场次", int(tour.sum()),
            "一巡~六巡的巡演场次（不含签唱会）", "巡演歌单长表（单一事实源）",
            "与 shows_all 成对出现：全站 64 = 巡演 59 + 签唱会等 5")
        add("setlist_rows", "歌单曲目记录行", int(len(df)),
            "长表曲目行（含串烧拆分行前的原始记录）", "巡演歌单长表", "")
        add("setlist_songs_unique", "歌单唯一曲目（数据层归一名）",
            int(df["数据层归一名"].fillna(df["曲目"]).astype(str).str.strip().nunique()),
            "长表去重后的曲目名", "巡演歌单长表", "")
    except Exception as e:
        add("shows_tour", "六轮巡演场次", None, "长表不可读", str(e), "")

    # 指数数据覆盖天数（页面"已覆盖 N 天"的唯一事实源）
    #   口径：以**已发布的指数长表**（music_index_long.csv）的唯一日期数为准，
    #   因为站点图表读的就是它；原始库文件覆盖数（music_index_raw_coverage.json）
    #   会少算补充来源的 11 天（2026-07-26~08-05），两者差异已在备忘第三十八节记录。
    try:
        import csv as _csv
        import io as _io
        from pathlib import Path as _Path
        csv_p = _Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
        cov_p = _Path(r"E:\wx\wx_textmine_out\music_index_raw_coverage.json")
        dates: set[str] = set()
        if csv_p.exists():
            with _io.open(csv_p, encoding="utf-8-sig", newline="") as f:
                for row in _csv.DictReader(f):
                    v = (row.get("date") or row.get("日期") or "").strip()
                    if v:
                        dates.add(v[:10])
        raw_n = None
        if cov_p.exists():
            _c = json.loads(cov_p.read_text(encoding="utf-8"))
            raw_n = int(_c.get("span_days", 0)) - len(_c.get("missing_days") or [])
        if dates:
            note = (f"已发布长表唯一日期；{min(dates)} 至 {max(dates)}"
                    + (f"；原始库文件覆盖 {raw_n} 天（少算补充来源 11 天）" if raw_n else ""))
            add("index_days", "指数数据覆盖天数", len(dates),
                "站点图表所用指数长表的实际覆盖天数", "E:\\wx\\wx_textmine_out\\music_index_long.csv", note)
        elif raw_n:
            add("index_days", "指数数据覆盖天数", raw_n,
                "原始库文件覆盖天数（长表不可读时的回退）", "music_index_raw_coverage.json", "")
    except Exception as e:
        add("index_days", "指数数据覆盖天数", None, "数据源不可读", str(e), "")

    # 现场实测（轨迹工程）：按场次入台账的口径，**不并入录音室主口径**
    try:
        stage_p = Path(r"E:\wx\论文素材_王晰作传\音域分析\轨迹\让她降落_四版实测.json")
        if stage_p.exists():
            sd = json.loads(stage_p.read_text(encoding="utf-8"))
            rows = sd.get("rows") or []
            shows = {(r.get("city"), r.get("date")) for r in rows if r.get("date")}
            add("stage_measured_versions", "现场实测版本数", len(rows),
                "B站音轨人声分离后实测的现场演唱版本（一巡/二巡/六巡的同一首歌多场次）",
                "音域分析\\轨迹\\让她降落_四版实测.json",
                "口径纪律：现场实测按场次入台账，**不并入录音室主口径**；"
                "与 recording_studio_vocal_songs 不同范围，禁止相加或混用")
            add("stage_measured_shows", "现场实测场次数", len(shows),
                "上述现场版本覆盖的实际演出场次（同场多源只算一场）",
                "音域分析\\轨迹\\让她降落_四版实测.json",
                "同场多源仅作一致性互证，不计入场次")
    except Exception as e:
        add("stage_measured_versions", "现场实测版本数", None, "实测台账不可读", str(e), "")

    # 现场低音读数复核（2026-09-11 起：原始混音谐波列完整性 + 同场同刻多源一致）
    try:
        tour = _load("data/archive_stage_tour.json") or {}
        ts = tour.get("summary") or {}
        n_rev = ts.get("n_harmonic_reviewed")
        lo = ts.get("lowest") or {}
        if isinstance(n_rev, int):
            add("stage_low_reviewed", "巡演现场低音读数·谐波列复核通过条数", n_rev,
                "archive_stage_tour.json 中复核状态为「谐波列复核通过」的素材条数",
                "data\\archive_stage_tour.json",
                "判据：原始混音 1f0–8f0 谐波列完整性 + 同场同刻多源一致；"
                "工具 音域分析\\轨迹\\低音复核_谐波列.py（判定表与纪要留在该目录，不上站点）")
        if lo.get("hz"):
            add("stage_lowest_hz", "巡演现场最低稳定音（现行）", lo.get("hz"),
                "王晰主导巡演现场·过复核门槛的最低稳定音（Hz）",
                "data\\archive_stage_tour.json",
                f"出处：{lo.get('song')}｜{lo.get('city')} {lo.get('date')}｜复核 {lo.get('verify')}；"
                "与 recording_studio_vocal_songs 不同范围，禁止混用")
    except Exception as e:
        add("stage_low_reviewed", "巡演现场低音读数·谐波列复核通过条数", None, "巡演层数据不可读", str(e), "")

    return [x for x in out if x["value"] is not None]


def render_md(items: list[dict], generated_at: str) -> str:
    lines = [
        "# 口径登记表（单一事实源 · 数字字典）",
        "",
        f"> 生成时间：{generated_at}　｜　生成脚本：`project_b/build_calibers.py`（幂等，部署时自动重跑）",
        ">",
        "> **纪律**：任何页面/论文/宣传材料引用数字，必须同时给出本表 id 与范围。",
        "> 不同范围的数字**不是矛盾**，混用才是错误。场次数必须成对出现（全站 = 巡演 + 签唱会）。",
        "",
        "| id | 名称 | 数值 | 范围 | 来源 |",
        "|---|---|---|---|---|",
    ]
    for x in items:
        lines.append(f"| `{x['id']}` | {x['label']} | **{x['value']}** | {x['scope']} | `{x['source']}` |")
    lines += ["", "## 常见误用", "",
              "- ❌ 把 `song_archive`(748) 当作'追踪曲目'——追踪曲目是 `tracked_songs`(383)。",
              "- ❌ 把 `tracked_links`(383) 与 `tracked_songs` 混为一谈——前者是链接单位。",
              "- ❌ 用'60 场'或'65 场'描述巡演——正确是 `shows_tour`(59) 或 `shows_all`(64)。",
              "- ❌ 跨平台比曲目数（QQ 池 vs 网易云）——平台口径不同，不可相加或相减。",
              ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="口径登记表生成器")
    ap.add_argument("--check", action="store_true", help="只检查是否与已登记文件一致")
    args = ap.parse_args()

    items = collect()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    payload = {"generated_at": generated_at, "count": len(items), "calibers": items}
    md = render_md(items, generated_at)

    out_json = ROOT / "data" / "calibers.json"
    out_md = ROOT / "data" / "calibers.md"
    new_json = json.dumps(payload, ensure_ascii=False, indent=2)

    drift = []
    if out_json.exists():
        old = json.loads(out_json.read_text(encoding="utf-8"))
        old_map = {x["id"]: x["value"] for x in old.get("calibers", [])}
        new_map = {x["id"]: x["value"] for x in items}
        for k in sorted(set(old_map) | set(new_map)):
            if old_map.get(k) != new_map.get(k):
                drift.append(f"{k}: {old_map.get(k)} -> {new_map.get(k)}")

    print("=" * 68)
    print("口径登记表（build_calibers.py）")
    print("=" * 68)
    for x in items:
        print(f"  {x['id']:22s} {str(x['value']):>7s}  {x['label']}")
    if drift:
        print("\n与上次登记相比的变化：")
        for d in drift:
            print("  -", d)

    if args.check:
        if drift:
            sys.exit(1)
        print("\n登记表与数据一致 ✅")
        return

    out_json.write_text(new_json, encoding="utf-8")
    out_md.write_text(md, encoding="utf-8")
    print(f"\n[OK] {out_json.relative_to(ROOT)}｜{out_md.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
