# -*- coding: utf-8 -*-
"""横向素材积攒看板 —— 声学层之外，其余素材流是否在**同步**增长？

第一性原理（用户 2026-09-24）：传记不能只有声学一条腿。本工具回答三个问题：
  ① 每条素材流现在有多少；② 最近在不在长（近 7 日新增）；③ 新鲜度是否掉队（距今天数）＋缺口。

产出：
  · data/asset_streams.json（机读，**不含本地绝对路径**）
  · E:\\wx\\论文素材_王晰作传\\横向素材积攒看板.md（本地人读）

用法：python -X utf8 project_b\\build_asset_streams.py
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
E = Path(r"E:\wx")
CORPUS = E / "wx_textmine_corpus"
OUT_JSON = D / "asset_streams.json"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\横向素材积攒看板.md")
NOW = datetime.now()
WEEK = NOW - timedelta(days=7)


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


S = []


def add(stream, source, n, latest=None, gap="", note="", new7=None):
    lag = None
    if isinstance(latest, datetime):
        lag = (NOW - latest).days
    S.append({"stream": stream, "source": source, "n": n,
              "latest": latest.strftime("%Y-%m-%d") if isinstance(latest, datetime) else (latest or ""),
              "lag_days": lag, "new_7d": new7, "gap": gap, "note": note})


def dir_stat(d: Path):
    """(文件数, 最新 mtime, 近7日新增数)"""
    if not d.exists():
        return 0, None, 0
    n = new = 0
    latest = None
    for p in d.rglob("*"):
        if p.is_file():
            n += 1
            m = p.stat().st_mtime
            if latest is None or m > latest:
                latest = m
            if m >= WEEK.timestamp():
                new += 1
    return n, datetime.fromtimestamp(latest) if latest else None, new


# ── 声学（本线基准）──────────────────────────────────────────────
t = load(D / "archive_stage_tour.json").get("summary", {})
add("声学·现场层", "data/archive_stage_tour.json", t.get("n_materials"), NOW, "在积攒（每晚 22:00 增量）")
aa = load(D / "audio_assets.json").get("summary", {})
add("声学·音频资产", "data/audio_assets.json", aa.get("files"), NOW, "在积攒", f"本日新增 {aa.get('new_files')} 个",
    aa.get("new_files"))

# ── 指数 ────────────────────────────────────────────────────────
csvp = E / "wx_textmine_out" / "music_index_long.csv"
if csvp.exists():
    import pandas as pd
    df = pd.read_csv(csvp, dtype=str)
    u = sorted(df["date"].dropna().unique())
    latest = datetime.strptime(u[-1], "%Y-%m-%d")
    new7 = sum(1 for x in u if x >= WEEK.strftime("%Y-%m-%d"))
    add("指数·每日指数", "music_index_long.csv", len(u), latest,
        "在积攒（每日多批次）", f"最新 {u[-1]}", new7)

# ── 文本语料（六个来源目录）──────────────────────────────────────
if CORPUS.exists():
    for d in sorted(CORPUS.iterdir()):
        if d.is_dir():
            n, latest, new = dir_stat(d)
            add(f"文本·{d.name}", f"wx_textmine_corpus/{d.name}", n, latest,
                "在积攒" if new else "**近期无新增**", "", new)

# ── 演出记录 ────────────────────────────────────────────────────
sl = load(D / "setlists.json").get("setlists", {})
sp = D / "setlists.json"
add("演出·场次歌单", "data/setlists.json", len(sl),
    datetime.fromtimestamp(sp.stat().st_mtime) if sp.exists() else None, "人工维护", "全站 64 场")

# ── 知识库 ──────────────────────────────────────────────────────
mf_p = D / "kb" / "manifest.json"
mf = load(mf_p)
ent = sum((mf.get("entities_by_type") or {}).values())
add("知识库·实体", "data/kb/manifest.json", ent,
    datetime.fromtimestamp(mf_p.stat().st_mtime) if mf_p.exists() else None, "随内容更新",
    f"事实 {mf.get('facts')}｜关系 {mf.get('relations')}｜语声集 {mf.get('entities_by_type', {}).get('voice_episode')}")
qb = load(D / "qa_bank.json")
add("知识库·问答库", "data/qa_bank.json", len(qb.get("items") or []),
    datetime.fromtimestamp((D / "qa_bank.json").stat().st_mtime) if (D / "qa_bank.json").exists() else None,
    "随页面更新")

# ── 影像 ────────────────────────────────────────────────────────
vs = load(D / "video_shows.json").get("stat", {})
add("影像·本地视频", "data/video_shows.json", vs.get("video_files_scanned"), NOW,
    "在积攒（G 盘归档；仅 1 批已抽轨入库）", f"有视频场次 {vs.get('shows_with_video')}｜体积 {vs.get('video_gb')} GB")

# ── 采访 / 杂志（缺口）──────────────────────────────────────────
mg = [p for p in E.rglob("*") if p.is_file() and any(k in p.name for k in ("采访", "杂志", "报道"))]
add("文本·采访/杂志/报道", "散落于 E:\\wx", len(mg), None, "**缺口：未建索引**",
    "AGENTS.md 第三批待办")

out = {"generated_at": NOW.strftime("%Y-%m-%d %H:%M"), "streams": S,
       "summary": {
           "streams": len(S),
           "accumulating": sum(1 for x in S if x["new_7d"]),
           "stale": [x["stream"] for x in S if x["lag_days"] is not None and x["lag_days"] > 7],
           "gaps": [x["stream"] for x in S if "缺口" in x["gap"]],
       }}
OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

md = [f"# 横向素材积攒看板（{out['generated_at']}）", "",
      f"共 **{len(S)}** 条素材流｜近 7 日有新增 **{out['summary']['accumulating']}** 条｜"
      f"超过 7 天未更新 **{len(out['summary']['stale'])}** 条｜标注缺口 **{len(out['summary']['gaps'])}** 条", "",
      "| 素材流 | 条目数 | 近7日新增 | 最新 | 距今天数 | 状态/缺口 | 数据源 |",
      "|---|---|---|---|---|---|---|"]
for x in S:
    md.append(f"| {x['stream']} | {x['n']} | {x['new_7d'] if x['new_7d'] is not None else '—'} | {x['latest'] or '—'} | "
              f"{x['lag_days'] if x['lag_days'] is not None else '—'} | {x['gap']} | `{x['source']}` |")
OUT_MD.write_text("\n".join(md), encoding="utf-8")

for x in S:
    print(f"  {x['stream']:<20} n={str(x['n']):<6} 近7日={str(x['new_7d'] if x['new_7d'] is not None else '—'):<4} "
          f"最新={x['latest'] or '—':<11} 滞后={x['lag_days'] if x['lag_days'] is not None else '—':<4} {x['gap']}")
print(f"\n近 7 日有新增：{out['summary']['accumulating']}/{len(S)}｜缺口：{out['summary']['gaps']}")
print(f"→ {OUT_JSON}\n→ {OUT_MD}")
