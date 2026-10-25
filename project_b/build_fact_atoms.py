#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""事实原子库：把站点数据拆成不可再分的「事实」，每条自带范围与边界。

句子会过时，事实不会：数据更新 → 重建事实 → 重建句子 → 旧句子自动失效。
每个事实必须能回答：主体 / 指标 / 值 / 单位 / 范围 / 证据 / 不能推出什么。

输出：data/fact_atoms.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"


def load(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d or {}


def main() -> None:
    alb = load(D / "archive_vocal_albums.json")
    stg = load(D / "archive_stage_tour.json")
    lv = load(D / "live_versions.json")
    vs = load(D / "derived" / "vibrato_spread.json")
    a = alb.get("summary", {})
    s = stg.get("summary", {})

    facts = []

    def add(fid, kind, subject, metric, value, unit, scope, boundary, source, snapshot=""):
        facts.append({"id": fid, "kind": kind, "subject": subject, "metric": metric,
                      "value": value, "unit": unit, "scope": scope,
                      "boundary": boundary, "source": source, "snapshot": snapshot})

    lo = a.get("lowest") or {}
    add("F-studio-lowest", "extreme", "录音室全量", "最低稳定音",
        f'{lo.get("note")} {lo.get("hz")}Hz', "", "72 首录音室曲目",
        "已测 72 首里的最低音，不代表生理极限", "archive_vocal_albums#summary.lowest", "albums")
    add("F-studio-span", "distribution", "录音室全量", "跨度中位",
        a.get("span_median_octaves"), "八度", "72 首录音室曲目",
        "跨度是单曲最低到最高的距离，不是唱功评分", "archive_vocal_albums#summary.span_median_octaves", "albums")
    add("F-studio-stability", "distribution", "录音室全量", "音符内稳定性中位",
        a.get("stability_cents_median") or a.get("stability_median_cents"), "音分",
        "72 首录音室曲目", "单音内部抖动，不是整曲音准", "archive_vocal_albums#summary.stability", "albums")

    rel = vs.get("release") or {}
    add("F-vibrato-range", "distribution", "专辑层", "逐碟颤音速率中位极差",
        rel.get("value_hz"), "Hz", f'{len(vs.get("included_albums") or [])} 张录音室作品',
        "跨作品差异，不等于时间稳定性", "derived/vibrato_spread#release", rel.get("snapshot_id", ""))

    add("F-stage-scale", "scale", "现场全量", "实测素材",
        s.get("n_materials"), "条", f'{s.get("n_tours")} 个巡次 / {s.get("n_songs")} 首曲目',
        "素材条数不等于场次数：一场可有多个上传或剪辑", "archive_stage_tour#summary", "stage")
    add("F-stage-span", "distribution", "现场全量", "跨度中位",
        s.get("span_median_octaves"), "八度", "排除人耳否决读数（n=682）",
        "含全部读数为 2.73，两值不可混用", "archive_stage_tour#summary", "stage")

    for song in (lv.get("songs") or []):
        vsl = song.get("versions") or []
        ok = [v for v in vsl if v.get("state") == "ok"]
        pend = sum(1 for v in vsl if v.get("state") == "pending")
        exc = sum(1 for v in vsl if v.get("state") == "excluded")
        rng = song.get("low_range_semitones")
        extra = " + ".join(x for x in (f"待判 {pend}" if pend else "", f"排除 {exc}" if exc else "") if x)
        tail = f"（{extra}）" if extra else ""
        sid = f'F-song-{song["song"]}'
        add(sid, "song_versions", song["song"], "版本分布",
            f'登记 {len(vsl)} 个版本，{len(ok)} 个纳入统计{tail}', "",
            f'{song.get("n_tours")} 个巡次',
            "纳入与未纳入分开计，不合并成「全部版本」", "live_versions#songs", "versions")
        if rng is not None:
            add(sid + "-range", "song_range", song["song"], "目标段读数极差",
                round(rng, 2), "半音", f'{len(ok)} 个纳入版本',
                "不同版本调性可能不同，不能当能力对比", "live_versions#low_range_semitones", "versions")

    out = {"schema": "fact_atoms/v1", "count": len(facts), "facts": facts}
    (D / "fact_atoms.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"事实原子 {len(facts)} 条 -> data/fact_atoms.json")
    for f in facts:
        print(f"  {f['id']:28s} {f['subject']}｜{f['metric']}＝{f['value']}{f['unit']}")


if __name__ == "__main__":
    main()
