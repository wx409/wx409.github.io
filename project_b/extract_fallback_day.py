# -*- coding: utf-8 -*-
"""extract_fallback_day.py —— 缺失日期的"备用数据源"提取（守护进程合并表 → 可回填的日档案）

背景
----
指数长表用「日档案 D 的昨日音乐指数 = D-1 官方值」的口径（2026-09-10 起已修正映射）。
若某天的日档案缺失（如 2026-09-09 因夜间停摆未生成），则该天对应前一日（2026-09-08）的
**官方值**在别处都拿不到 —— 只有那份文件里有。

本脚本提供**备用路径**：从守护进程自己的合并快照
（`E:\\wx\\index_records\\raw_archive\\raw_latest.xlsx`）里取出该日的 `current_index`
（= 当日 23:5x 的**准终值**，非官方定稿值），并可选地写成一个"次日"日档案，
让修正后的映射把它归位到正确日期。

⚠️ 口径提示：这是**准终值**，与官方值通常相差 0~7 点（中位 2.0、P90 7.0，见影子验证报告）。
   仅在"找不到真实日档案"时使用，且必须在站点/论文中标注来源与口径。

用法：
    # 1) 只分析 + 出 JSON（写 temp\\，不碰 E:\\）
    python project_b\\extract_fallback_day.py --date 2026-09-08

    # 2) 生成"次日"日档案（写入 E:\\wx\\指数vs\\，被 00_build_matrix 的 indexvs 兜底源读取）
    python project_b\\extract_fallback_day.py --date 2026-09-08 --install-as-day 2026-09-09

    说明：indexvs 源优先级低于 addon/download —— 你之后把**真实**的 2026.09.09.xlsx
    拷进增补数据库后，00_build_matrix 的 first-wins 会自动采用真实文件，备用文件自动失效。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
RAW_DIR = Path(r"E:\wx\index_records\raw_archive")
INDEXVS = Path(r"E:\wx\指数vs")
LONG_CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")


def newest_raw() -> Path | None:
    if not RAW_DIR.is_dir():
        return None
    files = sorted(RAW_DIR.glob("raw_*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def extract(day: dt.date) -> tuple[dict[str, float], dict]:
    raw = newest_raw()
    if raw is None:
        return {}, {"error": "raw_archive 目录不存在或无快照"}
    usecols = ["song_name", "data_date", "yesterday_index", "current_index", "listeners", "display_name"]
    df = pd.read_excel(raw, usecols=lambda c: c in usecols)
    df["data_date"] = pd.to_datetime(df["data_date"]).dt.strftime("%Y-%m-%d")
    sub = df[df["data_date"] == day.isoformat()].copy()
    sub = sub[sub["current_index"].notna()]
    vals: dict[str, float] = {}
    for _, r in sub.iterrows():
        nm = str(r.get("display_name") or r.get("song_name") or "").strip()
        if not nm or nm in ("nan", "None"):
            continue
        try:
            v = float(r["current_index"])
        except Exception:
            continue
        if v > 0:
            vals.setdefault(nm, v)
    info = {"raw_file": raw.name, "raw_mtime": dt.datetime.fromtimestamp(raw.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            "rows_for_day": int(len(sub)), "songs_with_value": len(vals),
            "mean": round(sum(vals.values()) / len(vals), 1) if vals else None}
    return vals, info


def neighbor_reference(day: dt.date) -> dict:
    """用长表里相邻日的覆盖面做参照（判断备用数据是否够用）。"""
    out = {}
    if not LONG_CSV.exists():
        return out
    df = pd.read_csv(LONG_CSV, encoding="utf-8-sig")
    df["date"] = df["date"].astype(str)
    for k in (-2, -1, 1, 2):
        d = (day + dt.timedelta(days=k)).isoformat()
        sub = df[df["date"] == d]
        if len(sub):
            out[d] = {"songs": int(len(sub)), "mean": round(float(sub["index"].mean()), 1)}
    return out


def install_dayfile(day: dt.date, as_day: dt.date, vals: dict[str, float]) -> Path:
    """把备用值写成"次日"日档案，使修正映射把它归位到 day。"""
    INDEXVS.mkdir(parents=True, exist_ok=True)
    out = INDEXVS / ("%s_0900_fallback.xlsx" % as_day.strftime("%Y.%m.%d"))
    rows = [{"序号": i + 1, "歌曲名称": nm, "演唱者": "王晰",
             "昨日音乐指数": v, "音乐指数": None, "当前收听人数": None,
             "状态": "备用:守护进程合并表准终值(非官方定稿)"}
            for i, (nm, v) in enumerate(sorted(vals.items(), key=lambda kv: -kv[1]))]
    pd.DataFrame(rows).to_excel(out, index=False)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="缺哪一天的值（如 2026-09-08）")
    ap.add_argument("--install-as-day", default=None,
                    help="写成哪一天的文件名（通常是缺失日档案的次日，如 2026-09-09）；缺省=只出 JSON")
    args = ap.parse_args()

    day = dt.date.fromisoformat(args.date)
    print("=" * 70)
    print("备用数据源提取：%s（来自守护进程合并快照的当日准终值）" % day.isoformat())
    print("=" * 70)

    vals, info = extract(day)
    print("快照: %s（%s）" % (info.get("raw_file"), info.get("raw_mtime")))
    print("该日有值歌曲: %s 首｜均值 %s" % (info.get("songs_with_value"), info.get("mean")))
    ref = neighbor_reference(day)
    for d, r in sorted(ref.items()):
        print("  参照 %s: %d 首 / 均值 %.1f" % (d, r["songs"], r["mean"]))

    if not vals:
        print("[X] 该日在快照里没有任何 current_index —— 无法提供备用值（可能当天各批次都没跑成）")
        return 1

    TEMP.mkdir(exist_ok=True)
    out_json = TEMP / ("备用值_%s.json" % day.strftime("%Y%m%d"))
    payload = {"date": day.isoformat(), "source": info,
               "口径": "守护进程合并表当日准终值（非官方定稿值；与官方值差中位 2.0 / P90 7.0）",
               "values": vals,
               "邻日参照": ref}
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[OK] 备用值 JSON: %s" % out_json)

    if args.install_as_day:
        as_day = dt.date.fromisoformat(args.install_as_day)
        p = install_dayfile(day, as_day, vals)
        print("[OK] 已写日档案: %s" % p)
        print("     修正映射下它会归位到 %s；真实 addon 文件优先级更高，拷回后自动覆盖。"
              % day.isoformat())
        print("     改完请重跑: python project_b\\rebuild_after_backfill.py --only matrix,baseline")
    else:
        print("[i] 未写入 E:\\（加 --install-as-day 2026-09-09 才会生成日档案）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
