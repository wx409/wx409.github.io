# -*- coding: utf-8 -*-
"""大疆等原始 MP4 省空间留存：HEVC 重编码（视频有损、**音频 bit-exact 保留**）。

逐文件闸门（三者全过才替换原件，否则保留原 MP4 并告警）：
  1. 音频流 md5 与原文件一致
  2. 前 60s PSNR ≥ --psnr-min（默认 40 dB）
  3. 产物体积 < 原件的 70%

用法:
  python -X utf8 project_b\\archive_reencode_hevc.py                 # 试算
  python -X utf8 project_b\\archive_reencode_hevc.py --apply         # 逐个替换
  python -X utf8 project_b\\archive_reencode_hevc.py --apply --cq 24 # 更保真（体积更大）

产物台账：temp\\hevc_manifest.json；原件不备份（替换后再无原始码流，故闸门从严）。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"G:\王晰巡演素材存档\现场录制视频")  # 2026-09-18 自录素材已整体归档到 G 盘
MANIFEST = Path(__file__).resolve().parent.parent / "temp" / "hevc_manifest.json"
SKIP_PARTS = ("_hevc",)


def ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def amd5(exe: str, f: Path) -> str | None:
    r = subprocess.run([exe, "-v", "error", "-i", str(f), "-map", "0:a:0", "-f", "md5", "-"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def psnr(exe: str, a: Path, b: Path, secs: int = 60) -> float | None:
    r = subprocess.run([exe, "-t", str(secs), "-i", str(a), "-t", str(secs), "-i", str(b),
                        "-lavfi", "[0:v][1:v]psnr", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"average:([\d.]+)", r.stderr)
    return float(m.group(1)) if m else None


def encode(exe: str, src: Path, dst: Path, cq: int) -> str:
    base = [exe, "-v", "error", "-y", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0",
            "-c:a", "copy", "-movflags", "+faststart", str(dst)]
    r = subprocess.run(base[:1] + ["-v", "error", "-y", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0",
                                   "-c:v", "hevc_nvenc", "-preset", "p5", "-cq", str(cq),
                                   "-tag:v", "hvc1", "-c:a", "copy", "-movflags", "+faststart", str(dst)],
                       capture_output=True, text=True)
    if r.returncode == 0 and dst.exists():
        return "hevc_nvenc"
    r = subprocess.run(base[:1] + ["-v", "error", "-y", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0",
                                   "-c:v", "libx265", "-crf", str(cq), "-preset", "medium",
                                   "-tag:v", "hvc1", "-c:a", "copy", "-movflags", "+faststart", str(dst)],
                       capture_output=True, text=True)
    return "libx265" if dst.exists() else f"FAILED:{r.stderr[-200:]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--cq", type=int, default=26)
    ap.add_argument("--psnr-min", type=float, default=40.0)
    a = ap.parse_args()
    exe = ffmpeg()
    srcs = [p for p in sorted(Path(a.root).rglob("*.MP4")) if not any(s in p.stem for s in SKIP_PARTS)]
    total = sum(p.stat().st_size for p in srcs)
    print(f"待处理 {len(srcs)} 个 / {total / 2**30:.2f} GB｜模式 {'APPLY' if a.apply else '试算'}")
    if not a.apply:
        return 0

    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []
    freed = 0.0
    for i, src in enumerate(srcs, 1):
        s0 = src.stat().st_size
        if s0 < 50 * 2**20:  # 已很小，无收益
            continue
        dst = src.with_name(src.stem + "_hevc.mp4")
        t0 = time.time()
        codec = encode(exe, src, dst, a.cq)
        if not dst.exists():
            print(f"  ✗ [{i}/{len(srcs)}] 编码失败：{src.name} {codec}")
            continue
        s1 = dst.stat().st_size
        ok_audio = amd5(exe, src) == amd5(exe, dst)
        p = psnr(exe, src, dst)
        gate = ok_audio and (p or 0) >= a.psnr_min and s1 < s0 * 0.7
        if not gate:
            print(f"  ✗ [{i}/{len(srcs)}] 闸门未过（音频一致={ok_audio} PSNR={p} 体积比={s1 / s0:.2f}），保留原件")
            dst.unlink(missing_ok=True)
            continue
        src.unlink()
        dst.rename(src)
        freed += s0 - s1
        man.append({"file": src.name, "orig_gb": round(s0 / 2**30, 3), "new_gb": round(s1 / 2**30, 3),
                    "ratio": round(s1 / s0, 3), "psnr60s": p, "codec": codec,
                    "min": round((time.time() - t0) / 60, 1)})
        MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  ✓ [{i}/{len(srcs)}] {src.name} {s0 / 2**30:.2f}→{s1 / 2**30:.2f} GB "
              f"({1 - s1 / s0:.0%}) PSNR {p} {codec} {man[-1]['min']}min")

    print(f"完成：累计释放 {freed / 2**30:.2f} GB｜台账 {MANIFEST}")
    assert all(m["orig_gb"] > m["new_gb"] for m in man)  # 台账只应记录真的变小了
    return 0


if __name__ == "__main__":
    sys.exit(main())
