# -*- coding: utf-8 -*-
"""歌迷赏析索引生成器 —— 从本地原文目录派生 data/fan_essays.json（站点只放元数据）。

著作权纪律（重要）：
  · 全文为作者本人作品：**只本地留存**（源目录 + _转换_markdown），**不进公开仓库、不转载**；
  · 本脚本只产出元数据索引（篇名/篇幅/撰写时间/发表与授权状态/声学互证），不含正文；
  · 发表状态与授权状态默认「待核 / 待确认」，作者确认后人工更新 registry 里的覆盖字段。

输入：
  <源目录>\\_转换_markdown\\_index.json     由 tools\\fan_essays_convert.py 生成的本地索引
  data/vocal_measurements.json              用于「文本 × 声学」互证（最低稳定音）
输出：
  data/fan_essays.json（公开，仅元数据）

用法：
  python -X utf8 project_b/build_fan_essays.py                 # 生成/刷新
  python -X utf8 project_b/build_fan_essays.py --check         # 只报告是否需要更新
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "project_b"))
from song_resolver import resolve as resolve_song, acoustic_for  # noqa: E402  复用共享解析器（三级名称库 + 别名表）
LOCAL_INDEX = Path(r"E:\wx\论文素材_王晰作传\歌迷文章（含已发表）\_转换_markdown\_index.json")
OUT = DATA / "fan_essays.json"
# 人工确认字段（作者/发表/授权）：按曲名覆盖默认值
OVERRIDES: dict[str, dict] = {}


def build() -> dict:
    if not LOCAL_INDEX.exists():
        raise SystemExit(f"本地索引不存在：{LOCAL_INDEX}（先跑 tools/fan_essays_convert.py）")
    idx = json.loads(LOCAL_INDEX.read_text(encoding="utf-8"))["items"]
    items, by_source = [], {}
    for i, it in enumerate(sorted(idx, key=lambda x: int(re.match(r"(\d+)", x["file"]).group(1))
                                 if re.match(r"(\d+)", x["file"]) else 99), 1):
        raw_song = re.sub(r"[《》]", "", str(it["song"] or "")).strip()
        r = resolve_song(raw_song)
        a = acoustic_for(r.get("canonical") or raw_song) or acoustic_for(r.get("norm") or raw_song)
        parts_info = None
        # 组曲（如二巡钢琴组曲「慢系列」）：展开为组成曲目，逐曲取实测
        from song_resolver import medley_parts, album_tracks  # noqa: E402
        mp = medley_parts(raw_song)
        if mp:
            parts_info = {"kind": "medley", "parts": [], "with_acoustic": 0}
            best = None
            for t in mp:
                rr = resolve_song(t)
                aa = acoustic_for(rr.get("canonical") or t) or acoustic_for(rr.get("norm") or t)
                parts_info["parts"].append({"song": t, "acoustic": aa})
                if aa:
                    parts_info["with_acoustic"] += 1
                    if best is None or aa["low_hz"] < best["low_hz"]:
                        best = aa
            r = {"canonical": raw_song, "source": "medley", "kind": "song",
                 "matched": "组曲展开", "norm": r.get("norm")}
            a = best
        else:
            # 仅当标题明确写「专辑」时才做整专展开（避免《歌颂》这类歌名与专辑同名被误判）
            tracks = album_tracks(raw_song) if "专辑" in raw_song else []
            if tracks:
                parts_info = {"kind": "album", "album": re.sub(r"^专辑", "", raw_song),
                              "tracks": [], "with_acoustic": 0}
                best = None
                for t in tracks:
                    aa = acoustic_for(t)
                    parts_info["tracks"].append({"song": t, "acoustic": aa})
                    if aa:
                        parts_info["with_acoustic"] += 1
                        if best is None or aa["low_hz"] < best["low_hz"]:
                            best = aa
                r = {"canonical": raw_song, "source": "album", "kind": "album",
                     "matched": "整张专辑", "norm": r.get("norm")}
                a = best
        if not a and r.get("source") == "none":
            # 「A+B」合写：拆开逐个解析，取能对上声学实测的那个
            from song_resolver import split_titles  # noqa: E402
            for part in split_titles(raw_song):
                rr = resolve_song(part)
                aa = acoustic_for(rr.get("canonical") or part) or acoustic_for(rr.get("norm") or part)
                if rr.get("source") != "none" or aa:
                    r, a = rr, aa
                if aa:
                    break
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
        o = OVERRIDES.get(raw_song, {})
        items.append({
            "no": i,
            "song": raw_song,
            "title": re.sub(r"\s+", " ", it.get("title") or "").strip()[:90] or f"《{raw_song}》赏析",
            "chars": it.get("chars"), "written": it.get("mtime", ""),
            "author": o.get("author") or it.get("author_hint") or "待补",
            "published": o.get("published") or "待核（作者确认中）",
            "rights": o.get("rights") or "待确认（本站未转载全文）",
            "resolved": {"canonical": r.get("canonical"), "source": r.get("source"),
                         "kind": r.get("kind"), "matched": r.get("matched", "精确")},
            "parts": parts_info,
            "acoustic": a,
        })
    return {
        "schema": 1,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": "歌迷赏析（民间评论）索引。全文为作者著作权内容，本站不转载；发表与授权状态待作者确认。"
                "曲名解析复用仓库既有归一化与别名表，按「巡演歌单 → 演出活动表 → 全量曲库」三级查找；"
                "「声学互证」列为本站同一曲目的实测最低稳定音（不含触达音读数）。",
        "source": "歌迷投稿（撰写于 2024-07；整理入档，全文本地留存，未进公开仓库）",
        "rights": {"policy": "全文不转载、不提供下载；如作者授权，可另设摘要或全文页",
                   "status": "待确认", "contact": "如为作者本人，欢迎通过站点投稿页联系授权与署名"},
        "counts": {"total": len(items),
                   "with_acoustic": sum(1 for x in items if x["acoustic"]),
                   "total_chars": sum(x["chars"] or 0 for x in items),
                   "resolved_by": by_source},
        "items": items,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    doc = build()
    new = json.dumps(doc, ensure_ascii=False, indent=1)
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    same = old.split('"generated_at"')[0] == new.split('"generated_at"')[0] and \
        json.loads(old).get("counts") == doc["counts"] if old else False
    if a.check:
        print(f"[检查] {'已最新' if same else '需要更新'}｜{doc['counts']}")
        return 0 if same else 1
    OUT.write_text(new, encoding="utf-8")
    print(f"[OK] {OUT.name}｜{doc['counts']['total']} 篇 / {doc['counts']['total_chars']} 字"
          f"｜声学互证 {doc['counts']['with_acoustic']} 篇")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
