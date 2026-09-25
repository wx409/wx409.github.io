# -*- coding: utf-8 -*-
"""《歌曲证据总表》v2 —— 修掉 v1 三个缺陷。

v2 修复
-------
① **文本提及假阳性**：通用词曲名（时间/爱情/是你…）只统计 **《》「」"" 内的出现**；
   非通用曲名（≥4 字或含专名）才允许裸匹配。
② **曲名净化**：两遍规范化——先收集全部来源的名字，再按「去演出后缀+去演唱者后缀」的严格键分组，
   选展示最优者为规范名，最后**所有来源统一映射**，消除 `(Live)` 残留与截断名。
③ **接声音素材源**：自动探测 voice corpus / tavern 转写 / archive_voice，统计曲目出现次数。

用法：python -X utf8 project_b\\build_song_evidence_master.py [--no-text]
产出：data/song_evidence_master.json ＋ E:\\wx\\论文素材_王晰作传\\歌曲证据总表.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from index_source import load as load_idx  # noqa: E402
import song_names as SN  # noqa: E402

OUT_JSON = SITE / "data" / "song_evidence_master.json"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\歌曲证据总表.md")
TEXT_ROOTS = [Path(r"E:\wx\私有工具\weibo_merged"), Path(r"E:\wx\wx_textmine_corpus")]
VOICE_CANDIDATES = [SITE / "data" / "voice_corpus.json", SITE / "data" / "voice_episodes.json",
                    SITE / "data" / "archive_voice.json", SITE / "tavern" / "tavern_transcripts.json",
                    SITE / "data" / "tavern" / "transcripts.json"]
# 通用词曲名：裸匹配会假阳性 → 只在书名号/引号内计数
GENERIC = {"时间", "爱情", "是你", "遇见", "人间", "也许", "情歌", "遗憾", "生日快乐", "夜色",
           "心动", "谁", "星", "玫瑰", "往前", "回声", "月", "梦", "家", "路", "光", "花"}


def strip_suffix(x: str) -> str:
    return SN._STRIP_SUFFIX.sub("", SN._ARTIST_TAIL.sub("", str(x)).strip()).strip()


def build_canon_map(names: set[str]) -> dict[str, str]:
    """表内两遍净化：按严格键分组 → 选展示最优者 → 返回 {原名: 规范名}"""
    groups = defaultdict(set)
    for n in names:
        groups[SN.strict_norm(strip_suffix(n))].add(n)
    m = {}
    for _, vs in groups.items():
        best = strip_suffix(sorted(vs, key=lambda x: -SN._display_score(x))[0])   # 规范名不带演唱者后缀
        for v in vs:
            m[v] = best
    return m


def mentions(names: set[str], canon_map: dict[str, str]) -> Counter:
    """文本提及：通用词只算书名号内；其余允许裸匹配。"""
    pats = {}
    for n in names:
        base = strip_suffix(n)
        if len(base) < 2:
            continue
        if base in GENERIC or len(base) <= 2:
            pats[n] = re.compile(r"[《〈「【\"“']" + re.escape(base) + r"[》〉」】\"”']")
        else:
            pats[n] = re.compile(re.escape(base))
    files = []
    for root in TEXT_ROOTS:
        if root.exists():
            files += [p for p in root.rglob("*.txt") if p.stat().st_size < 400 * 1024]
    print(f"  文本源：{len(files)} 个文件｜匹配式 {len(pats)} 条")
    cnt = Counter()
    for i, p in enumerate(files):
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for n, rx in pats.items():
            if rx.search(t):
                cnt[canon_map.get(n, n)] += 1
        if i and i % 3000 == 0:
            print(f"    …{i}/{len(files)}")
    return cnt


def voice_mentions(names: set[str], canon_map: dict[str, str]) -> tuple[Counter, str]:
    """声音素材提及：自动探测可用源。"""
    src = next((p for p in VOICE_CANDIDATES if p.exists()), None)
    if not src:
        return Counter(), "（未找到声音素材源）"
    try:
        raw = json.loads(src.read_text(encoding="utf-8"))
    except Exception:
        return Counter(), f"（{src.name} 读取失败）"
    blob = json.dumps(raw, ensure_ascii=False)
    cnt = Counter()
    for n in names:
        base = strip_suffix(n)
        if len(base) >= 2 and base in blob:
            cnt[canon_map.get(n, n)] = blob.count(base)
    return cnt, f"{src.relative_to(SITE)}（{len(blob)//1024} KB）"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-text", action="store_true")
    a = ap.parse_args()

    alb = json.loads((SITE / "data" / "archive_vocal_albums.json").read_text(encoding="utf-8"))
    ac_raw = {x["title"]: x for x in alb["songs"] if x.get("title")}
    meta = json.loads((SITE / "data" / "songs_meta.json").read_text(encoding="utf-8"))["songs"]
    meta_raw = {}
    for k, v in meta.items():
        nm = re.sub(r"\s+", " ", str((v or {}).get("name") or k)).split("\n")[0].strip()
        meta_raw[nm] = v
    st = json.loads((SITE / "data" / "archive_stage_tour.json").read_text(encoding="utf-8"))
    stage_raw = Counter()
    for r in (st.get("rows") or st.get("materials") or []):
        for key in ("song", "title", "曲目"):
            if r.get(key):
                stage_raw[str(r[key])] += 1
                break
    df = load_idx()
    g = df.dropna(subset=["current_index"])
    g = g[g["current_index"] > 0]
    idx_raw = {}
    for s, x in g.groupby("canon"):
        idx_raw[s] = {"days": int(x["day"].nunique()), "median": round(float(x["current_index"].median()), 1),
                      "peak": float(x["current_index"].max()), "first": x["day"].min()}

    # ── 两遍净化：统一规范名 ─────────────────────────────
    universe = set(ac_raw) | set(meta_raw) | set(stage_raw) | set(idx_raw)
    cmap = build_canon_map(universe)
    print(f"名字宇宙 {len(universe)} → 规范名 {len(set(cmap.values()))}（合并 {len(universe)-len(set(cmap.values()))}）")

    def C(x):
        return cmap.get(x, strip_suffix(x))
    ac = {C(k): v for k, v in ac_raw.items()}
    shows, kinds = {}, {}
    for k, v in meta_raw.items():
        cn = C(k)
        shows[cn] = max(shows.get(cn, 0), (v or {}).get("show_count") or 0)
    for k, n in stage_raw.items():
        stage_c = C(k)
        stage_raw[k] = n
    stage = Counter()
    for k, n in stage_raw.items():
        stage[C(k)] += n
    idx = {C(k): v for k, v in idx_raw.items()}

    names = set(ac) | set(shows) | set(stage) | set(idx)
    names = {n for n in names if n and len(n) >= 2}
    print(f"并入曲目：{len(names)} 首")

    men = Counter() if a.no_text else mentions(universe, cmap)
    voi, voi_src = voice_mentions(universe, cmap)
    print(f"  声音素材源：{voi_src}")

    rows = []
    for n in names:
        A = ac.get(n) or {}
        rs = A.get("register_share") or {}
        rows.append({"song": n, "low_note": A.get("low"), "low_hz": A.get("low_hz"),
                     "bass_share": rs.get("low_lt_C3"),
                     "show_count": shows.get(n, 0),
                     "stage_materials": stage.get(n, 0),
                     "text_mentions": men.get(n, 0),
                     "voice_mentions": voi.get(n, 0),
                     "idx_days": (idx.get(n) or {}).get("days", 0),
                     "idx_median": (idx.get(n) or {}).get("median"),
                     "idx_peak": (idx.get(n) or {}).get("peak"),
                     "idx_first": (idx.get(n) or {}).get("first")})
    for r in rows:
        r["sources_with_data"] = sum(1 for k in ("low_hz", "show_count", "stage_materials",
                                                 "text_mentions", "voice_mentions", "idx_days")
                                     if (r.get(k) or 0))
    rows.sort(key=lambda r: (-r["sources_with_data"], -(r["idx_days"] or 0), -(r["text_mentions"] or 0)))

    cov = {"acoustic": sum(1 for r in rows if r["low_hz"]), "shows": sum(1 for r in rows if r["show_count"]),
           "stage": sum(1 for r in rows if r["stage_materials"]),
           "text": sum(1 for r in rows if r["text_mentions"]),
           "voice": sum(1 for r in rows if r["voice_mentions"]),
           "index": sum(1 for r in rows if r["idx_days"])}
    OUT_JSON.write_text(json.dumps({"generated_at": datetime.now().isoformat(timespec="seconds"),
                                    "n_songs": len(rows), "coverage": cov,
                                    "voice_source": voi_src, "rows": rows},
                                   ensure_ascii=False, indent=1), encoding="utf-8")

    strong = [r for r in rows if r["sources_with_data"] >= 4]
    L = ["# 歌曲证据总表 v2（多源交叉，不合成单一分数）", "",
         f"生成 {datetime.now():%Y-%m-%d %H:%M}｜并入 **{len(rows)}** 首｜声音素材源：{voi_src}", "",
         "## 覆盖", "", "| 来源 | 曲目数 |", "|---|---|"]
    for k, v in cov.items():
        L.append(f"| {k} | {v} |")
    L += ["", "## 四源及以上有据（按源数/指数寿命排序，前 60）", "",
          "| 曲目 | 最低音 | Hz | 低音占比 | 演出 | 舞台 | 文本 | 声音 | 指数天 | 中位 | 源数 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in strong[:60]:
        L.append(f"| {r['song'][:18]} | {r['low_note'] or '—'} | {r['low_hz'] or '—'} | "
                 f"{r['bass_share'] if r['bass_share'] is not None else '—'} | {r['show_count']} | "
                 f"{r['stage_materials']} | {r['text_mentions']} | {r['voice_mentions']} | {r['idx_days']} | "
                 f"{r['idx_median'] if r['idx_median'] is not None else '—'} | {r['sources_with_data']} |")
    L += ["", "## 指数寿命 Top 20（平台口径）", "", "| 曲目 | 指数天 | 中位 | 峰值 | 首日 |",
          "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: -(x["idx_days"] or 0))[:20]:
        L.append(f"| {r['song'][:18]} | {r['idx_days']} | {r['idx_median']} | {r['idx_peak']} | {r['idx_first']} |")
    L += ["", "## 现场保留曲目 Top 20（演出场次）", "", "| 曲目 | 演出 | 舞台素材 | 文本 | 指数天 |",
          "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: -(x["show_count"] or 0))[:20]:
        L.append(f"| {r['song'][:18]} | {r['show_count']} | {r['stage_materials']} | "
                 f"{r['text_mentions']} | {r['idx_days']} |")
    L += ["", "## 低音特色曲（低音占比 ≥0.4）", "",
          "| 曲目 | 最低音 | Hz | 低音占比 | 演出 | 指数天 | 源数 |", "|---|---|---|---|---|---|---|"]
    for r in sorted([x for x in rows if (x["bass_share"] or 0) >= 0.4],
                    key=lambda x: -(x["bass_share"] or 0))[:25]:
        L.append(f"| {r['song'][:18]} | {r['low_note']} | {r['low_hz']} | {r['bass_share']} | "
                 f"{r['show_count']} | {r['idx_days']} | {r['sources_with_data']} |")
    L += ["", "## 口径与边界", "",
          "- 文本提及：通用词曲名（时间/爱情/是你…）**只在《》「」引号内计数**；其余允许裸匹配（v2 修复）",
          "- 曲名：**两遍净化**（去演出/演唱者后缀 → 表内严格键分组取展示最优），消除 (Live) 残留（v2 修复）",
          "- 声学仅录音室曲目；舞台素材来自现场层；指数为权威全量源 current_index>0（0 值=占位行，已剔除）",
          "- **不作因果推断**；本表用于选材（哪首歌有几源证据支撑）", ""]
    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    print(f"\n覆盖：{cov}")
    print(f"四源以上：{len(strong)} 首 → {[r['song'][:12] for r in strong[:12]]}")
    print(f"\n→ {OUT_JSON}\n→ {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
