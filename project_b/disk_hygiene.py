#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定期磁盘保洁（默认只报告；--apply 才清理）。

设计原则：**只清理"能证明是冗余"的东西**，任何拿不准的一律保留并写进报告。

清理项（按证据强度排序）
  1. input_ascii.wav 冗余副本
     demucs 为了绕开 CJK 路径会把源片段复制成 input_ascii.wav，分离后即无用。
     判定：源树里存在**字节数相同**的候选，且 MD5 **完全一致** → 删。
     找不到同哈希源的一律保留（那是该录音唯一的原始混音）。
  2. __pycache__ / *.pyc
  3. *.tmp / *.temp
  4. 陈旧 *.bak*（>90 天）——**只报告不删**，因为可能是人工留的救命备份

报告与告警
  · 每次运行写 temp/disk_hygiene_报告_<日期>.md
  · E 盘空闲低于 --warn-gb（默认 150）时在报告里标红

用法
  python -X utf8 project_b/disk_hygiene.py                  # 只报告
  python -X utf8 project_b/disk_hygiene.py --apply          # 执行清理
  python -X utf8 project_b/disk_hygiene.py --apply --warn-gb 120
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
AUDIO = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")
SCAN_ROOTS = [Path(r"E:\wx"), ROOT]
REPORT_DIR = ROOT / "temp"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", ".next"}

# 并发护栏（2026-11-08 加）：
# `批量专辑音域.py::separate_vocals` 会先 sanitize_filename() 创建 input_ascii.wav，
# 再判断 vocals.wav 是否已存在；tools/analyze.py::separate 同样先复制后短路。
# 也就是说「分离进行中」的那一刻，input_ascii.wav 同样满足"与源文件 MD5 一致"，
# 只按哈希删会把人正在跑的任务打断。因此加两道门：
#   · 分离已产出 vocals.wav（这次分离确实已经用完输入）
#   · 文件 mtime 超过 24 小时（避开正在复制/正在分离的时间窗）
MIN_AGE_H = 24

# 重点目录的「体积预算」：超过阈值就在报告里标红。
# 这些是"新素材必然要占的空间"，不能自动删——但必须让人在爆之前看见。
WATCH = [
    (Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频"), 300.0),
    (Path(r"E:\wx\论文素材_王晰作传\_staging_现场"), 60.0),
    (Path(r"E:\wx\论文素材_王晰作传\_staging_现场_分离"), 90.0),
    (Path(r"E:\wx\论文素材_王晰作传\现场录音-小卡带"), 130.0),
    (Path(r"E:\wx\index_records\raw_archive"), 25.0),
]


def _separation_done(p: Path) -> bool:
    """分离产物已落盘 = 这份 input_ascii.wav 的使命已经结束。"""
    return (p.parent / "htdemucs" / "input_ascii" / "vocals.wav").is_file()


def md5(p: Path) -> str | None:
    h = hashlib.md5()
    try:
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 22), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def disk_free() -> dict[str, float]:
    out = {}
    for d in "CDEF":
        try:
            u = shutil.disk_usage(f"{d}:\\")
            out[d] = round(u.free / 1024 ** 3, 2)
        except OSError:
            pass
    return out


def find_input_ascii_dupes() -> tuple[list[Path], int, int]:
    """返回（可删列表, 保留字节数, 因并发护栏而暂缓的个数）。

    只对"源树里有同尺寸候选"的文件做 MD5；无候选的直接跳过（不读盘）。
    """
    if not AUDIO.is_dir():
        return [], 0, 0
    inputs = sorted(AUDIO.rglob("input_ascii.wav"))
    idx_cache: dict[str, dict[int, list[Path]]] = {}

    def index_for(root: Path) -> dict[int, list[Path]]:
        key = str(root)
        if key not in idx_cache:
            idx: dict[int, list[Path]] = {}
            if root.is_dir():
                for p in root.rglob("*.wav"):
                    if p.name in ("input_ascii.wav", "vocals.wav"):
                        continue
                    try:
                        idx.setdefault(p.stat().st_size, []).append(p)
                    except OSError:
                        pass
            idx_cache[key] = idx
        return idx_cache[key]

    dupes, keep_bytes, busy = [], 0, 0
    for p in inputs:
        try:
            st = p.stat()
        except OSError:
            continue
        sz = st.st_size
        # —— 并发护栏：正在分离 / 刚生成的，一律放过 ——
        if not _separation_done(p) or (time.time() - st.st_mtime) / 3600 < MIN_AGE_H:
            keep_bytes += sz
            busy += 1
            continue
        top = p.relative_to(AUDIO).parts[0]
        src_top = top[:-3] if top.endswith("_分离") else top
        cands = index_for(AUDIO / src_top).get(sz, [])
        if not cands:
            keep_bytes += sz
            continue
        h1 = md5(p)
        if h1 and any(md5(c) == h1 for c in cands):
            dupes.append(p)
        else:
            keep_bytes += sz
    return dupes, keep_bytes, busy


