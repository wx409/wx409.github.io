# -*- coding: utf-8 -*-
"""归因/因果检验报告（可随活动与数据自动更新）。

读：指数长表 CSV + 站点事件 JSON + 微博语料（本地）
算：市场温度序列（每首歌除以自身 91 天滚动中位，去水平）
    对每类事件做四问：① 安慰剂（随机断点零分布）② 剂量-反应 ③ 事前趋势外推(ITS) ④ 中介链（场次/微博 vs 温度）
出：temp\\归因报告.md（人读）+ temp\\attribution_report.json（机读）；stdout 摘要供每日链路记录。

用法:
  python -X utf8 project_b\\attribution_report.py            # 全量重算
  python -X utf8 project_b\\attribution_report.py --quiet    # 只写文件（供 auto_update 调用）

新增手工里程碑：编辑 temp\\归因事件表.json（首次运行会自动生成含已知锚点）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LONG_CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
WEIBO = Path(r"E:\wx\私有工具\weibo_merged\weibo_all_posts.json")
DASH = ROOT / "dashboard" / "dashboard_data.json"
REG = ROOT / "temp" / "归因事件表.json"
OUT_MD = ROOT / "temp" / "归因报告.md"
OUT_JS = ROOT / "temp" / "attribution_report.json"
RNG = np.random.default_rng(20260326)
NEG = ["抱歉", "对不起", "请原谅", "背不动", "累了", "太累", "撑不住", "痛", "哭",
       "告别", "再见", "离开", "不想", "孤独", "失眠", "睡不着", "辜负"]
SEED_EVENTS = [
    {"date": "2025-03-26", "kind": "里程碑", "label": "小红书首次披露与东演关联", "source": "档案卡·年度2025"},
    {"date": "2025-04-09", "kind": "里程碑", "label": "生日 / 《不说》实体预售开启", "source": "微博·工作室"},
    {"date": "2026-01-21", "kind": "里程碑", "label": "《草原之夜》首演（东演歌舞剧）", "source": "命题卡05"},
    {"date": "2024-04-08", "kind": "微博-负情绪", "label": "负情绪微博（次日生日）", "source": "微博语料"},
]


# ---------------- 基础序列 ----------------
def temperature() -> pd.Series:
    df = pd.read_csv(LONG_CSV, encoding="utf-8-sig")
    df.columns = [c.strip().lower() for c in df.columns]
    dcol = [c for c in df.columns if "date" in c][0]
    scol = [c for c in df.columns if "song" in c or "name" in c][0]
    icol = [c for c in df.columns if "index" in c][0]
    df = df[[dcol, scol, icol]].rename(columns={dcol: "d", scol: "song", icol: "index"})
    df["d"] = pd.to_datetime(df["d"], errors="coerce")
    df["index"] = pd.to_numeric(df["index"].astype(str).str.replace(",", ""), errors="coerce")
    df = df.dropna().sort_values(["song", "d"])
    base = df.groupby("song")["index"].transform(lambda s: s.rolling(91, center=True, min_periods=30).median())
    df["rel"] = df["index"] / base
    return df.groupby("d")["rel"].median().dropna()


def placebo_null(vals: np.ndarray, win: int, step: int = 3) -> np.ndarray:
    pos = np.arange(win, len(vals) - win, step)
    med = pd.Series(vals)
    roll = med.rolling(win).median()
    return np.array([roll.iloc[p + win - 1] - roll.iloc[p - 1] for p in pos])  # 后窗中位 − 前窗中位


def four_questions(daily: pd.Series, cut: str, win: int, null: np.ndarray) -> dict:
    di = pd.DatetimeIndex(daily.index)
    vals = daily.to_numpy(dtype=float)
    p = int(di.searchsorted(pd.Timestamp(cut)))
    if p - win < 0 or p + win >= len(vals):
        return {}
    pre, post = vals[p - win:p], vals[p:p + win]
    lvl = float(np.median(post) - np.median(pre))
    # ③ ITS：事前趋势外推
    x = np.arange(win)
    b, a = np.polyfit(x, pre, 1)
    pred = a + b * (win + np.arange(win))
    its = float(np.median(post) - np.median(pred))
    resid_sd = float(np.std(pre - (a + b * x), ddof=2)) or 1e-9
    # ① 安慰剂
    pval = float((np.abs(null) >= abs(lvl)).mean()) if len(null) else np.nan
    # ② 剂量-反应（按事件类型在外部补）
    return {
        "cut": cut, "win": win,
        "pre_med": round(float(np.median(pre)), 4), "post_med": round(float(np.median(post)), 4),
        "level_diff": round(lvl, 4), "level_pct": round((np.median(post) / np.median(pre) - 1) * 100, 2),
        "its_diff": round(its, 4), "its_sd": round(its / resid_sd, 2),
        "placebo_p": round(pval, 3),
        "verdict": "可识别（须复核混杂）" if pval < 0.05 else "测不出（噪声范围内）",
    }


def mediation(daily: pd.Series, cut: str, win: int) -> dict:
    """中介链：签约/里程碑前后 场次数 与 微博条数 的变化（M 段是否成立）。"""
    c = pd.Timestamp(cut)
    a0, a1, b0, b1 = c - pd.Timedelta(days=win), c, c, c + pd.Timedelta(days=win)
    out = {}
    try:
        dash = json.loads(DASH.read_text(encoding="utf-8"))
        pe = pd.DataFrame(dash.get("performance_events", []))
        if "date" in pe:
            d = pd.to_datetime(pe["date"], errors="coerce")
            out["shows_pre"] = int(((d >= a0) & (d < a1)).sum())
            out["shows_post"] = int(((d >= b0) & (d <= b1)).sum())
    except Exception:
        pass
    try:
        posts = pd.DataFrame(json.loads(WEIBO.read_text(encoding="utf-8"))["posts"])
        wd = pd.to_datetime(posts["date"], errors="coerce")
        out["weibo_pre"] = int(((wd >= a0) & (wd < a1)).sum())
        out["weibo_post"] = int(((wd >= b0) & (wd <= b1)).sum())
    except Exception:
        pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    log = (lambda *m: None) if a.quiet else (lambda *m: print(*m))

    daily = temperature()
    log(f"市场温度序列 {len(daily)} 天（{daily.index.min().date()} ~ {daily.index.max().date()}）")

    if not REG.exists():
        REG.write_text(json.dumps(SEED_EVENTS, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"已初始化事件表：{REG}")
    events = json.loads(REG.read_text(encoding="utf-8"))

    # 自动事件：专辑发行 / 演出 / 负情绪微博
    auto = []
    try:
        dash = json.loads(DASH.read_text(encoding="utf-8"))
        for e in dash.get("release_events", []):
            if e.get("date"):
                auto.append({"date": str(e["date"])[:10], "kind": "发行",
                             "label": f"发行：{e.get('name') or e.get('song') or ''}", "source": "dashboard_data"})
    except Exception:
        pass
    try:
        posts = pd.DataFrame(json.loads(WEIBO.read_text(encoding="utf-8"))["posts"])
        posts["d"] = pd.to_datetime(posts["date"], errors="coerce")
        per = posts[posts["source"].str.contains("王晰微博", na=False) | ~posts["source"].str.contains("工作室", na=False)]
        per = per.dropna(subset=["d"])
        per["neg"] = per["text"].apply(lambda t: sum(k in str(t) for k in NEG))
        for _, r in per[per["neg"] >= 1].iterrows():
            auto.append({"date": r["d"].strftime("%Y-%m-%d"), "kind": "微博-负情绪",
                         "label": f"负情绪词×{r['neg']}", "source": "weibo"})
    except Exception as e:
        log("微博自动事件跳过:", e)

    rows, med_rows = [], []
    for win in (90, 180):
        null = placebo_null(daily.to_numpy(dtype=float), win)
        for ev in events + auto:
            r = four_questions(daily, ev["date"], win, null)
            if not r:
                continue
            r.update({k: ev[k] for k in ("kind", "label") if k in ev})
            rows.append(r)
        med_rows.append({"cut": "__窗口统计__", "win": win, "n_placebo_null": int(len(null)),
                         "null_abs_median": round(float(np.median(np.abs(null))), 4)})
    res = pd.DataFrame(rows)

    # 多重比较：一次跑几十个事件，必须校正，否则 0.04 的 p 是必然出现的假阳性
    corr = {}
    for w in (90, 180):
        sub = res[res["win"] == w]["placebo_p"].dropna()
        m = len(sub)
        if not m:
            continue
        bonf = 0.05 / m
        pv = np.sort(sub.to_numpy())
        bh = 0.0
        for i, p in enumerate(pv, 1):
            if p <= 0.05 * i / m:
                bh = p
        corr[w] = {"n_tests": int(m), "bonferroni_alpha": round(bonf, 5),
                   "pass_bonferroni": int((sub <= bonf).sum()),
                   "bh_fdr_significant": int((sub <= bh).sum()) if bh else 0,
                   "bh_threshold": round(bh, 5),
                   "min_p": round(float(sub.min()), 4)}

    # 剂量-反应（负情绪族：词数 vs 后窗变化）
    dose = {}
    neg = res[(res["kind"] == "微博-负情绪") & (res["win"] == 180)].copy()
    if len(neg) >= 5:
        cnt = neg["label"].str.extract(r"×(\d+)").astype(float)[0]
        dose = {"n": len(neg), "r_words_vs_delta": round(float(np.corrcoef(cnt.fillna(1), neg["level_diff"])[0, 1]), 3),
                "pos_share": round(float((neg["level_diff"] > 0).mean()), 2)}

    med = []
    for ev in [e for e in events if e["kind"] == "里程碑"]:
        m = mediation(daily, ev["date"], 365)
        if m:
            med.append({"event": ev["label"], "date": ev["date"], **m})

    # 输出
    piv = res.pivot_table(index=["kind", "label", "cut"], columns="win",
                          values=["level_pct", "placebo_p"], aggfunc="first")
    lines = [f"# 归因报告（自动生成 {datetime.now():%Y-%m-%d %H:%M}）", "",
             f"- 市场温度序列：{len(daily)} 天（{daily.index.min().date()} ~ {daily.index.max().date()}）",
             "- 口径：每首歌 ÷ 自身 91 天滚动中位 → 当日跨歌中位（1.0 = 自身常态）",
             "- 四问：① 安慰剂（随机断点零分布）② 剂量-反应 ③ 事前趋势外推(ITS) ④ 中介链", ""]
    for w, c in corr.items():
        lines.append(f"- **多重比较（±{w} 天，{c['n_tests']} 个检验）**：Bonferroni α = {c['bonferroni_alpha']}"
                     f"（通过 {c['pass_bonferroni']} 条）｜BH-FDR 阈值 {c['bh_threshold']}"
                     f"（显著 {c['bh_fdr_significant']} 条）｜最小 p = {c['min_p']}")
    lines += ["", "## 事件检验（窗口 ±90 / ±180 天）", "",
              "| 类型 | 事件 | 日期 | ±90 水平 | ±90 p | ±180 水平 | ±180 p | 判定 |",
              "|---|---|---|---|---|---|---|---|"]
    m90 = corr.get(90, {}).get("bonferroni_alpha", 0.05)
    m180 = corr.get(180, {}).get("bonferroni_alpha", 0.05)
    for (kind, label, cut), g in piv.iterrows():
        def gv(col, w):
            try:
                v = g[(col, w)]
                return "—" if pd.isna(v) else v
            except Exception:
                return "—"
        p180 = gv("placebo_p", 180)
        p90 = gv("placebo_p", 90)
        ok = (isinstance(p180, (int, float)) and p180 <= m180) or (isinstance(p90, (int, float)) and p90 <= m90)
        lines.append(f"| {kind} | {label} | {cut} | {gv('level_pct', 90)}% | {p90} | "
                     f"{gv('level_pct', 180)}% | {p180} | {'可识别' if ok else '测不出'} |")
    if dose:
        lines += ["", "## 剂量-反应（负情绪微博族，±180 天）",
                  f"- n={dose['n']}｜词数 × 事后变化 r = **{dose['r_words_vs_delta']}**｜事后变好占比 {dose['pos_share']:.0%}"]
    if med:
        lines += ["", "## 中介链（里程碑前后 365 天）", "",
                  "| 事件 | 演出场次 | 微博条数 |", "|---|---|---|"]
        for m in med:
            lines.append(f"| {m['event']}（{m['date']}） | {m.get('shows_pre','—')} → {m.get('shows_post','—')} | "
                         f"{m.get('weibo_pre','—')} → {m.get('weibo_post','—')} |")
    lines += ["", "> 判定规则：通过**多重比较校正**（Bonferroni/BH-FDR）才叫「可识别」；否则是叙事，不是关联。",
              "> 新增里程碑：编辑 `temp/归因事件表.json`；发行/演出/负情绪微博为自动采集。"]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    OUT_JS.write_text(json.dumps({"generated_at": datetime.now().isoformat(timespec="seconds"),
                                  "series_days": len(daily), "correction": corr,
                                  "events": rows, "dose": dose, "mediation": med},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    n_ok = int((res[res["win"] == 180]["placebo_p"] <= corr.get(180, {}).get("bonferroni_alpha", 0.05)).sum())
    log(f"事件 {len(res)} 条检验｜校正后「可识别」{n_ok} 条｜校正 {corr.get(180)}｜剂量-反应 {dose or '样本不足'}")
    log(f"→ {OUT_MD}\n→ {OUT_JS}")
    assert OUT_MD.exists() and len(daily) > 500, "产物缺失或序列过短"
    return 0


if __name__ == "__main__":
    sys.exit(main())
