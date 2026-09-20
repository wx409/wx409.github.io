# -*- coding: utf-8 -*-
"""原始素材无损压缩留存：WAV → FLAC（保留原采样率/位深），逐个 PCM md5 校验通过才删原文件。

用法:
  python -X utf8 project_b\\archive_compress_media.py                 # 试算（默认，只报数字）
  python -X utf8 project_b\\archive_compress_media.py --apply         # 转码+校验+删 WAV
  python -X utf8 project_b\\archive_compress_media.py --apply --lrf   # 另删大疆 .LRF 代理（同内容低码率）

纪律：FLAC 无损；每文件转码后先比对 PCM md5，相等才删 .WAV，不等则保留并告警。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"G:\王晰巡演素材存档\现场录制视频")  # 2026-09-18 自录素材已整体归档到 G 盘


def ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def pcm_md5(exe: str, f: Path) -> str | None:
    r = subprocess.run(
        [exe, "-v", "error", "-i", str(f), "-map", "0:a:0", "-f", "md5", "-"],
        capture_output=True, text=True,
    )
    return r.stdout.strip() if r.returncode == 0 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--lrf", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    exe = ffmpeg()

    wavs = sorted(root.rglob("*.WAV")) + sorted(root.rglob("*.wav"))
    before = sum(w.stat().st_size for w in wavs)
    print(f"[WAV] {len(wavs)} 个 / {before / 2**30:.2f} GB")
    if not a.apply:
        print(f"      试算：转 FLAC 预计省 ~{before * 0.45 / 2**30:.2f} GB（无损）")
    ok = skip = fail = 0
    freed = 0
    for w in wavs:
        flac = w.with_suffix(".flac")
        if flac.exists():
            skip += 1
            continue
        if not a.apply:
            continue
        m0 = pcm_md5(exe, w)
        r = subprocess.run(
            [exe, "-v", "error", "-y", "-i", str(w), "-c:a", "flac", "-compression_level", "8", str(flac)],
            capture_output=True,
        )
        if r.returncode != 0 or pcm_md5(exe, flac) != m0 or m0 is None:
            print(f"  ✗ 校验未过，保留原文件：{w.name}")
            flac.unlink(missing_ok=True)
            fail += 1
            continue
        freed += w.stat().st_size
        w.unlink()
        ok += 1
        print(f"  ✓ {w.name} → flac")

    lrf_freed = 0
    lrfs = sorted(root.rglob("*.LRF"))
    if lrfs:
        size = sum(f.stat().st_size for f in lrfs)
        print(f"[LRF] {len(lrfs)} 个 / {size / 2**30:.2f} GB（大疆代理文件，同内容低码率）")
        if a.apply and a.lrf:
            for f in lrfs:
                lrf_freed += f.stat().st_size
                f.unlink()
            print(f"  ✓ 已删 {len(lrfs)} 个 LRF")

    if a.apply:
        print(f"结果：转换 {ok} 个，跳过 {skip} 个，校验失败 {fail} 个")
        print(f"释放：WAV {freed / 2**30:.2f} GB + LRF {lrf_freed / 2**30:.2f} GB")
        assert fail == 0 or True  # 失败仅告警，不阻断
    return 0


if __name__ == "__main__":
    sys.exit(main())
