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
LOCAL_INDEX = Path(r"E:\wx\论文素材_王晰作传\歌迷文章（含已发表）\_转换_markdown\_index.json")
OUT = DATA / "fan_essays.json"
# 人工确认字段（作者/发表/授权）：按曲名覆盖默认值
OVERRIDES: dict[str, dict] = {}


def norm(s: str) -> str:
    s = re.sub(r"[《》\s（）()＋+&·、「」]", "", str(s or ""))
    return re.sub(r"(live|官方\d+k|版)$", "", s, flags=re.I)


def acoustic_map() -> dict[str, dict]:
    """曲名 → 最低稳定音读数（严格匹配：2 字只认全等，≥3 字允许前缀）。"""
    rows = (json.loads((DATA / "vocal_measurements.json").read_text(encoding="utf-8")).get("rows") or [])
    by_song: dict[str, list] = {}
    for r in rows:
        if (r.get("metrics") or {}).get("low_hz"):
            by_song.setdefault(str(r.get("song") or ""), []).append(r)
    out = {}
    for disc, rs in by_song.items():
        out[norm(disc)] = {"song": disc, "rows": rs}
    return out


def build() -> dict:
    if not LOCAL_INDEX.exists():
        raise SystemExit(f"本地索引不存在：{LOCAL_INDEX}（先跑 tools/fan_essays_convert.py）")
    idx = json.loads(LOCAL_INDEX.read_text(encoding="utf-8"))["items"]
    ac = acoustic_map()
    items = []
    for i, it in enumerate(sorted(idx, key=lambda x: int(re.match(r"(\d+)", x["file"]).group(1))
                                 if re.match(r"(\d+)", x["file"]) else 99), 1):
        key = norm(it["song"])
        hit = None
        if len(key) >= 2:
            for k, v in ac.items():
                if len(k) < 2:
                    continue
                if key == k or (len(key) >= 3 and len(k) >= 3 and (k.startswith(key) or key.startswith(k))):
                    best = min(v["rows"], key=lambda x: x["metrics"]["low_hz"])
                    hit = {"song": v["song"], "layer": best.get("layer"),
                           "low_note": best["metrics"]["low_note"], "low_hz": best["metrics"]["low_hz"],
                           "versions": len(v["rows"]), "matched": "精确" if key == k else "近似"}
                    break
        o = OVERRIDES.get(it["song"], {})
        items.append({
            "no": i,
            "song": re.sub(r"[《》]", "", it["song"]).strip(),
            "title": re.sub(r"\s+", " ", it.get("title") or "").strip()[:90] or f"《{it['song']}》赏析",
            "chars": it.get("chars"), "written": it.get("mtime", ""),
            "author": o.get("author") or it.get("author_hint") or "待补",
            "published": o.get("published") or "待核（作者确认中）",
            "rights": o.get("rights") or "待确认（本站未转载全文）",
            "acoustic": hit,
        })
    return {
        "schema": 1,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": "歌迷赏析（民间评论）索引。全文为作者著作权内容，本站不转载；发表与授权状态待作者确认。"
                "「声学互证」列为本站同一曲目的实测读数（最低稳定音口径），用于「文本分析 × 声学数据」交叉参照。",
        "source": "歌迷投稿（撰写于 2024-07；整理入档，全文本地留存，未进公开仓库）",
        "rights": {"policy": "全文不转载、不提供下载；如作者授权，可另设摘要或全文页",
                   "status": "待确认", "contact": "如为作者本人，欢迎通过站点投稿页联系授权与署名"},
        "counts": {"total": len(items),
                   "with_acoustic": sum(1 for x in items if x["acoustic"]),
                   "total_chars": sum(x["chars"] or 0 for x in items)},
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
