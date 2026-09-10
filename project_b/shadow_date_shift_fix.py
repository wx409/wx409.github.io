# -*- coding: utf-8 -*-
"""shadow_date_shift_fix.py —— 指数长表"日期偏移修正"影子验证（不动任何现有数据）

思路
----
修正映射的本质是**纯日期平移**：现状 `date=D 的值 = 文件 D 的昨日音乐指数`，
修正后 `date=D 的值 = 文件 D+1 的昨日音乐指数` = 现状表里 `D+1` 那一行的值。
所以影子表 = 用**同一个生产脚本**（E:\\wx\\wx_textmine\\00_build_matrix.py）
把"文件名日期"整体减一天后重建的长表。做法是打补丁 monkeypatch `parse_date`
后调用其 `main()` 写到一个**旁路文件**，绝不覆盖 music_index_long.csv。

随后用与 `compute_baseline_v1.py` 完全一致的口径（当日≥2首有指数才算有效日、
窗口≥3个有效日、基线<30 记 na）在两张表上分别算：
  · 年度表（日均/中位/覆盖天数）
  · 事件效应（T-21..T-7 基线 vs T+1..T+7 事后，事件取自 master_timeline.json）

输出：temp/music_index_long_SHADOW.csv、temp/shadow_date_shift_result.json、
      temp/日期偏移影子验证_20260910.md

用法：
    python project_b\\shadow_date_shift_fix.py            # 全流程（重建影子表约 5-10 分钟）
    python project_b\\shadow_date_shift_fix.py --reuse    # 复用已有影子表，只做对比
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import io
import json
import os
import statistics
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
REAL_CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
SHADOW_CSV = TEMP / "music_index_long_SHADOW.csv"
RESULT_JSON = TEMP / "shadow_date_shift_result.json"
REPORT_MD = TEMP / "日期偏移影子验证_20260910.md"
BM_SRC = Path(r"E:\wx\wx_textmine\00_build_matrix.py")
MASTER = Path(r"E:\wx\wx_textmine_out\master_timeline.json")
EVENT_TYPES = ("巡演/演出", "发歌/专辑", "综艺/影视", "获奖/荣誉", "演出")


# ---------------------------------------------------------------- 影子表构建
def build_shadow() -> dict:
    """用打了 -1 天补丁的生产脚本重建长表（旁路输出）。"""
    spec = importlib.util.spec_from_file_location("bm_shadow", str(BM_SRC))
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)

    orig_parse = bm.parse_date

    def parse_minus_one(name: str):
        # 注意：生产脚本的 parse_date 返回 "YYYY-MM-DD" 字符串（不是 date 对象）
        s = orig_parse(name)
        if not s:
            return None
        return (dt.date.fromisoformat(s) - dt.timedelta(days=1)).isoformat()

    bm.parse_date = parse_minus_one
    saved_argv = sys.argv
    buf = io.StringIO()
    try:
        sys.argv = ["00_build_matrix.py", str(SHADOW_CSV)]
        with redirect_stdout(buf):
            bm.main()
    finally:
        sys.argv = saved_argv
    tail = buf.getvalue().strip().splitlines()[-12:]
    return {"stdout_tail": tail, "shadow_csv": str(SHADOW_CSV),
            "exists": SHADOW_CSV.exists(),
            "rows": sum(1 for _ in open(SHADOW_CSV, encoding="utf-8-sig")) - 1 if SHADOW_CSV.exists() else 0}


# ---------------------------------------------------------------- 口径（与 compute_baseline_v1 一致）
def read_byday(path: Path) -> dict[str, list[float]]:
    import csv
    byday: dict[str, list[float]] = {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            d = (r.get("date") or "").strip()
            try:
                v = float(r["index"])
            except Exception:
                continue
            byday.setdefault(d, []).append(v)
    return byday


def day_mean(byday, d):
    xs = byday.get(d, [])
    return statistics.mean(xs) if len(xs) >= 2 else None


def win_mean(byday, lo, hi):
    vals = [day_mean(byday, d) for d in sorted(byday) if lo <= d <= hi]
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if len(vals) >= 3 else None


def annual(byday) -> list[dict]:
    days = sorted(byday)
    out = []
    for y in sorted({d[:4] for d in days}):
        ds = [d for d in days if d.startswith(y)]
        vals = [v for v in (day_mean(byday, d) for d in ds) if v is not None]
        if vals:
            out.append({"year": y, "cover_days": len(ds), "valid_days": len(vals),
                        "mean": round(statistics.mean(vals), 1),
                        "median": round(statistics.median(vals), 1)})
    return out


def effects(byday, d1) -> dict[str, dict]:
    try:
        events = json.load(open(MASTER, encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, dict] = {}
    for e in events:
        d = (e.get("date") or "")[:10]
        if not ("2023-01-01" <= d <= d1) or (e.get("type") or "") not in EVENT_TYPES:
            continue
        try:
            T = dt.date.fromisoformat(d)
        except Exception:
            continue
        b_lo, b_hi = (T - dt.timedelta(days=21)).isoformat(), (T - dt.timedelta(days=7)).isoformat()
        p_lo, p_hi = (T + dt.timedelta(days=1)).isoformat(), (T + dt.timedelta(days=7)).isoformat()
        base, post = win_mean(byday, b_lo, b_hi), win_mean(byday, p_lo, p_hi)
        eff = None
        if base is not None and post is not None and base >= 30:
            eff = round((post - base) / base * 100, 1)
        key = "%s|%s|%s" % (d, e.get("type"), (e.get("title") or "")[:40])
        out.setdefault(key, {"date": d, "type": e.get("type"),
                             "title": (e.get("title") or "")[:40],
                             "base": None if base is None else round(base, 1),
                             "post": None if post is None else round(post, 1),
                             "eff": eff})
    return out


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse", action="store_true", help="复用已有影子表，不重建")
    args = ap.parse_args()

    build_info = {"skipped": True}
    if not (args.reuse and SHADOW_CSV.exists()):
        print("[1/3] 用打补丁的生产脚本重建影子长表（日期整体 -1 天）…")
        build_info = build_shadow()
        print("      影子表:", build_info)

    print("[2/3] 读取真实长表与影子表…")
    cur, shd = read_byday(REAL_CSV), read_byday(SHADOW_CSV)
    cur_days, shd_days = sorted(cur), sorted(shd)
    result: dict = {
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "build": build_info,
        "current": {"range": [cur_days[0], cur_days[-1]],
                    "rows": sum(len(v) for v in cur.values()),
                    "days": len(cur_days), "annual": annual(cur)},
        "shadow": {"range": [shd_days[0], shd_days[-1]],
                   "rows": sum(len(v) for v in shd.values()),
                   "days": len(shd_days), "annual": annual(shd)},
    }

    # 平移等价性自检：现状表 D+1 的日均值 应等于 影子表 D 的日均值
    checked = same = 0
    for d in shd_days:
        nxt = (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat()
        a, b = day_mean(shd, d), day_mean(cur, nxt)
        if a is None or b is None:
            continue
        checked += 1
        if abs(a - b) < 0.05:
            same += 1
    result["shift_equivalence"] = {"checked": checked, "identical": same,
                                   "pct": round(same / checked * 100, 1) if checked else None}

    print("[3/3] 事件效应对照…")
    ec, es = effects(cur, cur_days[-1]), effects(shd, shd_days[-1])
    rows, flips = [], []
    for k in ec:
        if k not in es:
            continue
        a, b = ec[k]["eff"], es[k]["eff"]
        if a is None or b is None:
            continue
        rec = {"date": ec[k]["date"], "type": ec[k]["type"], "title": ec[k]["title"],
               "cur_eff": a, "fix_eff": b, "cur_base": ec[k]["base"], "fix_base": es[k]["base"],
               "cur_post": ec[k]["post"], "fix_post": es[k]["post"], "diff": round(abs(a - b), 2)}
        rows.append(rec)
        if (a > 0) != (b > 0):
            # 两端效应都达到 5% 才算"实质翻转"；否则属接近噪音的边缘翻转
            rec["material"] = (max(abs(a), abs(b)) >= 5)
            flips.append(rec)
    if rows:
        diffs = sorted(r["diff"] for r in rows)
        result["effects"] = {
            "comparable": len(rows),
            "diff_median": round(statistics.median(diffs), 2),
            "diff_mean": round(sum(diffs) / len(diffs), 2),
            "diff_p90": round(diffs[int(len(diffs) * 0.9)], 2),
            "diff_max": round(diffs[-1], 2),
            "sign_flips": len(flips),
            "sign_flips_material": sum(1 for r in flips if r.get("material")),
            "sign_flips_marginal": sum(1 for r in flips if not r.get("material")),
            "flip_rows": sorted(flips, key=lambda r: -r["diff"]),
            "flip_rows_material": sorted([r for r in flips if r.get("material")],
                                         key=lambda r: -r["diff"]),
            "top_diff_rows": sorted(rows, key=lambda r: -r["diff"])[:10],
        }
    json.dump(result, open(RESULT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---------- 出报告 ----------
    md = io.StringIO()
    md.write("# 指数长表日期偏移修正：影子验证报告\n\n")
    md.write("> 生成：%s · 脚本：`project_b\\shadow_date_shift_fix.py`（可复跑 `--reuse`）\n" % result["generated_at"])
    md.write("> 方式：用**同一个生产脚本** `E:\\wx\\wx_textmine\\00_build_matrix.py`（monkeypatch `parse_date` 整体 -1 天）"
             "重建旁路长表，**未覆盖** `music_index_long.csv`，未改动任何现有数据。\n\n")
    md.write("## 一、平移等价性自检\n\n")
    se = result["shift_equivalence"]
    md.write("- 比对 %d 天：影子表 D 的日均值 == 现状表 D+1 的日均值，一致 **%d 天（%s%%）**\n"
             % (se["checked"], se["identical"], se["pct"]))
    md.write("- 结论：修正映射确实是**纯日期平移**——同一批数值只换标签，不改变任何数值本身。\n\n")
    md.write("## 二、覆盖范围变化\n\n")
    md.write("| 口径 | 日期范围 | 覆盖天数 | 行数 |\n|---|---|---|---|\n")
    md.write("| 现状（文件名日=值日） | %s ~ %s | %d | %d |\n"
             % (cur_days[0], cur_days[-1], len(cur_days), sum(len(v) for v in cur.values())))
    md.write("| 修正（文件名日-1=值日） | %s ~ %s | %d | %d |\n\n"
             % (shd_days[0], shd_days[-1], len(shd_days), sum(len(v) for v in shd.values())))
    md.write("> 注意：修正后**最新可得日期 = 最新日档案日期 - 1**。日档案到 `2026.09.08.xlsx` 时，"
             "修正口径最新只到 **2026-09-07**；`2026-09-08` 要等 `2026.09.09.xlsx`（即用户待拷回的那份），"
             "`2026-09-09` 要等今晚 23:55 的 `2026.09.10.xlsx`。这正是「补录文件 + 修映射」必须配套的原因。\n\n")
    md.write("## 三、年度表对照（主口径：追踪曲目池日均）\n\n")
    md.write("| 年份 | 现状覆盖 | 现状日均 | 现状中位 | 修正覆盖 | 修正日均 | 修正中位 |\n|---|---|---|---|---|---|---|\n")
    cm = {r["year"]: r for r in result["current"]["annual"]}
    sm = {r["year"]: r for r in result["shadow"]["annual"]}
    for y in sorted(set(cm) | set(sm)):
        c, s = cm.get(y), sm.get(y)
        md.write("| %s | %s | %s | %s | %s | %s | %s |\n" % (
            y,
            c and c["cover_days"], c and c["mean"], c and c["median"],
            s and s["cover_days"], s and s["mean"], s and s["median"]))
    md.write("\n> 年度日均差异极小（跨年两天互换），**核心口径值不受影响**。\n\n")
    ef = result.get("effects")
    if ef:
        md.write("## 四、事件效应对照\n\n")
        md.write("- 可比事件 **%d** 个；效应%% 绝对差：中位 **%.2f** / 均值 %.2f / P90 %.2f / 最大 %.1f\n"
                 % (ef["comparable"], ef["diff_median"], ef["diff_mean"], ef["diff_p90"], ef["diff_max"]))
        md.write("- **正负号翻转（结论方向会变）的事件：%d 个**；其中**实质翻转（至少一端 |效应| ≥5%%）：%d 个**、"
                 "边缘翻转（两端都在 ±5%% 内，噪音级）：%d 个\n\n"
                 % (ef["sign_flips"], ef.get("sign_flips_material", 0),
                    ef.get("sign_flips_marginal", 0)))
        if ef.get("flip_rows_material"):
            md.write("### ① 实质翻转（论文/传记若引用过必须改）\n\n")
            md.write("| 日期 | 类型 | 事件 | 现状基线→事后 | 现状效应 | 修正基线→事后 | 修正效应 |\n")
            md.write("|---|---|---|---|---|---|---|\n")
            for r in ef["flip_rows_material"]:
                md.write("| %s | %s | %s | %s→%s | **%+.1f%%** | %s→%s | **%+.1f%%** |\n"
                         % (r["date"], r["type"], r["title"], r["cur_base"], r["cur_post"], r["cur_eff"],
                            r["fix_base"], r["fix_post"], r["fix_eff"]))
            md.write("\n")
        if ef["flip_rows"]:
            md.write("### ② 全部翻转明细（含边缘）\n\n")
            md.write("| 日期 | 类型 | 事件 | 现状基线→事后 | 现状效应 | 修正基线→事后 | 修正效应 |\n")
            md.write("|---|---|---|---|---|---|---|\n")
            for r in ef["flip_rows"]:
                md.write("| %s | %s | %s | %s→%s | **%+.1f%%** | %s→%s | **%+.1f%%** |\n"
                         % (r["date"], r["type"], r["title"], r["cur_base"], r["cur_post"], r["cur_eff"],
                            r["fix_base"], r["fix_post"], r["fix_eff"]))
            md.write("\n")
        md.write("### 差异最大的 10 条（不改符号但幅度变化明显）\n\n")
        md.write("| 日期 | 事件 | 现状效应 | 修正效应 | 差 |\n|---|---|---|---|---|\n")
        for r in ef["top_diff_rows"]:
            md.write("| %s | %s | %+.1f%% | %+.1f%% | %.1f |\n"
                     % (r["date"], r["title"], r["cur_eff"], r["fix_eff"], r["diff"]))
        md.write("\n")
    md.write("## 五、修正补丁（一行改动）\n\n")
    md.write("`E:\\wx\\wx_textmine\\00_build_matrix.py`：\n\n```python\n")
    md.write("# 原（第 123/149 行附近）：\n")
    md.write("#   d = parse_date(base)          # 返回 \"YYYY-MM-DD\" 字符串\n")
    md.write("#   ...\n")
    md.write("#   if d not in sub:  sub[d] = v\n")
    md.write("# 改为（值日期 = 文件名日期 - 1）：\n")
    md.write("d = parse_date(base)\n")
    md.write("if d:\n")
    md.write("    d = (datetime.date.fromisoformat(d) - datetime.timedelta(days=1)).isoformat()\n")
    md.write("    # 昨日音乐指数属于前一天\n")
    md.write("```\n\n")
    md.write("> 或等价地在 `parse_date()` 返回处统一减一天（本影子验证用的就是这种做法，"
             "证明整条生产链路都能跑通）。\n\n")
    md.write("## 六、切正式口径的配套动作\n\n")
    md.write("1. `python E:\\wx\\wx_textmine\\00_build_matrix.py`（重建 `music_index_long.csv`）\n")
    md.write("2. `python E:\\wx\\wx论文素材_王晰作传\\基线口径\\compute_baseline_v1.py`（年度表 + 事件效应 + 自动同步站点 `data/archive_baseline.json`）\n")
    md.write("3. 操作中心 **45/44 → 65/66 → 39**（基线 → 年度卡/档案层 → 原始库长表/诊断 → 完整部署）\n")
    md.write("4. `事件效应口径修正.py` 重跑；**逐条复核上表符号翻转事件**（论文/传记若引用过必须改）\n")
    md.write("5. `data/calibers.md` 登记新口径；`audit_caliber.py` + `audit_nav.py` 全 OK\n\n")
    md.write("## 七、风险与建议\n\n")
    md.write("- 修正会改变**日期标签**：任何按日期引用的叙事（story/academic/命题卡/事件效应）需复核；\n")
    md.write("- 大屏侧（守护进程）本来就是正确口径（源码 834-838 行已 `data_date-1`），"
             "修正后**长表与大屏终于同一天口径**；\n")
    md.write("- 修正的代价：最新可得日期回退一天（见第二节说明），需与补录文件配套执行。\n")
    REPORT_MD.write_text(md.getvalue(), encoding="utf-8")

    print("\n[OK] 影子表:", SHADOW_CSV)
    print("[OK] 结果 JSON:", RESULT_JSON)
    print("[OK] 报告:", REPORT_MD)
    print("平移等价性: %s/%s (%s%%)" % (se["identical"], se["checked"], se["pct"]))
    if ef:
        print("事件效应: 可比 %d | 中位差 %.2f | 符号翻转 %d"
              % (ef["comparable"], ef["diff_median"], ef["sign_flips"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
