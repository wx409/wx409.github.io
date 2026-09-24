# -*- coding: utf-8 -*-
"""待人耳确认清单（单一事实源）——把散在两处的待核项汇成一份，并自动切缺失样本。

为什么需要它（2026-09-24）
--------------------------
待听辨事项此前散在：① `data/listening_verdicts.json` 里 verdict 含「待核」的条目；
② `data/archive_long_notes.json → top_flagged`（高音区闸门/同音区存疑被移出榜单的条目）。
而人读清单 `_听辨清单.json` **停在 2026-09-16**，新增待核项（如《当爱已成往事》C5 8.2s）无人知晓。

本脚本做两件事：
  1. 汇总 → `temp\\待听辨清单.md`（人读：条目+状态+样本路径+源音频）+ `data/pending_review.json`（机读）
  2. `--cut` 时为缺样本的条目自动切样本（源音频可从 场次音频/专辑音频 定位时），落 `听辨样本\\待听辨_<日期>\\`

用法：
  python -X utf8 project_b\\build_pending_review.py            # 只出清单
  python -X utf8 project_b\\build_pending_review.py --cut      # 出清单并切缺失样本
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
AUD = Path(r"E:\wx\论文素材_王晰作传\音域分析")
SAMPLES = AUD / "听辨样本"

LEDGER = D / "listening_verdicts.json"
LONGNOTES = D / "archive_long_notes.json"
OUT_MD = SITE / "temp" / "待听辨清单.md"
OUT_JSON = D / "pending_review.json"


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def find_source(song: str, scope: str = "") -> Path | None:
    """按曲名在 场次音频 / 专辑音频 里找源音频（优先混音 wav，其次 mp3/m4a）。"""
    if not song:
        return None
    key = re.sub(r"[（(].*?[)）]", "", song).strip()[:10]
    if not key:
        return None
    roots = [AUD / "场次音频" / "wav", AUD / "专辑音频"]
    roots += sorted(p for p in (AUD / "场次音频").glob("wav_*") if p.is_dir())   # 全部场次批次
    for r in roots:
        if not r.exists():
            continue
        hits = [p for p in r.rglob(f"*{key}*") if p.suffix.lower() in (".wav", ".mp3", ".m4a")]
        if hits:
            return sorted(hits, key=lambda x: (x.suffix.lower() != ".wav", len(str(x))))[0]
    return None


def cut(src: Path, t0: float, dur: float, name: str, outdir: Path) -> Path | None:
    try:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ff = "ffmpeg"
    t0 = float(t0 or 0)
    outdir.mkdir(parents=True, exist_ok=True)
    dst = outdir / f"{name}.mp3"
    ss = max(0.0, t0 - 4)
    ln = float(dur or 8) + 8
    r = subprocess.run([ff, "-v", "error", "-y", "-ss", str(ss), "-t", str(ln), "-i", str(src),
                        "-ac", "2", "-ar", "44100", "-b:a", "192k", str(dst)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return dst if (r.returncode == 0 and dst.exists()) else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut", action="store_true", help="为缺样本的条目自动切样本")
    a = ap.parse_args()

    items = []
    # ① 台账待核
    for i in load(LEDGER).get("items", []):
        if "待核" in str(i.get("verdict")) or "待听辨" in str(i.get("verdict")):
            items.append({
                "source": "台账(listening_verdicts)", "id": i.get("id"), "song": i.get("song"),
                "aspect": i.get("aspect"), "hz": i.get("verdict_hz"), "dur": i.get("dur_s"),
                "t_s": i.get("t_s"), "status": i.get("verdict"),
                "note": str(i.get("verdict_note") or "")[:120], "sample": "",
            })
    # ② 长声榜被移出/待归属
    for x in load(LONGNOTES).get("top_flagged", []):
        items.append({
            "source": "长声闸门(archive_long_notes)", "id": f"LN-{x.get('song')}-{x.get('note')}",
            "song": x.get("song"), "aspect": f"长声 {x.get('note')}", "hz": x.get("hz"),
            "dur": x.get("dur_s"), "t_s": x.get("t_start_s"),
            "status": str(x.get("verdict_conflict") or "")[:80],
            "note": f"来源 {x.get('src')}｜{x.get('where')}", "sample": "",
        })
    # 已终裁的（直接冲突）不再列为待听辨
    items = [x for x in items if "直接冲突" not in x["status"]]
    # 同一曲目 + 同一 Hz（±3%）已有「非王晰」终裁 → 该读数已不进结论，无需再打扰人耳
    _rej = [(str(i.get("song")), float(i.get("verdict_hz") or 0)) for i in load(LEDGER).get("items", [])
            if str(i.get("verdict", "")).startswith("非王晰") and isinstance(i.get("verdict_hz"), (int, float))]

    def superseded(x) -> bool:
        try:
            hz = float(x.get("hz") or 0)
        except (TypeError, ValueError):
            return False
        if not hz:
            return False
        return any(str(x.get("song")) == s0 and abs(hz - h1) / hz <= 0.03 for s0, h1 in _rej)

    _n0 = len(items)
    items = [x for x in items if not superseded(x)]
    if _n0 != len(items):
        print(f"  （{_n0 - len(items)} 条已有否决终裁，无需人耳）")

    outdir = SAMPLES / f"待听辨_{datetime.now():%Y%m%d}"

    def existing_sample(song: str, aspect: str) -> str:
        """磁盘上已有的样本（只看文件名，公开 JSON 不含本地路径）。
        2026-09-24 修：必须「曲名 + 音名」双匹配，否则同曲不同音名会互相顶替。"""
        key = str(song)[:8]
        note = ""
        m = re.search(r"([A-G]#?\d)", str(aspect))
        if m:
            note = m.group(1)
        for d0 in sorted(SAMPLES.glob("待听辨_*"), reverse=True):
            for f in d0.glob("*.mp3"):
                if f.name.startswith(key) and (not note or note in f.name):
                    return f.name
        return ""

    if a.cut:
        cut_n = 0
        for x in items:
            src = find_source(str(x.get("song") or ""))
            if not src:
                x["sample"] = "（源音频未定位，需另行提供）"
                continue
            dst = cut(src, x.get("t_s") or 0, x.get("dur") or 8,
                      f"{x['song']}_{x['aspect']}_{x['hz']}Hz".replace("/", "-")[:60], outdir)
            x["sample"] = dst.name if dst else "（切制失败）"   # 公开 JSON 只存文件名，不含本地路径
            cut_n += 1 if dst else 0
        print(f"切样本 {cut_n} 条 → {outdir}")

    for x in items:
        if not x.get("sample"):
            x["sample"] = existing_sample(str(x.get("song") or ""), str(x.get("aspect") or ""))

    md = [f"# 待人耳确认清单（{datetime.now():%Y-%m-%d %H:%M} 生成）", "",
          f"共 **{len(items)}** 条。数据源：`data/listening_verdicts.json`（台账待核）＋ "
          f"`data/archive_long_notes.json → top_flagged`（长声闸门）。", "",
          "> 处置方式：听完后跑 **操作中心 159（听辨台账回填）** 写回终裁，再跑 **160（定案后重建）**。", ""]
    for i, x in enumerate(items, 1):
        md += [f"## {i}. {x['song']}｜{x['aspect']}｜{x.get('hz')}Hz｜{x.get('dur')}s",
               f"- 状态：{x['status']}",
               f"- 来源：{x['source']}（id={x['id']}）",
               f"- 说明：{x['note']}"]
        if x.get("sample"):
            md.append(f"- **样本**：`{x['sample']}`")
        md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(
        {"generated_at": datetime.now().isoformat(timespec="seconds"), "count": len(items), "items": items},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"待人耳确认 {len(items)} 条 → {OUT_MD.name} / {OUT_JSON.name}")
    for x in items:
        print(f"  · {x['song']}｜{x['aspect']}｜{x.get('hz')}Hz｜{x['status'][:38]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
