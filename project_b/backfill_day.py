# -*- coding: utf-8 -*-
"""backfill_day.py —— 按日补录与验收（例：把 2026.09.09 日档案补进指数长表）

场景（2026-09-09 停摆事故）：
    当晚 23:55 全量批次未执行 → 增补数据库缺 `2026.09.09.xlsx`；
    用户从另一台机器拷回该文件后，需要：确认落位 → 重建长表 → 验收该日覆盖 → 才敢往下走。

本脚本一条命令做完"预检 → 重建 → 验收 → 报告"，并且**顺带自查长表用的是哪种日期映射**
（现状：文件名日=值日 / 修正：文件名日-1=值日），避免补录落错行。

用法：
    python project_b\\backfill_day.py --date 2026-09-09                # 预检 + 重建 + 验收
    python project_b\\backfill_day.py --date 2026-09-09 --check-only   # 只预检，不动长表
    python project_b\\backfill_day.py --date 2026-09-09 --downstream   # 追加：基线/年度卡/部署提示
    python project_b\\backfill_day.py --date 2026-09-09 --no-rebuild   # 只验收（长表已重建过）

退出码：0 = 该日已成功进入长表；1 = 未进入 / 有阻塞；2 = 脚本异常。
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"

ADDON = Path(r"E:\wx\指数数据库\增补数据库2025.2.22-")
ARCHIVED = ADDON / "archived"
DOWNLOAD = Path(r"E:\wx\download")
INDEXVS = Path(r"E:\wx\指数vs")
LONG_CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
BM = Path(r"E:\wx\wx_textmine\00_build_matrix.py")
BASELINE_DIR = Path(r"E:\wx\论文素材_王晰作传\基线口径")
COMPUTE_BASELINE = BASELINE_DIR / "compute_baseline_v1.py"


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_date(name: str) -> dt.date | None:
    m = re.search(r"(?:^|[^\d])(\d{4})[._-]?(\d{1,2})[._-]?(\d{1,2})(?:[^\d]|$)", name)
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def find_day_files(day: dt.date) -> list[Path]:
    """列出该日所有候选日档案（多个目录 + 带时刻后缀的都算）。"""
    out: list[Path] = []
    stamp = day.strftime("%Y.%m.%d")
    for d in (ADDON, DOWNLOAD, INDEXVS):
        if not d.is_dir():
            continue
        for p in sorted(d.glob(stamp + "*.xlsx")):
            if not p.name.startswith("~$"):
                out.append(p)
        if d is ARCHIVED:
            continue
        for p in sorted(d.glob("archived_%s*.xlsx" % day.strftime("%Y%m%d"))):
            out.append(p)
    return out


def read_day_values(p: Path) -> dict[str, tuple[float | None, float | None]]:
    """{歌曲: (昨日音乐指数, 音乐指数)}；列名做模糊匹配（历史文件有乱码表头）。"""
    df = pd.read_excel(p)
    cols = list(df.columns)
    nc = next((c for c in cols if "歌曲" in str(c)), cols[1] if len(cols) > 1 else None)
    yc = next((c for c in cols if "昨日音乐指数" in str(c)), None)
    cc = next((c for c in cols if str(c).strip() == "音乐指数"), None)

    def num(v):
        try:
            x = float(str(v).replace(",", "").replace("，", "").strip())
            return x if x == x and x > 0 else None
        except Exception:
            return None

    out = {}
    if nc is None:
        return out
    for _, r in df.iterrows():
        nm = str(r.get(nc)).strip()
        if not nm or nm in ("nan", "None"):
            continue
        out[nm] = (num(r.get(yc)) if yc else None, num(r.get(cc)) if cc else None)
    return out


def long_table_rows(day: dt.date) -> pd.DataFrame:
    if not LONG_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(LONG_CSV, encoding="utf-8-sig")
    df["date"] = df["date"].astype(str)
    return df[df["date"] == day.isoformat()]


def detect_mapping(day: dt.date, day_files: list[Path]) -> dict:
    """自查长表口径：该日行的值 = 文件 D 的昨日（现状）还是文件 D+1 的昨日（修正）？"""
    info = {"mapping": "unknown", "evidence": {}}
    sub = long_table_rows(day)
    if sub.empty:
        info["mapping"] = "该日尚无数据（无法判定）"
        return info
    lt = {str(r["song"]): float(r["index"]) for _, r in sub.iterrows()}
    # 文件 D 的昨日
    if day_files:
        fD = read_day_values(day_files[0])
        hitD = sum(1 for nm, (y, _c) in fD.items() if y is not None and nm in lt and abs(y - lt[nm]) < 0.5)
        totD = sum(1 for nm, (y, _c) in fD.items() if y is not None and nm in lt)
        info["evidence"]["文件D昨日 vs 长表D"] = "%d/%d" % (hitD, totD)
        # 文件 D+1 的昨日
        nxt = day + dt.timedelta(days=1)
        nxt_files = find_day_files(nxt)
        if nxt_files:
            fN = read_day_values(nxt_files[0])
            hitN = sum(1 for nm, (y, _c) in fN.items() if y is not None and nm in lt and abs(y - lt[nm]) < 0.5)
            totN = sum(1 for nm, (y, _c) in fN.items() if y is not None and nm in lt)
            info["evidence"]["文件D+1昨日 vs 长表D"] = "%d/%d" % (hitN, totN)
            if totN and hitN / totN > 0.8:
                info["mapping"] = "修正口径（文件名日-1=值日）"
                return info
        if totD and hitD / totD > 0.8:
            info["mapping"] = "现状口径（文件名日=值日）"
    return info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="目标日期 YYYY-MM-DD")
    ap.add_argument("--check-only", action="store_true", help="只预检，不重建长表")
    ap.add_argument("--no-rebuild", action="store_true", help="不重建（长表已重建过）")
    ap.add_argument("--downstream", action="store_true", help="重建后继续跑 compute_baseline_v1")
    args = ap.parse_args()

    day = dt.date.fromisoformat(args.date)
    report: dict = {"date": day.isoformat(), "steps": []}

    def step(name, ok, detail=""):
        report["steps"].append({"step": name, "ok": bool(ok), "detail": str(detail)[:400]})
        log("  [%s] %s%s" % ("OK " if ok else "!! ", name, (" — " + str(detail)[:200]) if detail else ""))

    log("=" * 70)
    log("按日补录与验收：%s" % day.isoformat())
    log("=" * 70)

    # 1) 文件落位
    files = find_day_files(day)
    step("候选日档案落位", bool(files), ("、".join(p.name for p in files[:3]) if files else
                                   "未找到 %s*.xlsx（增补数据库/download/指数vs 均无）" % day.strftime("%Y.%m.%d")))
    if files:
        addon_hit = [p for p in files if p.parent == ADDON]
        step("已在增补数据库目录", bool(addon_hit),
             addon_hit[0].name if addon_hit else "仅在其他目录；建议拷入 %s" % ADDON)
        v = read_day_values(files[0])
        with_y = sum(1 for _nm, (y, _c) in v.items() if y is not None)
        with_c = sum(1 for _nm, (_y, c) in v.items() if c is not None)
        step("日档案内容可用", with_y > 0 or with_c > 0,
             "共 %d 首；有昨日音乐指数 %d 首、有音乐指数 %d 首" % (len(v), with_y, with_c))

    before = long_table_rows(day)
    step("重建前该日在长表", not before.empty,
         "已有 %d 行" % len(before) if not before.empty else "无（待重建纳入）")

    # 2) 重建长表
    if not (args.check_only or args.no_rebuild):
        log("  -- 重建长表：%s --" % BM)
        r = subprocess.run([sys.executable, "-X", "utf8", str(BM)], cwd=str(BM.parent),
                           capture_output=True, text=True, encoding="utf-8", errors="ignore",
                           timeout=1800)
        tail = [x for x in (r.stdout or "").splitlines() if x.strip()][-6:]
        step("重建 music_index_long.csv", r.returncode == 0, " | ".join(tail))

    # 3) 验收
    after = long_table_rows(day)
    ok_cover = not after.empty
    step("该日已进入长表", ok_cover, "行数 %d" % len(after) if ok_cover else "仍无数据")
    day_mean = None
    if ok_cover:
        vals = pd.to_numeric(after["index"], errors="coerce").dropna()
        day_mean = round(float(vals.mean()), 1) if len(vals) else None
        step("该日有效观测", len(vals) >= 2, "%d 首｜日均 %s" % (len(vals), day_mean))
        ctx = []
        for k in (-2, -1, 1, 2):
            d2 = (day + dt.timedelta(days=k)).isoformat()
            sub = long_table_rows(dt.date.fromisoformat(d2))
            if not sub.empty:
                vs = pd.to_numeric(sub["index"], errors="coerce").dropna()
                if len(vs):
                    ctx.append("%s=%d首/%.0f" % (d2, len(vs), vs.mean()))
        step("前后日对照", bool(ctx), "、".join(ctx))
    report["day_mean"] = day_mean

    # 4) 口径自查
    mp = detect_mapping(day, files)
    report["mapping"] = mp
    step("长表口径自查", True, "%s（%s）" % (mp["mapping"], json.dumps(mp["evidence"], ensure_ascii=False)))

    # 5) 下游
    if args.downstream and ok_cover and not args.check_only:
        if COMPUTE_BASELINE.exists():
            r = subprocess.run([sys.executable, "-X", "utf8", str(COMPUTE_BASELINE)],
                               cwd=str(BASELINE_DIR), capture_output=True, text=True,
                               encoding="utf-8", errors="ignore", timeout=900)
            step("compute_baseline_v1（年度表+效应+同步站点）", r.returncode == 0,
                 " | ".join([x for x in (r.stdout or "").splitlines() if x.strip()][-4:]))
        log("  后续请依次执行：操作中心 45/44（基线+档案卡）→ 65/66（原始库长表+诊断）→ 39（完整部署）")

    # 报告
    TEMP.mkdir(exist_ok=True)
    out_md = TEMP / ("补录验收_%s.md" % day.strftime("%Y%m%d"))
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# 按日补录与验收：%s\n\n" % day.isoformat())
        f.write("生成：%s\n\n| 步骤 | 结果 | 详情 |\n|---|---|---|\n"
                % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        for s in report["steps"]:
            f.write("| %s | %s | %s |\n" % (s["step"], "✅" if s["ok"] else "❌", s["detail"]))
        f.write("\n口径自查：**%s**\n" % report["mapping"]["mapping"])
        f.write("\n该日池均值：%s\n" % (day_mean if day_mean is not None else "—"))
    (TEMP / ("补录验收_%s.json" % day.strftime("%Y%m%d"))).write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    log("  报告：%s" % out_md)

    ok = ok_cover
    log("=" * 70)
    log("结论：%s" % ("该日已成功进入指数长表 ✅" if ok else "该日尚未进入长表（看上面 ❌ 步骤）❌"))
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("[backfill] 异常: %s" % e, file=sys.stderr)
        sys.exit(2)
