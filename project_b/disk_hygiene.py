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


def find_input_ascii_dupes() -> tuple[list[Path], int]:
    """返回（可删列表, 保留字节数）。只对"源树里有同尺寸候选"的做 MD5。"""
    if not AUDIO.is_dir():
        return [], 0
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

    dupes, keep_bytes = [], 0
    for p in inputs:
        try:
            sz = p.stat().st_size
        except OSError:
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
    return dupes, keep_bytes


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
    dupes, keep_bytes = find_input_ascii_dupes()
    dup_gb = size_of(dupes) / 1024 ** 3
    L += ["## 1. input_ascii.wav 冗余副本", "",
          f"- 可删除（MD5 与源文件完全一致）：**{len(dupes)}** 个 / {dup_gb:.2f} GB",
          f"- 保留（无同哈希源，属唯一副本）：{keep_bytes/1024**3:.2f} GB", ""]

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
