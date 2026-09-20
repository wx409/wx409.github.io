# -*- coding: utf-8 -*-
"""翻唱/选曲价值分析引擎（把「没有指数数据的 222 首」变成可引用结论）。

五个角度（全部读现有数据，不新采）：
  A 自有曲 vs 翻唱曲 · 舞台效应 DiD（自己给自己当对照：同人同期同场地，只差"是否他的作品"）
  B 选曲指纹（跨巡保留率 / 每巡换血率 / 看家曲与一次性曲目结构）
  C 同曲多版本方差（他每场是不是同一个水平：版本间离散 + 组内/组间分解）
  D 音区适配（翻唱曲 vs 自有曲 的音区落点差异；含女声原唱翻唱专项）
  E 语言/风格跨度（中/英/民族·戏曲 三组的音域与音区差异）
产出：data/cover_analysis.json ＋ temp/翻唱价值分析.md
用法: python -X utf8 project_b\\build_cover_analysis.py
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LONG_CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
RNG = np.random.default_rng(20260920)

# 女声原唱翻唱（人工小表，仅用于 D 的专项；标"手工"，不做全量推断）
FEMALE_ORIG = {"橄榄树": "齐豫", "心动": "陈洁仪", "玫瑰人生（La Vie en Rose）": "Edith Piaf",
               "女人花＋水中花": "梅艳芳", "让她降落": "张惠妹", "亲密爱人": "梅艳芳",
               "月半弯": "陈坤/张学友（男）", "再见我的爱（Goodbye My Love）": "邓丽君"}
ETHNIC = ("嘎达梅林", "海然海然", "敕勒歌", "茉莉花", "小河淌水", "沂蒙", "花儿为什么这样红", "乌兰巴托",
          "我的太阳", "桑塔露琪亚", "玛依拉", "阿拉木汗")


def load(name, default=None):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def norm(t):
    t = str(t or "").strip().lower()
    t = re.sub(r"[（(].*?[)）]", "", t)
    return re.sub(r"[\s·・,，、'’\"“”!！?？.。\-—_]+", "", t)


def song_matrix():
    df = pd.read_csv(LONG_CSV, encoding="utf-8-sig")
    df.columns = [c.strip().lower() for c in df.columns]
    d = [c for c in df.columns if "date" in c][0]
    s = [c for c in df.columns if "song" in c or "name" in c][0]
    i = [c for c in df.columns if "index" in c][0]
    df = df[[d, s, i]].rename(columns={d: "d", s: "song", i: "index"})
    df["d"] = pd.to_datetime(df["d"], errors="coerce")
    df["index"] = pd.to_numeric(df["index"].astype(str).str.replace(",", ""), errors="coerce")
    df = df.dropna().sort_values(["song", "d"])
    df["rel"] = df["index"] / df.groupby("song")["index"].transform(
        lambda x: x.rolling(91, center=True, min_periods=30).median())
    return df.pivot_table(index="d", columns="song", values="rel", aggfunc="median")


def did_own_vs_cover(mat, setlists, own_norm, win=30, n_placebo=300):
    """A：每场演出里，自有曲（受处理）vs 翻唱曲（对照）在演出前后 30 天的相对变化差。"""
    di = pd.DatetimeIndex(mat.index)
    m = np.log(np.clip(mat.to_numpy(dtype=float), 0.2, 5.0))
    cols = {str(c).strip(): k for k, c in enumerate(mat.columns)}
    rows = []
    for date, v in sorted(setlists.items()):
        idx = di.searchsorted(pd.Timestamp(date))
        if idx < win or idx + win >= len(m):
            continue
        titles = [s.get("title") for s in v.get("songs", []) if s.get("title")]
        hits = [cols[t] for t in titles if t in cols]
        if len(hits) < 2:
            continue
        own_hits = [cols[t] for t in titles if t in cols and norm(t) in own_norm]
        cov_hits = [cols[t] for t in titles if t in cols and norm(t) not in own_norm]
        if len(own_hits) < 2 or len(cov_hits) < 2:      # 两侧都要 ≥2 首，否则中位不可估
            continue
        pre = np.nanmedian(m[idx - win:idx, :], axis=0)
        post = np.nanmedian(m[idx:idx + win, :], axis=0)
        d = post - pre
        t_delta = float(np.nanmedian(d[own_hits]))
        c_delta = float(np.nanmedian(d[cov_hits]))
        if not (np.isfinite(t_delta) and np.isfinite(c_delta)):   # 剔除首末无数据的曲目
            continue
        did = t_delta - c_delta
        pool = [k for k in hits if np.isfinite(d[k])]
        if len(pool) < 4:
            continue
        null = []
        for _ in range(n_placebo):
            pick = list(RNG.choice(pool, size=len(own_hits), replace=False))
            rest = [k for k in pool if k not in pick]
            if not rest:
                break
            null.append(float(np.nanmedian(d[pick])) - float(np.nanmedian(d[rest])))
        p = float((np.abs(np.array(null)) >= abs(did)).mean()) if null else np.nan
        if not np.isfinite(p):
            continue
        rows.append({"date": date, "tour": v.get("tour", ""), "city": v.get("city", ""),
                     "own_n": len(own_hits), "cover_n": len(cov_hits),
                     "own_pct": round((np.exp(t_delta) - 1) * 100, 1),
                     "cover_pct": round((np.exp(c_delta) - 1) * 100, 1),
                     "did_pct": round((np.exp(did) - 1) * 100, 1), "placebo_p": round(p, 3)})
    return rows


def main() -> int:
    sl = load("setlists.json").get("setlists", {})
    cat = load("cover_catalog.json")
    songs = cat.get("songs", [])
    own_norm = {norm(s["title"]) for s in songs if s.get("own")}
    tour = load("archive_stage_tour.json")
    rows = tour.get("rows", [])

    out = {"generated_at": datetime.now().isoformat(timespec="seconds"), "stat": cat.get("stat", {})}

    # ---------- B 选曲指纹 ----------
    by_tour = defaultdict(lambda: {"songs": set(), "new": set()})
    seen_all = set()
    for date, v in sorted(sl.items()):
        t = v.get("tour") or "未标"
        for s in v.get("songs", []):
            ti = s.get("title")
            if not ti:
                continue
            by_tour[t]["songs"].add(ti)
    # 跨巡保留率：一巡唱过、后续巡次仍唱
    order = [t for t in ["一巡", "二巡", "三巡", "四巡", "五巡", "六巡"] if t in by_tour]
    keep = []
    for i in range(1, len(order)):
        prev = by_tour[order[i - 1]]["songs"]
        cur = by_tour[order[i]]["songs"]
        keep.append({"from": order[i - 1], "to": order[i], "prev_n": len(prev), "cur_n": len(cur),
                     "retained": len(prev & cur), "retain_rate": round(len(prev & cur) / max(len(prev), 1), 3),
                     "new": len(cur - prev), "new_rate": round(len(cur - prev) / max(len(cur), 1), 3)})
    tiers = cat.get("stat", {}).get("tiers", {})
    out["fingerprint"] = {"tours": {t: len(v["songs"]) for t, v in by_tour.items()},
                          "tour_order": order, "retention": keep, "tiers": tiers,
                          "once_only": sum(1 for s in songs if s["times"] == 1),
                          "home_songs": sum(1 for s in songs if s["times"] >= 10),
                          "once_list": [s["title"] for s in songs if s["times"] == 1][:60]}

    # ---------- C 同曲多版本方差 ----------
    per = defaultdict(list)
    for r in rows:
        song, lo, hi = r.get("song"), r.get("low_hz"), r.get("high_hz")
        if song and lo:
            per[song].append((float(lo), float(hi) if hi else np.nan, r.get("tag"), str(r.get("date"))[:10]))
    multi = {k: v for k, v in per.items() if len(v) >= 3}
    c_stats = []
    for k, v in sorted(multi.items(), key=lambda kv: -len(kv[1])):
        los = np.array([x[0] for x in v])
        his = np.array([x[1] for x in v if not np.isnan(x[1])])
        c_stats.append({"song": k, "versions": len(v), "low_median": round(float(np.median(los)), 1),
                        "low_iqr": round(float(np.percentile(los, 75) - np.percentile(los, 25)), 1),
                        "low_range": round(float(los.max() - los.min()), 1),
                        "high_median": round(float(np.median(his)), 1) if len(his) else None,
                        "low_cv": round(float(np.std(los) / np.mean(los)), 4)})
    all_low_cv = [c["low_cv"] for c in c_stats]
    out["multi_version"] = {"songs_with_3plus": len(c_stats), "rows": c_stats[:40],
                            "low_cv_median": round(float(np.median(all_low_cv)), 4) if all_low_cv else None,
                            "note": "low_cv＝最低稳定音的版本间变异系数；越小＝各场越一致"}

    # ---------- D 音区适配 ----------
    alb = load("archive_vocal_albums.json").get("songs", [])
    live_by_song = defaultdict(list)
    for r in rows:
        if r.get("low_hz"):
            live_by_song[r.get("song")].append(float(r["low_hz"]))
    own_live = [np.median(v) for k, v in live_by_song.items() if norm(k) in own_norm and v]
    cov_live = [np.median(v) for k, v in live_by_song.items() if norm(k) not in own_norm and v]
    female = {k: {"orig": v, "live_low_median": round(float(np.median(live_by_song[k])), 1) if live_by_song.get(k) else None}
              for k, v in FEMALE_ORIG.items()}
    out["register_adapt"] = {
        "own_live_low_median": round(float(np.median(own_live)), 1) if own_live else None,
        "cover_live_low_median": round(float(np.median(cov_live)), 1) if cov_live else None,
        "own_n": len(own_live), "cover_n": len(cov_live),
        "female_origin_covers": female,
        "note": "同一个人唱自有曲/翻唱曲时的最低稳定音落点；差异＝他给不同来源曲目的音区预算",
    }

    # ---------- E 语言 / 风格跨度 ----------
    def grp(t):
        if re.search(r"[A-Za-z]", t) and not re.search(r"[\u4e00-\u9fff]", t):
            return "英文/外语"
        if any(k in t for k in ETHNIC):
            return "民族·戏曲·民歌"
        return "中文流行"
    g = defaultdict(list)
    for s in songs:
        g[grp(s["title"])].append(s)
    out["language_style"] = {k: {"songs": len(v), "home_songs": sum(1 for s in v if s["times"] >= 10),
                                 "with_index": sum(1 for s in v if s.get("has_index_data"))}
                             for k, v in g.items()}

    # ---------- A DiD ----------
    mat = song_matrix()
    a_rows = did_own_vs_cover(mat, sl, own_norm)
    if a_rows:
        d = [r["did_pct"] for r in a_rows]
        bonf = 0.05 / len(a_rows)
        out["did_own_vs_cover"] = {
            "n_shows": len(a_rows), "did_median_pct": round(float(np.median(d)), 1),
            "positive_share": round(float(np.mean([x > 0 for x in d])), 2),
            "bonferroni_alpha": round(bonf, 4),
            "significant": sum(1 for r in a_rows if r["placebo_p"] <= bonf),
            "rows": sorted(a_rows, key=lambda r: -abs(r["did_pct"]))[:20],
        }
    else:
        out["did_own_vs_cover"] = {"n_shows": 0, "note": "同场同时含自有曲与翻唱曲且有指数数据的场次不足"}

    (DATA / "cover_analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---------- 报告 ----------
    L = [f"# 翻唱与选曲价值分析（自动生成 {datetime.now():%Y-%m-%d %H:%M}）", "",
         f"- 唱过 {cat.get('stat',{}).get('songs_total')} 首｜自有 {cat.get('stat',{}).get('own_released')}｜"
         f"翻唱 {cat.get('stat',{}).get('covers')}｜**有指数数据仅 {cat.get('stat',{}).get('own_with_index_data',0)+cat.get('stat',{}).get('covers_with_index_data',0)} 首**", "",
         "## A 自有曲 vs 翻唱曲 · 舞台效应 DiD（自己给自己当对照）", ""]
    d = out["did_own_vs_cover"]
    if d.get("n_shows"):
        L += [f"- 可算场次 **{d['n_shows']}**｜DiD 中位 **{d['did_median_pct']:+.1f}%**｜为正 {d['positive_share']:.0%}"
              f"｜校正后显著 **{d['significant']}** 条（α={d['bonferroni_alpha']}）", "",
              "| 场次 | 巡次/城市 | 自有 n | 翻唱 n | 自有变化 | 翻唱变化 | **DiD** | p |",
              "|---|---|---|---|---|---|---|---|"]
        L += [f"| {r['date']} | {r['tour']}{r['city']} | {r['own_n']} | {r['cover_n']} | {r['own_pct']:+.1f}% | "
              f"{r['cover_pct']:+.1f}% | **{r['did_pct']:+.1f}%** | {r['placebo_p']} |" for r in d["rows"]]
    else:
        L += [f"- {d.get('note')}"]
    mv = out["multi_version"]
    L += ["", "## B 选曲指纹", "",
          f"- 各巡曲目数：" + "｜".join(f"{k} {v}" for k, v in out["fingerprint"]["tours"].items()),
          f"- 看家曲（≥10 场）**{out['fingerprint']['home_songs']}** 首｜只唱过一次 **{out['fingerprint']['once_only']}** 首", "",
          "| 从 → 到 | 上巡曲目 | 本巡曲目 | 保留 | 保留率 | 新增 | 新增率 |", "|---|---|---|---|---|---|---|"]
    L += [f"| {r['from']}→{r['to']} | {r['prev_n']} | {r['cur_n']} | {r['retained']} | {r['retain_rate']:.0%} | "
          f"{r['new']} | {r['new_rate']:.0%} |" for r in out["fingerprint"]["retention"]]
    L += ["", f"只唱过一次的曲目（前 60）：" + "、".join(out["fingerprint"]["once_list"]), "",
          "## C 同曲多版本方差（他每场是不是同一个水平）", "",
          f"- ≥3 个现场版本的曲目 **{mv['songs_with_3plus']}** 首｜版本间变异系数中位 **{mv['low_cv_median']}**（越小越一致）", "",
          "| 曲目 | 版本数 | 最低音中位 Hz | 四分位差 | 极差 | 变异系数 |", "|---|---|---|---|---|---|"]
    L += [f"| {c['song']} | {c['versions']} | {c['low_median']} | {c['low_iqr']} | {c['low_range']} | {c['low_cv']} |"
          for c in mv["rows"][:20]]
    ra = out["register_adapt"]
    L += ["", "## D 音区适配（他给不同来源曲目的音区预算）", "",
          f"- 自有曲现场最低音中位 **{ra['own_live_low_median']} Hz**（n={ra['own_n']}） vs "
          f"翻唱曲 **{ra['cover_live_low_median']} Hz**（n={ra['cover_n']}）",
          f"- 女声原唱翻唱专项（手工标注）：" + "；".join(f"{k}（原唱 {v['orig']}）→ 现场最低音中位 {v['live_low_median']}"
                                                     for k, v in ra["female_origin_covers"].items() if v["live_low_median"]), "",
          "## E 语言 / 风格跨度", "",
          "| 组 | 曲目数 | 看家曲 | 有指数数据 |", "|---|---|---|---|"]
    L += [f"| {k} | {v['songs']} | {v['home_songs']} | {v['with_index']} |" for k, v in out["language_style"].items()]
    L += ["", "> 全部结论只在「有指数数据」的子集上谈市场；其余 222 首的价值在**选择行为本身**（见 §B/§C/§D/§E）。"]
    (ROOT / "temp" / "翻唱价值分析.md").write_text("\n".join(L), encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != "rows"})
                      for k, v in out.items()}, ensure_ascii=False, indent=1)[:1400])
    print("→ data/cover_analysis.json\n→ temp/翻唱价值分析.md")
    assert out["did_own_vs_cover"] and out["multi_version"]["songs_with_3plus"] >= 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
