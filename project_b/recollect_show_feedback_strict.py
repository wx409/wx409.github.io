# -*- coding: utf-8 -*-
"""按「本场专属关键词」收紧观众反馈采集口径（一次性＋可复用）。

背景（2026-10-10 事故）：`analyze_audience_comments.load_feedback()` 除了读本场
`show_feedback/<date>_<city>/`，还会读三处**全局未按场次过滤**的语料
（`temp/_xhs_classified.json`、`E:\\wx\\私有工具\\xhs_archive\\按链接`、`temp/_gz_quotes.json`），
导致 2026-10-09 北京站的报告里混进了大量 **2026-08-23 六巡广州**的内容
（曲目提及榜全部是广州曲目、代表句带「8.23 广州」），文件标题亦被误标。

本脚本的做法：**仍用原聚合器取池**，但加一道「本场专属信号」硬过滤 ——
必须命中「剧名/场馆/日期」之一（并含主体词），才计入本场统计；
旧产物先备份，再输出新 JSON/MD（保持原 schema，另加 filter / source_comparison 两段说明）。

用法：
  python -X utf8 project_b\\recollect_show_feedback_strict.py --date 2026-10-09 --city 北京 \
      --show 沉响与长歌 --venue 天桥
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(r"D:\wx409.github.io")
sys.path.insert(0, str(HERE))

import analyze_audience_comments as A  # noqa: E402  复用词表 / analyze / render_md

OUT_DIR = ROOT / "temp" / "audience_analysis"

# 本场专属信号：剧名 / 场馆 / 日期（任一命中即算「本场内容」）
SHOW_SIGNALS = ["沉响与长歌", "沉响", "与长歌", "天桥", "天橋",
                "20261009", "2026-10-09", "10月9日", "10月9號", "10.9", "1009"]
# 主体词（防止命中「天桥」但与本项目无关）
SUBJECT = ["王晰", "傲日", "晰哥", "晰", "魔力sir", "东方演艺"]
# 反证词：命中即判为「非本场」（其他巡演场次/城市的明确标记）
NEG_SIGNALS = ["广州", "廣州", "深圳", "上海", "成都", "杭州", "宁波", "南京", "厦门",
               "8.23", "0823", "20260823", "六巡"]


def hit_any(t, words):
    return [w for w in words if w in t]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--city", required=True)
    ap.add_argument("--show", default="沉响与长歌")
    ap.add_argument("--venue", default="天桥")
    ap.add_argument("--xhs-dirs", default="",
                    help="小红书 crawler 归档的关键词目录名（逗号分隔），"
                         "如 沉响与长歌,王晰 天桥；读取 E:\\wx\\私有工具\\xhs_archive\\<目录>\\*")
    ap.add_argument("--drop-neg", action="store_true",
                    help="同时剔除含其他城市/场次反证词的条目（当该条不含本场剧名时）")
    a = ap.parse_args()

    pool = A.dedup(A.load_feedback(a.date, a.city))
    # 缺陷修补：聚合器只认 `text` 字段，而 B站采集产物用的是 `title`/`desc`
    # → 导致 B站条目**从未进入分析**（本场 14 条全丢）。此处补挂。
    fb_dir = next((d for d in (A.FB / f"{a.date}_{a.city}",
                               A.FB / f"{a.date.replace('-', '')}_{a.city}") if d.exists()), None)
    if fb_dir is not None:
        bili = fb_dir / "bili_feedback.json"
        if bili.exists():
            try:
                arr = json.loads(bili.read_text(encoding="utf-8"))
            except Exception:
                arr = []
            added = 0
            for r in arr:
                if not isinstance(r, dict):
                    continue
                txt = " ".join(str(r.get(k, "")) for k in ("title", "desc") if r.get(k))
                if not txt:
                    continue
                pool.append({"platform": "B站", "text": txt, "user": str(r.get("author", "")),
                             "url": str(r.get("url", "")), "date": a.date})
                added += 1
            print(f"补挂 B站 title/desc：{added} 条（原聚合器因缺 text 字段整批丢弃）")
    # 缺陷修补 2：小红书 crawler（xhs_crawler.py）把笔记存到 xhs_archive/<关键词>/<folder>/，
    # 而聚合器只读「按链接」子目录与全局分类档 → 关键词抓取的结果从未进入单场统计。
    XHS_ARCH = Path(r"E:\wx\私有工具\xhs_archive")
    xhs_added = 0
    for kw_dir in [x.strip() for x in (a.xhs_dirs or "").split(",") if x.strip()]:
        d0 = XHS_ARCH / kw_dir
        if not d0.exists():
            print(f"   （小红书归档目录不存在，跳过：{kw_dir}）")
            continue
        for note_dir in sorted(d0.iterdir()):
            if not note_dir.is_dir():
                continue
            ct = note_dir / "content.txt"
            if not ct.exists():
                continue
            txt = ct.read_text(encoding="utf-8", errors="ignore").strip()
            if not txt:
                continue
            try:
                meta = json.loads((note_dir / "meta.json").read_text(encoding="utf-8"))
            except Exception:
                meta = {}
            pool.append({"platform": "小红书", "text": txt,
                         "user": str(meta.get("author", "") or meta.get("nickname", "")),
                         "url": str(meta.get("link", "") or meta.get("url", "")),
                         "date": a.date, "xhs_kw": kw_dir})
            xhs_added += 1
    if xhs_added:
        print(f"补挂 小红书 crawler 归档：{xhs_added} 条（关键词目录 {a.xhs_dirs}）")
    print(f"聚合池（未收紧）：{len(pool)} 条 | 平台构成 {dict(Counter(i['platform'] for i in pool))}")

    kept, dropped = [], []
    for it in pool:
        t = it["text"]
        sig = hit_any(t, SHOW_SIGNALS)
        sub = hit_any(t, SUBJECT)
        if not sig or not sub:
            dropped.append((it, "缺本场信号" if not sig else "缺主体词"))
            continue
        neg = hit_any(t, NEG_SIGNALS)
        # 其他场次的反证词：只有当该条**没有**剧名/日期这类强信号时才据此剔除
        strong = hit_any(t, ["沉响与长歌", "沉响", "与长歌", "20261009", "2026-10-09", "10月9日"])
        if neg and not strong:
            dropped.append((it, "命中他场反证词(%s)" % "/".join(neg)))
            continue
        it2 = dict(it)
        it2["match"] = {"signal": sig, "subject": sub, "neg": neg}
        kept.append(it2)

    kept = A.dedup(kept)
    print(f"收紧后：{len(kept)} 条 | 平台构成 {dict(Counter(i['platform'] for i in kept))}")
    print(f"剔除：{len(dropped)} 条（原因分布 {dict(Counter(r for _, r in dropped))}）")
    print("\n--- 保留条目预览（前 20）---")
    for it in kept[:20]:
        print(f"  [{it['platform']}] match={it['match']['signal']}｜{it['text'][:70]}")

    stats = A.analyze(kept, a.date)
    stats["fingerprint"] = hashlib.md5(
        json.dumps([i["text"] for i in kept], ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
    stats["filter"] = {
        "rule": "必须命中本场信号（剧名/场馆/日期）之一 且 含主体词；含他场反证词且无强信号者剔除",
        "show_signals": SHOW_SIGNALS, "subject": SUBJECT, "neg_signals": NEG_SIGNALS,
        "pool_total": len(pool), "pool_platforms": dict(Counter(i["platform"] for i in pool)),
        "kept_total": len(kept), "kept_platforms": dict(Counter(i["platform"] for i in kept)),
        "dropped_total": len(dropped),
        "dropped_reasons": dict(Counter(r for _, r in dropped)),
    }
    old_json = OUT_DIR / f"{a.date}_{a.city}.json"
    old_md = OUT_DIR / f"{a.date}_{a.city}.md"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # 1) 备份旧批次（可回溯）
    for src, tag in ((old_json, "旧批次_未收紧"), (old_md, "旧批次_未收紧"),
                     (old_json, "v1"), (old_md, "v1")):
        if src.exists():
            bak = OUT_DIR / f"{a.date}_{a.city}_{tag}{src.suffix}"
            if not bak.exists():
                bak.write_bytes(src.read_bytes())
                print(f"备份旧产物 → {bak.name}")
    # 2) 写新产物
    payload = {"fingerprint": stats["fingerprint"], "date": a.date, "city": a.city,
               "show": a.show, "llm": None, "stats": stats}
    old_json.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    old_md.write_text(A.render_md(a.date, a.city, stats, None), encoding="utf-8")
    print(f"\n[ok] 新产物 → {old_json.name} / {old_md.name}")
    print(f"  total {stats['total']}｜维度 {stats['dimensions']}")
    print(f"  情感 {stats['sentiment']}｜歌名榜 {stats['song_top'][:6]}")
    (OUT_DIR / f"{a.date}_{a.city}_filter_report.json").write_text(
        json.dumps({"pool": [{"platform": i["platform"], "text": i["text"][:160], "url": i["url"]}
                             for i in pool],
                    "kept": [{"platform": i["platform"], "text": i["text"][:160], "url": i["url"],
                              "match": i.get("match")} for i in kept],
                    "dropped": [{"platform": i["platform"], "text": i["text"][:160],
                                 "reason": r} for i, r in dropped]},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] 过滤明细 → {a.date}_{a.city}_filter_report.json")


if __name__ == "__main__":
    main()