def find_caches() -> list[Path]:
    out = []
    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            if Path(dp).name == "__pycache__":
                out.append(Path(dp))
                dns[:] = []
                continue
            for fn in fns:
                if fn.endswith((".pyc", ".tmp", ".temp")):
                    out.append(Path(dp) / fn)
    return out


def stale_baks(days: int = 90) -> list[Path]:
    cut = time.time() - days * 86400
    out = []
    if not Path(r"E:\wx").is_dir():
        return out
    for dp, dns, fns in os.walk(Path(r"E:\wx")):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if ".bak" in fn or fn.endswith(".tmp"):
                p = Path(dp) / fn
                try:
                    if p.stat().st_mtime < cut:
                        out.append(p)
                except OSError:
                    pass
    return out


def size_of(ps: list[Path]) -> int:
    total = 0
    for p in ps:
        try:
            if p.is_dir():
                for dp, _, fns in os.walk(p):
                    for fn in fns:
                        try:
                            total += (Path(dp) / fn).stat().st_size
                        except OSError:
                            pass
            else:
                total += p.stat().st_size
        except OSError:
            pass
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--warn-gb", type=float, default=150.0)
    a = ap.parse_args()

    free_before = disk_free()
    L = [f"# 磁盘保洁报告 {datetime.now():%Y-%m-%d %H:%M}", "",
         f"模式：**{'执行' if a.apply else '仅报告'}**", ""]

    L.append("## 磁盘水位")
    L.append("| 盘 | 空闲 GB | 状态 |")
    L.append("|---|---|---|")
    for d, gb in free_before.items():
        flag = "⚠️ 低于阈值" if d == "E" and gb < a.warn_gb else "正常"
        L.append(f"| {d}: | {gb} | {flag} |")
    L.append("")

    # 1) input_ascii 冗余
    dupes, keep_bytes, busy = find_input_ascii_dupes()
    dup_gb = size_of(dupes) / 1024 ** 3
    L += ["## 1. input_ascii.wav 冗余副本", "",
          f"- 可删除（MD5 与源文件完全一致）：**{len(dupes)}** 个 / {dup_gb:.2f} GB",
          f"- 保留（无同哈希源，属唯一副本）：{keep_bytes/1024**3:.2f} GB",
          f"- 暂缓（分离未完成或 24 小时内有过写入）：{busy} 个 —— 并发护栏", ""]

    # 2) 缓存
    caches = find_caches()
    cache_gb = size_of(caches) / 1024 ** 3
    L += ["## 2. Python 缓存 / 临时文件", "",
          f"- `__pycache__` / `*.pyc` / `*.tmp`：**{len(caches)}** 项 / {cache_gb:.3f} GB", ""]

    # 3) 陈旧备份
    baks = stale_baks()
    bak_gb = size_of(baks) / 1024 ** 3
    L += ["## 3. 陈旧备份（>90 天，仅报告不删）", "",
          f"- {len(baks)} 个 / {bak_gb:.3f} GB", ""]
    if baks:
        L.append("  示例：" + "、".join(f"`{p.name}`" for p in baks[:5]))
        L.append("")

    # 4) 重点目录体积预算（只报告，不删）
    L += ["## 4. 重点目录体积预算（只报告，不删）", "",
          "| 目录 | 实际 GB | 预算 GB | 状态 |", "|---|---|---|---|"]
    for path, budget in WATCH:
        if not path.exists():
            L.append(f"| `{path.name}` | — | {budget} | 不存在 |")
            continue
        gb = size_of([path]) / 1024 ** 3
        flag = "⚠️ 超预算" if gb > budget else "正常"
        L.append(f"| `{path.name}` | {gb:.1f} | {budget} | {flag} |")
    L.append("")

    reclaimed = 0
    if a.apply:
        for p in dupes:
            try:
                reclaimed += p.stat().st_size
                p.unlink()
            except OSError:
                reclaimed -= 0
        for p in caches:
            try:
                if p.is_dir():
                    reclaimed += size_of([p])
                    shutil.rmtree(p, ignore_errors=True)
                elif p.is_file():
                    reclaimed += p.stat().st_size
                    p.unlink()
            except OSError:
                pass
        L += ["## 执行结果", "",
              f"- 实际回收：**{reclaimed/1024**3:.2f} GB**", ""]

    free_after = disk_free()
    L += ["## 磁盘水位（结束时）", ""]
    for d, gb in free_after.items():
        L.append(f"- {d}: {gb} GB")
    L.append("")

    text = "\n".join(L)
    print(text)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rp = REPORT_DIR / f"disk_hygiene_报告_{datetime.now():%Y%m%d}.md"
    rp.write_text(text, encoding="utf-8")
    (REPORT_DIR / "disk_hygiene_last.json").write_text(json.dumps({
        "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "apply": a.apply,
        "input_ascii_dupes": len(dupes),
        "input_ascii_dupe_gb": round(dup_gb, 2),
        "caches": len(caches),
        "reclaimed_gb": round(reclaimed / 1024 ** 3, 2),
        "free_before": free_before,
        "free_after": free_after,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"报告：{rp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
