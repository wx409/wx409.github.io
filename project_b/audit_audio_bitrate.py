# -*- coding: utf-8 -*-
"""存量音源码率审计：不信标称，逐文件算真实码率（平均码率 = 字节数×8 ÷ 时长）。

为什么要审：2026-09-10 发现 QQ 音乐 M500 档实际只给 128kbps，而白皮书/llms/voice/stage/论文 9.4
都写着「QQ音乐 320k 官方音源」。**读数大概率不受影响**（128k 压的是高频段，60–90Hz 基频段存活），
但「320k」这句话是**元数据声明**，错就是错——必须先拿到全貌再决定重跑范围。

用法：
  python -X utf8 project_b/audit_audio_bitrate.py                 # 扫默认根目录
  python -X utf8 project_b/audit_audio_bitrate.py --root <dir> ... # 指定根目录
输出：temp/码率审计_<日期>.json / .md
"""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "temp"
EXT = {".mp3", ".flac", ".m4a", ".wav", ".ape", ".wma"}

DEFAULT_ROOTS = [
    Path(r"E:\wx\论文素材_王晰作传\音域分析\专辑音频"),
    Path(r"E:\wx\论文素材_王晰作传\音域分析\qqmusic下载"),
    Path(r"E:\wx\论文素材_王晰作传\音域分析\向着太阳重测\音源"),
    Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频"),
    Path(r"E:\wx\论文素材_王晰作传\音域分析\他人主导\音频"),
]


def ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def duration_s(p: Path) -> float | None:
    """时长：先试 soundfile，失败再用 ffmpeg -i 解析。"""
    try:
        import soundfile as sf
        return float(sf.info(str(p)).duration)
    except Exception:
        pass
    try:
        r = subprocess.run([ffmpeg(), "-i", str(p)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        for line in (r.stderr or "").splitlines():
            if "Duration:" in line:
                t = line.split("Duration:")[1].split(",")[0].strip()
                hh, mm, ss = t.split(":")
                return int(hh) * 3600 + int(mm) * 60 + float(ss)
    except Exception:
        pass
    return None


def scan(root: Path, limit: int = 0) -> list[dict]:
    rows = []
    if not root.exists():
        return rows
    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in EXT and p.is_file())
    if limit:
        files = files[:limit]
    for p in files:
        dur = duration_s(p)
        size = p.stat().st_size
        kbps = round(size * 8 / dur / 1000, 1) if dur and dur > 0 else None
        rows.append({"path": str(p.relative_to(root)), "root": root.name,
                     "ext": p.suffix.lower(), "mb": round(size / 1048576, 2),
                     "duration_s": round(dur, 1) if dur else None, "kbps_actual": kbps})
    return rows


def bucket(kbps: float | None) -> str:
    if kbps is None:
        return "未知"
    if kbps >= 900:
        return "无损(≥900)"
    if kbps >= 256:
        return "320k 档(256–460)"
    if kbps >= 180:
        return "192k 档(180–255)"
    if kbps >= 100:
        return "128k 档(100–179)"
    return "低码率(<100)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append", default=[])
    ap.add_argument("--limit", type=int, default=0, help="每个根目录只扫前 N 个（调试用）")
    args = ap.parse_args()
    roots = [Path(r) for r in args.root] or DEFAULT_ROOTS

    all_rows: list[dict] = []
    for r in roots:
        rows = scan(r, args.limit)
        print(f"  {r} → {len(rows)} 个音频文件")
        all_rows += rows

    from collections import Counter
    per_root: dict[str, Counter] = {}
    for row in all_rows:
        per_root.setdefault(row["root"], Counter())[bucket(row["kbps_actual"])] += 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    payload = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
               "method": "平均码率 = 文件字节数×8 ÷ 时长（不信标称档位）",
               "roots": [str(r) for r in roots],
               "counts": {k: dict(v) for k, v in per_root.items()},
               "total": len(all_rows), "rows": all_rows}
    (OUT_DIR / f"码率审计_{stamp}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["# 存量音源码率审计（不信标称，逐文件实测）", "",
         f"> 生成：{payload['generated_at']}｜方法：{payload['method']}",
         f"> 文件总数：{len(all_rows)}", "", "## 总览", "",
         "| 根目录 | " + " | ".join(["无损(≥900)", "320k 档", "192k 档", "128k 档", "低码率", "未知"]) + " |",
         "|---" * 7 + "|"]
    order = ["无损(≥900)", "320k 档(256–460)", "192k 档(180–255)", "128k 档(100–179)", "低码率(<100)", "未知"]
    for name, c in per_root.items():
        L.append(f"| {name} | " + " | ".join(str(c.get(k, 0)) for k in order) + " |")
    low = [r for r in all_rows if (r["kbps_actual"] or 0) < 256]
    L += ["", f"## 低于 320k 档的文件（{len(low)} / {len(all_rows)}）", ""]
    if low:
        L += ["| 根目录 | 文件 | 实测 kbps | 时长 |", "|---|---|---|---|"]
        for r in sorted(low, key=lambda x: (x["root"], x["kbps_actual"] or 0))[:120]:
            L.append(f"| {r['root']} | {r['path']} | {r['kbps_actual']} | {r['duration_s']}s |")
        if len(low) > 120:
            L.append(f"| … | （其余 {len(low)-120} 条见 json） | | |")
    (OUT_DIR / f"码率审计_{stamp}.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"\n[OK] 共 {len(all_rows)} 个文件；低于 320k 档 {len(low)} 个")
    for name, c in per_root.items():
        print(f"   {name}: " + "｜".join(f"{k} {c.get(k,0)}" for k in order if c.get(k)))
    print(f"报告：temp/码率审计_{stamp}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
