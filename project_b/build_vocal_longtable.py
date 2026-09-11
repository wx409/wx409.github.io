# -*- coding: utf-8 -*-
"""声学数据统一长表 + 复核台账（⑦ 减法：4 套 JSON + 3 处复核状态 → 1 长表 + 1 台账）。

问题：声学数据现在是"按项目分叉"的 4 套 JSON——
  archive_vocal.json（十曲精测）· archive_vocal_albums.json（72 曲录音室）
  archive_stage.json（他人主导舞台）· archive_stage_tour.json（巡演现场）
复核状态又散在 3 处：A3复核交付表.json · archive_lowc_verify.json · album_verify_status.json
→ 每次要跨版本比较（同曲 live↔录音室、跨巡对比、待复核闭环）都得再写一个脚本。

本脚本把它们归一成两张表（**只读旧源、不改旧文件**）：
  data/vocal_measurements.json  一行 = 一首歌×一个版本（含 layer/tour/city/date/source_ref/metrics/verify/provenance）
  data/verify_ledger.json       一行 = 一次复核判定（含 yin/crepe/state/how/source），全站唯一复核台账

用法：
  python -X utf8 project_b/build_vocal_longtable.py            # 构建（幂等）
  python -X utf8 project_b/build_vocal_longtable.py --check    # 只校验长表与旧源一致（CI/每日把关）
  python -X utf8 project_b/build_vocal_longtable.py --query "让她降落"
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
ANA = Path(r"E:\wx\论文素材_王晰作传\音域分析")

OUT_MEAS = DATA / "vocal_measurements.json"
OUT_LEDGER = DATA / "verify_ledger.json"

LAYERS = {
    "studio_album": "录音室专辑（QQ音乐 320k）",
    "single": "网易云独有单曲/OST",
    "precision": "十曲精测（含现场个案）",
    "stage_other": "他人主导舞台（综艺/晚会/商演/饭拍）",
    "tour_live": "王晰主导巡演现场",
}
# 旧源行级复核状态 → 台账统一状态
STATE_MAP = [
    ("✅", "双引擎一致"), ("🟡", "已取证"), ("⚪", "待复核"), ("✕", "次谐波错误"),
    ("YIN_OK", "已取证"), ("YIN_SUBHARMONIC", "次谐波错误"), ("UNCLEAR", "待复核"),
    ("已核验", "已核验"), ("参考", "参考"), ("未复核", "未复核"), ("待核", "待复核"),
]


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


_REVIEW = None


def low_review() -> dict:
    """低音读数终裁表（音域分析\\轨迹\\低音复核_判定_*.json，取最新一份）。

    判据：原始混音谐波列完整性 + 同场同刻多源一致（工具 轨迹/低音复核_谐波列.py）。
    两引擎对「缺基频」刺激会同向误锁，故 A3 表的「双引擎一致/已取证」不能单独作为定论。
    """
    global _REVIEW
    if _REVIEW is None:
        files = sorted((ANA / "轨迹").glob("低音复核_判定_*.json"))
        _REVIEW = {}
        if files:
            for v in (load(files[-1]).get("verdicts") or []):
                if v.get("tag"):
                    _REVIEW[str(v["tag"])] = v
    return _REVIEW


def apply_review(entry: dict) -> dict:
    rv = low_review().get(str(entry.get("key")))
    if not rv:
        return entry
    verdict = str(rv.get("verdict") or "")
    if verdict == "不成立":
        entry["state"] = "待复核"
        entry["how"] = "谐波列复核未通过（基频缺失 / 与同场另一路源相差整数倍）"
    elif verdict == "待核":
        entry["state"] = "待复核"
        entry["how"] = "极值未过门槛（音符 ≥0.2s），改列待复核"
    else:
        entry["state"] = "谐波列复核通过"
        entry["how"] = "原始混音谐波列完整（1f0–8f0 逐级在列）＋同场同刻多源一致"
    return entry


def norm_state(s: str) -> str:
    s = str(s or "").strip()
    for k, v in STATE_MAP:
        if s.startswith(k) or k in s:
            return v
    return s or "未复核"


def m(**kw) -> dict:
    return {k: v for k, v in kw.items() if v is not None}


def rows_from_albums() -> list[dict]:
    out = []
    for s in (load(DATA / "archive_vocal_albums.json").get("songs") or []):
        out.append({
            "id": f"studio_album|{s.get('title')}|{s.get('album')}",
            "song": s.get("title"), "version": f"录音室《{s.get('album')}》", "layer": "studio_album",
            "album": s.get("album"), "source_ref": s.get("album"),
            "metrics": m(low_note=s.get("low"), low_hz=s.get("low_hz"), high_note=s.get("high"),
                         high_hz=s.get("high_hz"), span_octaves=s.get("span_octaves"),
                         stability_cents=s.get("stability_cents"), intonation_cents=s.get("intonation_cents"),
                         vibrato_hz=s.get("vibrato_hz"), vibrato_cents=s.get("vibrato_cents"),
                         density_per_s=s.get("density"), hnr_db=s.get("hnr_db")),
            "verify": {"state": "未复核"},
            "provenance": {"measured_by": "批量专辑音域", "legacy": "archive_vocal_albums.json"},
        })
    return out


def rows_from_precision() -> list[dict]:
    out = []
    for s in (load(DATA / "archive_vocal.json").get("songs") or []):
        name = s.get("name")
        out.append({
            "id": f"precision|{name}|stable",
            "song": name, "version": "十曲精测·稳定音", "layer": "precision",
            "source_ref": s.get("source"),
            "metrics": m(low_note=s.get("stable_note"), low_hz=s.get("stable_hz"),
                         span_octaves=None, stability_cents=s.get("stability_cents_median"),
                         vibrato_hz=s.get("vibrato_rate_hz_median"),
                         vibrato_cents=s.get("vibrato_extent_cents_median"),
                         hnr_db=s.get("stable_hnr_db"), duration_s=s.get("stable_dur_s")),
            "verify": {"state": norm_state(s.get("stable_status") or s.get("stable_verified")),
                       "evidence": s.get("stable_evidence")},
            "provenance": {"measured_by": "复核十曲严格口径", "legacy": "archive_vocal.json"},
        })
        if s.get("reach_hz"):
            out.append({
                "id": f"precision|{name}|reach",
                "song": name, "version": "十曲精测·触达音", "layer": "precision",
                "source_ref": s.get("source"),
                "metrics": m(low_note=s.get("reach_note"), low_hz=s.get("reach_hz"),
                             duration_s=s.get("reach_duration")),
                "verify": {"state": norm_state(s.get("reach_status")), "engine": s.get("reach_engine")},
                "provenance": {"measured_by": "复核十曲严格口径", "legacy": "archive_vocal.json",
                               "note": "触达音不作能力依据"},
            })
        for v in (s.get("versions") or []):
            scene = str(v.get("场次") or "")
            if not scene or "录音室" in scene:
                continue
            if "排除" in str(v.get("状态") or ""):        # 混剪等被排除的素材不进长表
                continue
            note = _note_of(v.get("稳定音"))
            if not note:                                  # 无音名 = 未测/待测，不是测量结果
                continue
            hz = _hz_of(v.get("稳定音"), str(v.get("BV") or ""), scene, note)
            out.append({
                "id": f"precision|{name}|{scene}",
                "song": name, "version": scene, "layer": "tour_live" if any(
                    k in scene for k in ("巡", "肆益", "图景", "吾", "回")) else "stage_other",
                "source_ref": v.get("BV"), "date": v.get("日期"),
                "metrics": m(low_note=note, low_hz=hz),
                "verify": {"state": norm_state(v.get("可信度"))},
                "provenance": {"measured_by": "十曲精测版本表", "legacy": "archive_vocal.json#versions",
                               "quality": v.get("素材质量")},
            })
    return out


def _note_of(text) -> str | None:
    import re
    mt = re.search(r"([A-G]#?\d)", str(text or ""))
    return mt.group(1) if mt else None


def _hz_of(text, bv: str = "", scene: str = "", note: str = "") -> float | None:
    """从「稳定音」文本取 Hz：优先小数（真实读数 63.4/74.9/111.6），否则按 BV/音名/场次回查 b1_reproduction。"""
    import re
    mt = re.search(r"(\d+\.\d+)", str(text or ""))
    if mt:
        return float(mt.group(1))
    repro = load(DATA / "archive_vocal.json").get("b1_reproduction") or []
    for b in repro:
        if bv and bv == str(b.get("source") or ""):
            return b.get("hz")
    for b in repro:                                  # 音名一致优先（B1/D2/A2 唯一性强）
        if note and note == str(b.get("note") or ""):
            return b.get("hz")
    best, score = None, 0
    for b in repro:
        s = _lcs(scene, str(b.get("version") or ""))
        if s > score:
            best, score = b, s
    return best.get("hz") if best is not None and score >= 3 else None


def _lcs(a: str, b: str) -> int:
    """最长公共子串长度（用于把「四巡 直拍」对上「四巡现场直拍」）。"""
    a, b = str(a or ""), str(b or "")
    best = 0
    for i in range(len(a)):
        for j in range(len(b)):
            k = 0
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            best = max(best, k)
    return best


def rows_from_stage() -> list[dict]:
    out = []
    for it in (load(DATA / "archive_stage.json").get("items") or []):
        # 舞台素材只有 B站标题：优先取《…》里的曲名，取不到再退化为截断标题
        title = str(it.get("title") or "")
        mt = re.search(r"《([^》]{1,24})》", title)
        song = (mt.group(1) if mt else (it.get("song") or title[:24])).strip()
        out.append({
            "id": f"stage_other|{it.get('bvid')}",
            "song": song,
            "version": title[:40], "layer": "stage_other",
            "source_ref": it.get("bvid"), "category": it.get("cat"),
            "metrics": m(low_note=it.get("low"), low_hz=it.get("low_hz"), high_note=it.get("high"),
                         high_hz=it.get("high_hz"), span_octaves=it.get("span"),
                         stability_cents=it.get("stability"), density_per_s=it.get("density"),
                         vibrato_hz=it.get("vibrato_hz"), vibrato_cents=it.get("vibrato_cents")),
            "verify": {"state": "未复核"},
            "provenance": {"measured_by": "生成他人主导报告", "legacy": "archive_stage.json"},
        })
    return out


def rows_from_tour() -> list[dict]:
    out = []
    for r in (load(DATA / "archive_stage_tour.json").get("rows") or []):
        out.append({
            "id": f"tour_live|{r.get('song')}|{r.get('tag')}",
            "song": r.get("song"), "version": r.get("tag"), "layer": "tour_live",
            "tour": r.get("tour"), "city": r.get("city"), "date": r.get("date"),
            "source_ref": r.get("bv"), "measure_route": r.get("source_layer"),
            "metrics": m(low_note=r.get("low_note"), low_hz=r.get("low_hz"), high_note=r.get("high_note"),
                         high_hz=r.get("high_hz"), span_octaves=r.get("span_octaves"),
                         stability_cents=r.get("stability_cents"), intonation_cents=r.get("intonation_cents"),
                         vibrato_hz=r.get("vibrato_hz"), vibrato_cents=r.get("vibrato_cents"),
                         density_per_s=r.get("density_per_s"), hnr_db=r.get("hnr_db"),
                         duration_s=r.get("duration_s")),
            "verify": {"state": norm_state(r.get("a3_final_note")),
                       "engines": m(yin_hz=r.get("a3_yin_hz"), crepe_hz=r.get("a3_crepe_hz")),
                       "raw_state": r.get("a3_state")},
            "provenance": {"measured_by": r.get("source_layer") or "场次音频实测",
                           "legacy": "archive_stage_tour.json", "bandwidth_kbps": r.get("bandwidth_kbps")},
        })
    return out


def ledger_entries() -> list[dict]:
    out = []
    for r in (load(ANA / "轨迹" / "A3复核交付表.json").get("rows") or []):
        crepe = r.get("crepe") or {}
        out.append({
            "scope": "stage", "key": r.get("file"), "kind": r.get("kind"),
            "yin_hz": r.get("yin_hz"), "crepe_hz": r.get("crepe_ref") or (list(crepe.values())[0] if crepe else None),
            "state": norm_state(r.get("final") or r.get("state")),
            "how": str(r.get("how") or "")[:120], "source": "A3复核交付表",
            "prominence_db": r.get("f0_prominence_db"), "coverage": {"yin": r.get("coverage_yin"), "crepe": r.get("coverage_crepe")},
        })
    for r in (load(DATA / "archive_lowc_verify.json").get("rows") or []):
        out.append({
            "scope": "studio", "key": f"{r.get('album')}·{r.get('name')}", "kind": "低音候选",
            "yin_hz": r.get("yin_hz"), "crepe_hz": r.get("crepe_low_hz"),
            "state": norm_state(r.get("verdict") or r.get("state") or r.get("note")),
            "how": "LowC 谐波列复核（E1/E2/E3/E4 + CREPE）", "source": "archive_lowc_verify",
        })
    for s in (load(DATA / "album_verify_status.json").get("songs") or []):
        out.append({
            "scope": "studio", "key": s.get("title"), "kind": "曲目终裁",
            "yin_hz": None, "crepe_hz": None, "state": norm_state(s.get("status")),
            "how": str(s.get("how") or "")[:120], "source": "album_verify_status",
        })
    return [apply_review(e) for e in out]


def rows_from_singles() -> list[dict]:
    """网易云独有曲目（单曲/OST）实测 → single 层。
    数据源：音域分析\\网易云独有\\音频_汇总.json（由 project_b/netease_extra_songs.py 取源实测产出）。"""
    p = ANA / "网易云独有" / "音频_汇总.json"
    if not p.exists():
        return []
    data = load(p, {}) or {}
    out = []
    for s in data.get("songs") or []:
        low = s.get("low_stable") or {}
        high = s.get("high_stable") or {}
        if not low.get("hz"):
            continue
        out.append({
            "id": f"single|{s.get('title')}",
            "song": s.get("title"), "version": "网易云独有·录音室", "layer": "single",
            "source_ref": f"netease:{s.get('title')}",
            "metrics": m(low_note=low.get("note"), low_hz=low.get("hz"),
                         high_note=high.get("note"), high_hz=high.get("hz"),
                         span_octaves=s.get("span_octaves"),
                         stability_cents=s.get("stability_cents_median"),
                         intonation_cents=s.get("intonation_cents_median"),
                         vibrato_hz=s.get("vibrato_rate_hz_median"),
                         vibrato_cents=s.get("vibrato_extent_cents_median"),
                         density_per_s=s.get("note_density_per_s"),
                         hnr_db=s.get("hnr_db_median")),
            "verify": {"state": "未复核"},
            "provenance": {"measured_by": "批量专辑音域（网易云取源）", "legacy": "网易云独有/音频_汇总.json"},
        })
    # 追加：专辑音域汇总.json 中**不属于 8 张录音室专辑**的条目（OST/单曲，QQ 源补录）→ 同归 single 层。
    # 排除「舞台对照·QQ官方版」与标题含 Live/现场 的条目（那属于现场/舞台层）。
    alb = load(DATA / "albums.json", {}) or {}
    studio = {str(a.get("name")) for a in (alb.get("albums") or []) if a.get("name")}
    seen = {str(r.get("song")) for r in out}
    for s in (load(ANA / "专辑音域汇总.json", {}) or {}).get("songs") or []:
        album = str(s.get("album") or "")
        title = str(s.get("title") or "")
        low = s.get("low_stable") or {}
        if not title or not low.get("hz") or album in studio or title in seen:
            continue
        if "舞台对照" in album or re.search(r"\(live\)|（live）|现场", title, re.I):
            continue
        high = s.get("high_stable") or {}
        seen.add(title)
        out.append({
            "id": f"single|{title}",
            "song": title, "version": f"录音室·单曲/OST（{album[:16]}）", "layer": "single",
            "source_ref": album,
            "metrics": m(low_note=low.get("note"), low_hz=low.get("hz"),
                         high_note=high.get("note"), high_hz=high.get("hz"),
                         span_octaves=s.get("span_octaves"),
                         stability_cents=s.get("stability_cents_median"),
                         intonation_cents=s.get("intonation_cents_median"),
                         vibrato_hz=s.get("vibrato_rate_hz_median"),
                         vibrato_cents=s.get("vibrato_extent_cents_median"),
                         density_per_s=s.get("note_density_per_s"),
                         hnr_db=s.get("hnr_db_median")),
            "verify": {"state": "未复核"},
            "provenance": {"measured_by": "批量专辑音域（QQ 源 OST/单曲）", "legacy": "专辑音域汇总.json"},
        })
    return out


def build() -> dict:
    rows = (rows_from_albums() + rows_from_precision() + rows_from_stage()
            + rows_from_tour() + rows_from_singles())
    ledger = ledger_entries()
    by_layer, by_verify = {}, {}
    for r in rows:
        by_layer[r["layer"]] = by_layer.get(r["layer"], 0) + 1
        st = r["verify"].get("state") or "未复核"
        by_verify[st] = by_verify.get(st, 0) + 1
    meas = {
        "schema": 1, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": "声学测量统一长表：一行 = 一首歌 × 一个版本。旧 4 套 JSON 仍是页面视图，本表供跨版本查询与统计",
        "layers": LAYERS,
        "counts": {"total": len(rows), "by_layer": by_layer, "by_verify": by_verify,
                   "songs": len({r["song"] for r in rows if r.get("song")})},
        "rows": rows,
    }
    lg = {
        "schema": 1, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": "全站声学复核台账（A3 终裁 + LowC 复核 + 专辑层状态 三源合一）；待复核项不作能力依据",
        "counts": {k: sum(1 for e in ledger if e["state"] == k) for k in {e["state"] for e in ledger}},
        "entries": ledger,
    }
    return {"meas": meas, "ledger": lg, "rows": rows, "ledger_entries": ledger}


def check(doc: dict) -> int:
    """校验长表与旧源一致：按来源逐一对账 + 关键指标抽查。"""
    problems = []
    legacy = {
        "archive_vocal_albums.json": len(load(DATA / "archive_vocal_albums.json").get("songs") or []),
        "archive_stage.json": len(load(DATA / "archive_stage.json").get("items") or []),
        "archive_stage_tour.json": len(load(DATA / "archive_stage_tour.json").get("rows") or []),
        "archive_vocal.json": len(load(DATA / "archive_vocal.json").get("songs") or []),
    }
    for f, want in legacy.items():
        got = sum(1 for r in doc["rows"] if str((r.get("provenance") or {}).get("legacy") or "").startswith(f))
        if f == "archive_vocal.json":
            if got < want:
                problems.append(f"{f} 派生行数不足：长表 {got} vs 旧源 {want}（每曲至少 1 行稳定音）")
        elif got != want:
            problems.append(f"{f} 行数不一致：长表 {got} vs 旧源 {want}")
    for s in (load(DATA / "archive_vocal_albums.json").get("songs") or []):
        hit = next((r for r in doc["rows"] if r["id"] == f"studio_album|{s.get('title')}|{s.get('album')}"), None)
        if not hit or hit["metrics"].get("low_hz") != s.get("low_hz"):
            problems.append(f"录音室层指标不一致：{s.get('title')}")
    for r in (load(DATA / "archive_stage_tour.json").get("rows") or []):
        hit = next((x for x in doc["rows"] if x["id"] == f"tour_live|{r.get('song')}|{r.get('tag')}"), None)
        if not hit or hit["metrics"].get("low_hz") != r.get("low_hz"):
            problems.append(f"巡演层指标不一致：{r.get('tag')}")
    if problems:
        print(f"结论：长表与旧源不一致 {len(problems)} 处")
        for p in problems[:10]:
            print("   ✗", p)
        return 1
    print(f"结论：长表与旧源一致 ✅（{doc['meas']['counts']['total']} 行 / "
          f"层 {doc['meas']['counts']['by_layer']} / 复核台账 {len(doc['ledger_entries'])} 条）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--query", default=None)
    a = ap.parse_args()
    doc = build()
    if a.query:
        key = a.query
        hits = [r for r in doc["rows"] if key in str(r.get("song") or "") or key in str(r.get("version") or "")]
        print(f"== 查询「{key}」命中 {len(hits)} 行")
        for r in hits:
            mm = r["metrics"]
            print(f"   {r['layer']:<12} {r['song']:<10} {r['version'][:26]:<28} "
                  f"{mm.get('low_note') or '—':<5}{mm.get('low_hz') or '—':<8} {r['verify'].get('state')}")
        return 0
    if a.check:
        return check(doc)
    OUT_MEAS.write_text(json.dumps(doc["meas"], ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_LEDGER.write_text(json.dumps(doc["ledger"], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {OUT_MEAS.name}｜{doc['meas']['counts']['total']} 行｜层 {doc['meas']['counts']['by_layer']}"
          f"｜同名曲 {doc['meas']['counts']['songs']} 首")
    print(f"[OK] {OUT_LEDGER.name}｜{len(doc['ledger_entries'])} 条｜状态 {doc['ledger']['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
