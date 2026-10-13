# -*- coding: utf-8 -*-
"""传记素材映射 → docs/传记素材映射_<日期>.md（只做映射与缺口清单，不写正文）。

数字全部从 data/ 派生；词条部分直接取 data/share/entries.json 的 bio 字段（同源，不重复维护）。
用法：python -X utf8 project_b\\build_bio_mapping.py [--date 20261013]
"""
from __future__ import annotations
import json
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
DOCS = SITE / "docs"


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def n_of(p, *keys, default=None):
    o = load(p)
    if o is None:
        return default
    if isinstance(o, list):
        return len(o)
    for k in keys:
        if isinstance(o, dict) and k in o:
            v = o[k]
            return len(v) if isinstance(v, (list, dict)) else v
    return default


def main() -> int:
    day = "20261013"
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            day = sys.argv[i + 1]
    entries = (load(D / "share" / "entries.json", {}) or {}).get("entries") or []
    cal = {c["id"]: c for c in (load(D / "calibers.json", {}) or {}).get("calibers", [])}
    spread = load(D / "share" / "woyaoni_spread.json", {}) or {}
    cn = ((load(D / "archive_cross_night.json", {}) or {}).get("versions") or {})

    assets = [
        ("声学·录音室全量", "data/archive_vocal_albums.json",
         n_of(D / "archive_vocal_albums.json", "songs", default="—"), "曲"),
        ("声学·跨素材精测层", "data/archive_vocal.json",
         n_of(D / "archive_vocal.json", "songs", default="—"), "曲"),
        ("声学·现场层（王晰主导）", "data/archive_stage_tour.json",
         n_of(D / "archive_stage_tour.json", "rows", default="—"), "条素材"),
        ("声学·长声实测", "data/archive_long_notes.json",
         n_of(D / "archive_long_notes.json", "top", default="—"), "条（保留榜）"),
        ("声学·跨夜一致性", "data/archive_cross_night.json",
         len(cn), "组对照"),
        ("声学·动态范围", "data/archive_dynamic_range.json",
         n_of(D / "archive_dynamic_range.json", "classes", default="—"), "音级"),
        ("传播·小红书同场样本", "data/share/woyaoni_spread.json",
         spread.get("notes", "—"), "条笔记"),
        ("传播·评论语料", "data/share/woyaoni_spread.json",
         spread.get("comments_grabbed", "—"), "条评论"),
        ("传播·词条库", "data/share/entries.json", len(entries), "条"),
        ("传播·监测配置", "data/propagation_watch.json",
         len(((load(D / "propagation_watch.json", {}) or {}).get("keywords") or {})), "组关键词"),
        ("指数·覆盖天数", "data/calibers.json",
         (cal.get("index_days") or {}).get("value", "—"), "天"),
    ]

    LINES = {
        "能力-市场": "能力-市场线：唱得好，市场看见了吗？",
        "市场-情绪": "市场-情绪线：他如何面对被看见/不被看见",
        "情绪-能力": "情绪-能力线：状态如何影响声音",
    }
    by_line = {}
    for e in entries:
        by_line.setdefault((e.get("bio") or {}).get("line", "未标注"), []).append(e)

    out = [f"# 传记素材映射（{day}）", "",
           "> 只做**映射与缺口清单**，不写正文。数字由 `project_b/build_bio_mapping.py` 从 `data/` 派生；",
           "> 词条部分与 `data/share/entries.json` 同源（不重复维护）。", "",
           "## 一、三条主线", ""]
    for k, v in LINES.items():
        out.append(f"- **{k}**：{v}")
    out += ["", "## 二、词条 → 主线映射（%d 条）" % len(entries), "",
            "| # | 词条钩子 | 证据等级 | 主线 | 可写进哪一章 | 证据 ID | 还缺什么 |",
            "|---|---|---|---|---|---|---|"]
    for e in sorted(entries, key=lambda x: x.get("no", 0)):
        b = e.get("bio") or {}
        out.append("| %s | %s | %s | %s | %s | `%s` | %s |" % (
            e.get("no"), e.get("hook"), e.get("grade"), b.get("line"),
            b.get("chapter"), b.get("evidence_id"), b.get("gap")))
    out += ["", "## 三、已有资产 → 主线（可作章节骨架）", "",
            "| 资产 | 数据源 | 量 | 主用主线 | 用法 |", "|---|---|---|---|---|"]
    use = {
        "声学·录音室全量": ("能力-市场", "能力边界的底座：最低稳定音/跨度/颤音指纹"),
        "声学·跨素材精测层": ("能力-市场", "极值集与对照集：哪些能力主张可对外引用"),
        "声学·现场层（王晰主导）": ("能力-市场", "能力是否在现场成立（现场 vs 录音室）"),
        "声学·长声实测": ("能力-市场", "长音/气息控制的具体读数"),
        "声学·跨夜一致性": ("情绪-能力", "同一首歌在不同夜晚的稳定性（n 小，只作个案）"),
        "声学·动态范围": ("能力-市场", "强弱控制（音级受限，注明覆盖范围）"),
        "传播·小红书同场样本": ("市场-情绪", "一次自燃的完整样本：时间结构 + 互动量级"),
        "传播·评论语料": ("市场-情绪", "观众到底在谈什么（维度/触发点计数）"),
        "传播·词条库": ("市场-情绪", "可传播钩子与其禁忌写法"),
        "传播·监测配置": ("市场-情绪", "后续每次演出的可比观测口径"),
        "指数·覆盖天数": ("能力-市场", "市场端的长期曲线口径"),
    }
    for name, src, val, unit in assets:
        ln, how = use.get(name, ("—", "—"))
        out.append(f"| {name} | `{src}` | {val} {unit} | {ln} | {how} |")
    out += ["", "## 四、缺口清单（按主线）", ""]
    for k in LINES:
        gaps = [((e.get("bio") or {}).get("gap") or "") for e in by_line.get(k, [])]
        out.append(f"**{k}**")
        for g in gaps:
            if g:
                out.append(f"- {g}")
        if k == "能力-市场":
            out += ["- 缺同曲「现场 vs 录音室」的稳定音级对照（现有为触达音级）",
                    "- 缺动态范围/气声/弱混的量化读数（现仅覆盖部分音级）"]
        if k == "市场-情绪":
            out += ["- 缺平台侧曝光/推荐数据（不得据本站样本断言平台热度）",
                    "- 缺跨场次/跨城市的同口径维度统计",
                    "- `data/kb/facts.json#f1195` 反馈维度用的是已备份的「未收紧」批次，与现行收紧口径冲突 → 待统一"]
        if k == "情绪-能力":
            out += ["- 缺状态变量的可观测代理（如演出密度、连续场次）与声学读数的对齐实验"]
        out.append("")
    out += ["## 五、引用纪律（写作时必须遵守）", "",
            "- 声学：一律「最低稳定音」口径；触达音/低音带读数只展示、不作能力结论。",
            "- 传播：样本＝可检索到的公开 UGC，**非全平台普查**；平台机制一律「经验性认知（非官方）」。",
            "- 每条词条的「禁忌写法」必须与钩子同页保存，防二次传播走形。",
            "- 不评优劣、不拉踩；事实/推断/待核三分。", ""]

    DOCS.mkdir(parents=True, exist_ok=True)
    p = DOCS / f"传记素材映射_{day}.md"
    p.write_text("\n".join(out), encoding="utf-8")
    print(f"[ok] {p}（{len(entries)} 条词条映射 + {len(assets)} 项资产）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
