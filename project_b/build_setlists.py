# -*- coding: utf-8 -*-
"""生成 59 场巡演完整歌单数据 data/setlists.json
数据源：长表（唯一事实源）+ 补全版本（备注增强）
"""
import json
import re
import glob
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\wx409.github.io")
LONG_TABLE = r"E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx"
SUPPLEMENT_DIR = r"E:\wx\巡演歌单\补全版本"
CITIES_JSON = ROOT / "data" / "cities.json"
OUT = ROOT / "data" / "setlists.json"

TOUR_THEME = {
    "一巡": "Cherish珍晰", "二巡": "2020-2021 个人巡回", "三巡": "图景",
    "四巡": "肆益", "五巡": "吾", "六巡": "回",
}
SUFFIXES = ("收官", "返场", "加场", "首场")


def clean_city(scene: str) -> str:
    city = re.split(r"[（(]", str(scene))[0].strip()
    for s in SUFFIXES:
        if city.endswith(s):
            city = city[: -len(s)]
            break
    return city.strip()


def norm_date(v) -> str:
    """datetime / str -> YYYY-MM-DD"""
    if v is None:
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    m = re.match(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return s[:10]


def load_supplement_notes() -> dict:
    """补全版本 -> {(date, song): note}，仅作备注增强"""
    notes = {}
    for f in sorted(glob.glob(str(Path(SUPPLEMENT_DIR) / "*.xlsx"))):
        if "~$" in f:
            continue
        try:
            xl = pd.ExcelFile(f)
            for sheet in xl.sheet_names:
                df = pd.read_excel(f, sheet_name=sheet)
                # 找曲目列和时间列（兼容 曲目/歌曲名称、时间）
                title_col = next((c for c in df.columns if str(c) in ("曲目", "歌曲名称")), None)
                date_col = next((c for c in df.columns if str(c) in ("时间", "日期")), None)
                note_col = "备注" if "备注" in df.columns else None
                if title_col is None or date_col is None:
                    continue
                for _, r in df.iterrows():
                    title = str(r[title_col]).strip() if pd.notna(r[title_col]) else ""
                    d = norm_date(r[date_col])
                    note = str(r[note_col]).strip() if note_col and pd.notna(r[note_col]) else ""
                    if title and d:
                        key = (d, title)
                        if key not in notes and note:
                            notes[key] = note
        except Exception as e:
            print(f"  [skip] {Path(f).name}: {e}")
    return notes


def main():
    # 1. 长表（唯一事实源）
    df = pd.read_excel(LONG_TABLE, sheet_name="合并长表")
    df = df[df["曲目"].notna() & (df["曲目"].astype(str).str.strip() != "")]
    print(f"长表曲目行: {len(df)}")

    # 2. 补全备注
    supp = load_supplement_notes()
    print(f"补全版本备注条目: {len(supp)}")

    # 3. cities.json venue 映射
    cities = json.loads(CITIES_JSON.read_text(encoding="utf-8"))["cities"]
    venue_by_date = {}
    for node in cities.values():
        for s in node.get("shows", []):
            if s.get("venue"):
                venue_by_date[s["date"]] = s["venue"]

    # 4. 按日期+场次分组
    groups = {}
    for _, r in df.iterrows():
        date = norm_date(r["日期"])
        scene = str(r["场次"]).strip()
        key = (date, scene)
        title_raw = str(r["数据层归一名"]) if pd.notna(r["数据层归一名"]) and str(r["数据层归一名"]).strip() else str(r["曲目"]).strip()
        note = str(r["备注"]).strip() if pd.notna(r["备注"]) else ""
        order = r["场次内序号"]
        try:
            order = int(float(order))
        except (ValueError, TypeError):
            order = 0
        if not note:
            note = supp.get((date, title_raw), "")
        groups.setdefault(key, []).append({"order": order, "title": title_raw, "note": note})

    # 5. 组装
    setlists = {}
    for (date, scene), songs in groups.items():
        songs.sort(key=lambda x: x["order"])
        tour_raw = ""
        # 找该场巡次（同组行里取）
        for _, r in df[(df["日期"].astype(str).str[:10] == date) & (df["场次"].astype(str).str.strip() == scene)].iterrows():
            tour_raw = str(r["巡次"])
            break
        m = re.match(r"^(一巡|二巡|三巡|四巡|五巡|六巡)", tour_raw)
        tour = m.group(1) if m else tour_raw[:2]
        setlists[date] = {
            "date": date,
            "scene": scene,
            "city": clean_city(scene),
            "tour": tour,
            "theme": TOUR_THEME.get(tour, ""),
            "venue": venue_by_date.get(date),
            "songs": songs,
        }

    out = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "show_count": len(setlists),
        "setlists": {k: setlists[k] for k in sorted(setlists)},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # 6. 统计
    total = sum(len(v["songs"]) for v in setlists.values())
    by_tour = {}
    for v in setlists.values():
        by_tour[v["tour"]] = by_tour.get(v["tour"], 0) + 1
    print(f"场次数: {len(setlists)} | 总曲目: {total}")
    print("每巡场次:", by_tour)
    no_venue = [k for k, v in setlists.items() if not v["venue"]]
    print(f"缺venue场次: {len(no_venue)}", no_venue[:5])
    # 多听有益
    for k, v in setlists.items():
        for s in v["songs"]:
            if "多听有益" in s["title"]:
                print(f"多听有益: {k} {v['scene']}")
    print(f"[OK] 已生成 -> {OUT}")


if __name__ == "__main__":
    main()
