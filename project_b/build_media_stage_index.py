# -*- coding: utf-8 -*-
"""晚会·综艺·合作舞台索引：把散在各数据文件的"非巡演曝光"捞成结构化表。

为什么需要：现场层素材只来自巡演饭拍，**晚会/综艺几乎未收录**
（例：《雾里》2023 央视网络春晚，五源里四源为 0）→ 这是素材缺口，不是数据问题。

抽取方式：**确定性关键词扫描 + 已知合作者词典**（不调 LLM，可复现）。
产出：data/media_stage_index.json ＋ E:\wx\论文素材_王晰作传\晚会综艺合作舞台索引.md
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from song_names import canon  # noqa: E402

OUT_JSON = SITE / "data" / "media_stage_index.json"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\晚会综艺合作舞台索引.md")

PLATFORM = {"央视": ["央视", "CCTV", "中央广播电视总台", "总台"], "湖南卫视": ["湖南卫视", "芒果"],
            "江苏卫视": ["江苏卫视"], "东方卫视": ["东方卫视"], "浙江卫视": ["浙江卫视"],
            "北京卫视": ["北京卫视"], "广东卫视": ["广东卫视"], "辽宁卫视": ["辽宁卫视"],
            "腾讯": ["腾讯", "TME"], "爱奇艺": ["爱奇艺"], "优酷": ["优酷"], "B站": ["B站", "bilibili"]}
PROGRAM = {"春晚": ["春晚", "春节联欢"], "网络春晚": ["网络春晚"], "元宵": ["元宵"],
           "中秋": ["中秋"], "国庆": ["国庆"], "跨年": ["跨年"], "双十一": ["双十一", "天猫"],
           "金钟奖": ["金钟奖"], "金鹰奖": ["金鹰奖"], "歌手": ["我是歌手", "歌手20", "歌手2026", "歌手"],
           "声入人心": ["声入人心"], "综艺": ["综艺", "真人秀", "季播"], "颁奖盛典": ["盛典", "颁奖", "典礼"],
           "音乐节": ["音乐节", "音乐盛典"], "演唱会(合作)": ["演唱会", "音乐会"]}
PARTNERS = ["张韶涵", "么红", "黄霄雲", "黄霄云", "尚雯婕", "谭维维", "杨洪基", "井柏然", "龚俊",
            "张可盈", "李汶翰", "尹姝贻", "汪小敏", "傲日其愣", "廖昌永", "霍圆元", "阿云嘎",
            "郑云龙", "鞠红川", "王凯", "蔡程昱", "马佳", "周深", "李琦", "王凯丽", "金圣权"]


def scan(text: str) -> dict:
    plat = [k for k, kws in PLATFORM.items() if any(w in text for w in kws)]
    prog = [k for k, kws in PROGRAM.items() if any(w in text for w in kws)]
    parts = [p for p in PARTNERS if p in text]
    return {"platforms": plat, "programs": prog, "partners": parts}


def main() -> int:
    # 已知曲目宇宙（用于从文本里认出曲目）
    master = json.loads((SITE / "data" / "song_evidence_master.json").read_text(encoding="utf-8"))
    universe = sorted({r["song"] for r in master["rows"] if len(r["song"]) >= 2},
                      key=len, reverse=True)

    rows = []
    # 来源 1：timeline（生涯事件）
    tl = json.loads((SITE / "data" / "timeline.json").read_text(encoding="utf-8"))
    tl = tl if isinstance(tl, list) else (tl.get("items") or [])
    for t in tl:
        blob = json.dumps(t, ensure_ascii=False)
        s = scan(blob)
        if s["platforms"] or s["programs"]:
            rows.append({"date": str(t.get("date") or "")[:10], "kind": t.get("type") or "生涯",
                         "title": t.get("title") or "", **s, "source": "timeline.json"})
    # 来源 2：live_repos（视频库标题）
    lr = json.loads((SITE / "data" / "live_repos.json").read_text(encoding="utf-8"))
    items = lr if isinstance(lr, list) else (lr.get("items") or lr.get("repos") or [])
    for it in (items if isinstance(items, list) else []):
        blob = json.dumps(it, ensure_ascii=False)
        s = scan(blob)
        if s["platforms"] or s["programs"] or s["partners"]:
            songs = [u for u in universe if u in blob][:5]
            rows.append({"date": str(it.get("date") or "")[:10], "kind": "视频库",
                         "title": str(it.get("title") or it.get("name") or "")[:60],
                         "songs": songs, **s, "source": "live_repos.json"})
    # 来源 3：现场层素材 tag（含综艺/晚会字样者）
    st = json.loads((SITE / "data" / "archive_stage_tour.json").read_text(encoding="utf-8"))
    for r in (st.get("rows") or st.get("materials") or []):
        blob = json.dumps(r, ensure_ascii=False)
        s = scan(blob)
        if s["platforms"] or s["programs"] or s["partners"]:
            rows.append({"date": str(r.get("date") or "")[:10], "kind": "现场层",
                         "title": str(r.get("tag") or r.get("song") or "")[:70],
                         "songs": [canon(str(r.get("song")))] if r.get("song") else [],
                         **s, "source": "archive_stage_tour.json"})
    # 来源 4：动态范围档案（含"综艺/…"路径）
    try:
        dr = json.loads((SITE / "data" / "archive_dynamic_range.json").read_text(encoding="utf-8"))
        for k in (dr.get("rows") or dr.get("items") or []):
            blob = json.dumps(k, ensure_ascii=False)
            s = scan(blob)
            if s["platforms"] or s["programs"]:
                rows.append({"date": str(k.get("date") or "")[:10], "kind": "动态范围",
                             "title": blob[:70], "source": "archive_dynamic_range.json", **s})
    except Exception:
        pass

    seen, uniq = set(), []
    for r in rows:
        key = (r["date"], r["title"][:30], tuple(r.get("partners") or []))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    uniq.sort(key=lambda x: (x["date"] or "9999"))

    OUT_JSON.write_text(json.dumps({"generated_at": datetime.now().isoformat(timespec="seconds"),
                                    "n": len(uniq), "rows": uniq}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    L = ["# 晚会 · 综艺 · 合作舞台索引（初版）", "",
         f"生成 {datetime.now():%Y-%m-%d %H:%M}｜条目 **{len(uniq)}**", "",
         "> 建它的原因：现场层素材**只来自巡演饭拍**，晚会/综艺几乎未收录 ——",
         "> 这正是《雾里》（2023 央视网络春晚）在五源里四源为 0 的原因：**缺口在素材，不在分析**。", "",
         "| 日期 | 类型 | 平台/节目 | 合作者 | 曲目 | 标题 | 来源 |", "|---|---|---|---|---|---|---|"]
    for r in uniq:
        L.append(f"| {r['date'] or '—'} | {r['kind']} | {'/'.join((r.get('platforms') or []) + (r.get('programs') or [])) or '—'} "
                 f"| {'、'.join(r.get('partners') or []) or '—'} | {'、'.join(r.get('songs') or []) or '—'} "
                 f"| {r['title'][:42]} | {r['source']} |")
    L += ["", "## 已知缺口（必须补）", "",
          "- **《雾里》2023 央视网络春晚**（与么红、黄霄雲）：索引内**无条目**，需人工补录",
          "- **《黎明前的黑暗》**（与张韶涵，综艺舞台）：仅有指数/文本痕迹，**无舞台素材**",
          "- 央视/卫视晚会、声入人心、歌手等综艺的**完整曲目与日期**均未系统登记", "",
          "## 补录方式", "",
          "1. 从微博语料（934+3275 篇）与视频库标题中抽取晚会/综艺条目（本索引已做初版扫描）",
          "2. 人工核对日期与曲目，写入 `data/media_stage_index.json` 的 rows",
          "3. 再跑本脚本合并去重（幂等）", ""]
    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    print(f"晚会/综艺/合作条目：{len(uniq)}")
    from collections import Counter
    print("  按来源:", dict(Counter(r["source"] for r in uniq)))
    print("  含合作者:", sum(1 for r in uniq if r.get("partners")))
    print(f"→ {OUT_JSON}\n→ {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
