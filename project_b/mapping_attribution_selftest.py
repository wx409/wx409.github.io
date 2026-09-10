# -*- coding: utf-8 -*-
"""mapping_attribution_selftest.py —— 日期映射「归属」自测（合成数据，不碰真实数据）

要证明的事
----------
修正映射（文件 D 的「昨日音乐指数」→ 日期 **D−1**）在**今晚这批数据到来时**会怎么落位：
    · 文件 2026.09.10.xlsx（今晚 23:55 生成，其昨日音乐指数 = 9/9 官方值） → 日期 **2026-09-09** ✅
    · 文件 2026.09.09.xlsx（缺失那份，其昨日 = 9/8 官方值）              → 日期 **2026-09-08**
    · 若只补了"次日"文件（无 2026.09.09.xlsx），则 2026-09-08 仍是空洞

做法：把 `00_build_matrix.py` 的 STORES 打桩到一个**临时合成目录**（只有两个小 xlsx），
分别用「当前映射（已修正）」与「原始映射（未修正）」跑一遍，把输出 CSV 写到 temp\\，
逐条断言归属日期与取值。全程不读写任何真实数据。

用法：python project_b\\mapping_attribution_selftest.py       # 退出码 0 = 全部通过
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "temp"
BM_SRC = Path(r"E:\wx\wx_textmine\00_build_matrix.py")

PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = ""):
    (PASS if cond else FAIL).append(name)
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name, (" — " + detail) if detail else ""))


def make_dayfile(folder: Path, name: str, rows: list[tuple[str, float]]) -> Path:
    """按守护进程全量输出的列结构造一份合成日档案。"""
    df = pd.DataFrame([{"序号": i + 1, "歌曲名称": nm, "演唱者": "王晰",
                        "昨日音乐指数": v, "音乐指数": v + 5, "当前收听人数": 10,
                        "链接": "https://example.invalid/%s" % nm, "状态": "成功"}
                       for i, (nm, v) in enumerate(rows)])
    p = folder / name
    df.to_excel(p, index=False)
    return p


def load_ns(strip_fix: bool) -> dict:
    """把 00_build_matrix.py 以命名空间 dict 装载。

    strip_fix=True 时从源码文本里**剥掉**「日期 − 1」那两行（标记行 + 紧随一行），
    从而得到真正的"未修正"口径 —— 注意直接 exec_module 拿到的是磁盘上已打补丁的版本。
    """
    text = BM_SRC.read_text(encoding="utf-8")
    if strip_fix:
        lines, keep, dropping = text.split("\n"), [], False
        for ln in lines:
            if "昨日音乐指数属于前一天" in ln:
                dropping = True
                continue
            if dropping:
                dropping = False
                continue
            keep.append(ln)
        text = "\n".join(keep)
    ns: dict = {"__name__": "bm_selftest", "__file__": str(BM_SRC)}
    exec(compile(text, str(BM_SRC), "exec"), ns)
    return ns


def run_matrix(ns: dict, src_dir: Path, out_csv: Path) -> dict:
    """把命名空间里的 STORES 打桩到合成目录，跑一次 main()，返回 {date: {song: value}}。"""
    orig_stores, orig_argv = ns["STORES"], sys.argv
    try:
        ns["STORES"] = [("addon", str(src_dir))]
        sys.argv = ["00_build_matrix.py", str(out_csv)]
        with redirect_stdout(io.StringIO()):
            ns["main"]()
    finally:
        ns["STORES"], sys.argv = orig_stores, orig_argv
    df = pd.read_csv(out_csv, encoding="utf-8-sig")
    out: dict[str, dict[str, float]] = {}
    for _, r in df.iterrows():
        out.setdefault(str(r["date"]), {})[str(r["song"])] = float(r["index"])
    return out


def main() -> int:
    if not BM_SRC.exists():
        print("[X] 未找到 %s" % BM_SRC)
        return 2

    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "synth"
        src.mkdir(parents=True)
        # 合成：9/9 文件（其昨日=9/8 官方值）与 9/10 文件（其昨日=9/9 官方值）
        make_dayfile(src, "2026.09.09.xlsx", [("甲歌", 111.0), ("乙歌", 222.0), ("丙歌", 333.0)])
        make_dayfile(src, "2026.09.10.xlsx", [("甲歌", 444.0), ("乙歌", 555.0), ("丙歌", 666.0)])

        print("=" * 68)
        print("日期映射归属自测（合成数据：仅 2026.09.09.xlsx + 2026.09.10.xlsx）")
        print("=" * 68)

        # ---- A) 当前（已修正）映射 ----
        bm = load_ns(strip_fix=False)
        out_fixed = TEMP / "_attr_selftest_fixed.csv"
        res_fixed = run_matrix(bm, src, out_fixed)
        print("[A] 当前映射（文件日 − 1 = 值日）输出日期：%s" % sorted(res_fixed))
        check("9/9 文件的昨日值落到 2026-09-08",
              res_fixed.get("2026-09-08", {}).get("甲歌") == 111.0,
              str(res_fixed.get("2026-09-08")))
        check("9/10 文件的昨日值落到 2026-09-09（今晚这批数据的落位）",
              res_fixed.get("2026-09-09", {}).get("甲歌") == 444.0,
              str(res_fixed.get("2026-09-09")))
        check("不产生 2026-09-10 行（昨日值不属于文件日本身）",
              "2026-09-10" not in res_fixed)

        # ---- B) 仅补"次日"文件（无 2026.09.09.xlsx）→ 9/8 空洞、9/9 到位 ----
        src2 = Path(td) / "synth_nextonly"
        src2.mkdir(parents=True)
        make_dayfile(src2, "2026.09.10.xlsx", [("甲歌", 444.0), ("乙歌", 555.0)])
        bm2 = load_ns(strip_fix=False)
        out_n = TEMP / "_attr_selftest_nextonly.csv"
        res_n = run_matrix(bm2, src2, out_n)
        print("[B] 只补次日文件时输出日期：%s" % sorted(res_n))
        check("只有 9/10 文件时：2026-09-09 到位", res_n.get("2026-09-09", {}).get("甲歌") == 444.0)
        check("只有 9/10 文件时：2026-09-08 仍缺（需真实 9/9 文件或准终值备用）",
              "2026-09-08" not in res_n)

        # ---- C) 原始（未修正）映射对照：值会挂到文件名日本身 ----
        bm3 = load_ns(strip_fix=True)        # 真正的未修正口径（源码文本剥掉补丁行）
        out_bug = TEMP / "_attr_selftest_buggy.csv"
        res_bug = run_matrix(bm3, src, out_bug)
        print("[C] 未修正映射输出日期：%s" % sorted(res_bug))
        check("未修正映射会把 9/9 的昨日值错挂到 2026-09-09",
              res_bug.get("2026-09-09", {}).get("甲歌") == 111.0,
              "（说明修正前的口径确实晚一天）")

        report = {"fixed": {k: v for k, v in res_fixed.items()},
                  "next_only": {k: v for k, v in res_n.items()},
                  "unfixed": {k: v for k, v in res_bug.items()}}
        (TEMP / "mapping_attribution_selftest.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print("-" * 68)
    print("通过 %d 项 / 失败 %d 项" % (len(PASS), len(FAIL)))
    for f in FAIL:
        print("  FAIL:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
