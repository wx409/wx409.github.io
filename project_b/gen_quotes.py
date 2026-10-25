#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""句子装配厂：用「事实原子 + 模板」生成可核查的句子。

规则（写死在代码里，不靠人记）：
  1. 句子里每个数字都必须来自某条事实；
  2. 不同范围（录音室/现场/专辑）的事实不得混成一句而不label；
  3. 每条句子都带 boundary 与 fact_ids，可回查；
  4. 数据更新 → 重建事实 → 重生成句子，旧句子自然消失（不手改）。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
FACTS = D / "fact_atoms.json"
OUT = D / "quotes_generated.json"


def main() -> None:
    facts = json.loads(FACTS.read_text(encoding="utf-8"))["facts"]
    by_id = {f["id"]: f for f in facts}
    songs = {}
    for f in facts:
        if f["kind"] == "song_versions":
            songs[f["subject"]] = {"versions": f}
        elif f["kind"] == "song_range":
            songs.setdefault(f["subject"], {})["range"] = f
    layers = {f["id"]: f for f in facts if f["kind"] in ("extreme", "distribution", "scale")}

    quotes = []

    def emit(text, fids, mode, boundary):
        quotes.append({"text": text, "fact_ids": fids, "mode": mode,
                       "boundary": boundary,
                       "snapshots": sorted({by_id[i]["snapshot"] for i in fids if by_id[i]["snapshot"]}),
                       "sources": sorted({by_id[i]["source"] for i in fids})})

    # T1 单事实：某首歌的版本分布
    for song, g in songs.items():
        v = g.get("versions")
        if not v:
            continue
        emit(f'{song}：{v["value"]}。', [v["id"]], "short", v["boundary"])
        if g.get("range"):
            r = g["range"]
            emit(f'{song}：{v["value"]}；{r["metric"]}约 {r["value"]} 半音（{r["scope"]}）。',
                 [v["id"], r["id"]], "full", r["boundary"])

    # T2 同层两事实：录音室层
    pairs = [("F-studio-lowest", "F-studio-span"), ("F-studio-lowest", "F-studio-stability"),
             ("F-stage-scale", "F-stage-span")]
    for a, b in pairs:
        if a not in by_id or b not in by_id:
            continue
        fa, fb = by_id[a], by_id[b]
        emit(f'{fa["subject"]}：{fa["metric"]}{fa["value"]}{fa["unit"]}；'
             f'{fb["metric"]}{fb["value"]}{fb["unit"]}（{fb["scope"]}）。',
             [a, b], "full", f"{fa['boundary']}；{fb['boundary']}")

    # T3 单层事实
    for fid in ("F-studio-lowest", "F-studio-span", "F-vibrato-range", "F-stage-scale", "F-stage-span"):
        if fid not in by_id:
            continue
        f = by_id[fid]
        emit(f'{f["subject"]}的{f["metric"]}是 {f["value"]}{f["unit"]}（{f["scope"]}）。',
             [fid], "short", f["boundary"])

    out = {"schema": "quotes_generated/v1", "count": len(quotes), "quotes": quotes}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"生成 {len(quotes)} 条 -> data/quotes_generated.json")
    for q in quotes[:6]:
        print(f'  [{q["mode"]}] {q["text"]}')


if __name__ == "__main__":
    main()
