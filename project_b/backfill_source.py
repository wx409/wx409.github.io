# -*- coding: utf-8 -*-
"""用「来源台账.json」回填来源：台账里 tag→bv/owner/source_verdict 是逐素材的权威记录。

匹配顺序：tag 精确 → 去掉 _pN_曲名 后的 tag → tag 前缀（≥10 字符）→ 库标题模糊（兜底）
"""
import json, os, re
from collections import Counter
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
TOUR = ROOT / "data" / "archive_stage_tour.json"
LEDGER = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频\来源台账.json")
LIB = Path(r"E:\wx\论文素材_王晰作传\音域分析\轨迹\轨迹素材库.json")
OUT = ROOT / "data" / "source_backfill.json"

def norm(s):
    return re.sub(r"[【】\[\]（）()《》「」\s\-_/|·、，,。.:：!！?？~～]", "", str(s or "")).lower()

TOUR_PREFIX = re.compile(r"^(?:一|二|三|四|五|六)巡")


def key_of(tag):
    t = str(tag or "").strip()
    t = re.sub(r"_BV[0-9A-Za-z]{10}.*$", "", t)
    t = re.sub(r"_p\d+_.*$", "", t)
    t = re.sub(r"^【[^】]*】", "", t)
    return TOUR_PREFIX.sub("", t).strip()


def verdict_class(v):
    v = str(v or "")
    if "官方" in v: return "官方直传"
    if "重制" in v or "混剪" in v: return "二创/混剪"
    return ""

def main() -> int:
    led = json.loads(LEDGER.read_text(encoding="utf-8"))
    items = led.get("items") or []
    by_tag = {}
    by_key = {}
    for it in items:
        t = (it.get("tag") or "").strip()
        if t and t not in by_tag:
            by_tag[t] = it
        k = key_of(t)
        if k and k not in by_key:
            by_key[k] = it

    rows = json.loads(TOUR.read_text(encoding="utf-8"))["rows"]

    def unclassified(r):
        return not (r.get("bv") or "").strip() and not (r.get("source_verdict") or "").strip()

    todo = [r for r in rows if unclassified(r)]
    hits, miss = [], []
    for r in todo:
        tag = (r.get("tag") or "").strip()
        base = re.sub(r"_p\d+_.*$", "", tag) or tag
        base = re.sub(r"_BV.*$", "", base)
        ent = by_tag.get(tag) or by_tag.get(base) or by_key.get(key_of(tag))
        if not ent:
            k = key_of(tag)
            best, sc = None, 0.0
            for kk, ee in by_key.items():
                if abs(len(kk) - len(k)) > 6:
                    continue
                r = SequenceMatcher(None, k, kk).ratio()
                if r > sc:
                    best, sc = ee, r
            if best and sc >= 0.85:
                ent = best
        if not ent:
            # 前缀匹配（≥10 字符）
            for t, e in by_tag.items():
                if len(t) >= 10 and tag.startswith(t[:10]):
                    ent = e; break
        if ent:
            v = ent.get("source_verdict") or ""
            hits.append({"tag": tag, "bv": ent.get("bv") or "", "owner": ent.get("owner") or "",
                         "verdict": v, "cls": verdict_class(v) or "B站（台账已记录·类型未判）",
                         "ledger_tag": ent.get("tag") or ""})
        else:
            miss.append(r)

    print("无来源素材 %d｜台账命中 %d（%.1f%%）｜仍未命中 %d"
          % (len(todo), len(hits), 100*len(hits)/max(1,len(todo)), len(miss)))
    print("命中后类型：", dict(Counter(h["cls"] for h in hits)))
    for r in miss[:6]:
        if isinstance(r, dict):
            print("  未命中:", (r.get("tag") or "")[:60])

    OUT.write_text(json.dumps({
        "schema": "source-backfill/v2",
        "method": "来源台账 tag 精确/去分P/前缀匹配；命中即继承 bv/owner/source_verdict",
        "n_todo": len(todo), "n_hit": len(hits), "n_miss": len(miss),
        "hit_classes": dict(Counter(h["cls"] for h in hits)),
        "hits": hits,
        "miss": [{"tag": (r.get("tag") or "") if isinstance(r, dict) else "",
                 "tour": (r.get("tour") or "") if isinstance(r, dict) else "",
                 "date": (r.get("date") or "") if isinstance(r, dict) else ""} for r in miss],
        "generated_at": date.today().isoformat(),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT.relative_to(ROOT).as_posix())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
