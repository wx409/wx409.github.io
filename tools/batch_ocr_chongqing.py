#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量 OCR repo 截图。默认使用 C:\\Users\\yezhe\\.EasyOCR 模型目录。"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

DEFAULT_MODEL = Path(r"C:\Users\yezhe\.EasyOCR")
SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def run_ocr(image: Path, reader) -> str:
    lines = reader.readtext(str(image), detail=0, paragraph=True)
    return "\n".join(lines).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="重庆站 repo 图片 OCR")
    parser.add_argument("input", help="图片文件或文件夹")
    parser.add_argument(
        "-o",
        "--output",
        default="data/chongqing2026_ocr/text",
        help="输出 txt 目录",
    )
    parser.add_argument(
        "--model-dir",
        default=str(DEFAULT_MODEL),
        help="EasyOCR 模型目录",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    os.chdir(root)

    try:
        import easyocr
    except ImportError:
        print("请先安装: pip install easyocr pillow")
        sys.exit(1)

    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        print(f"[!] 模型目录不存在: {model_dir}")
        print("    EasyOCR 首次运行会自动下载到该目录")

    reader = easyocr.Reader(
        ["ch_sim", "en"],
        gpu=False,
        model_storage_directory=str(model_dir),
    )

    target = Path(args.input)
    images = (
        [target]
        if target.is_file()
        else sorted(p for p in target.rglob("*") if p.suffix.lower() in SUPPORTED)
    )
    if not images:
        print(f"[X] 未找到图片: {target}")
        sys.exit(1)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    for img in images:
        try:
            text = run_ocr(img, reader)
            out = out_dir / f"{img.stem}.txt"
            out.write_text(f"# {img.name}\n\n{text}\n", encoding="utf-8")
            print(f"[✓] {img.name} -> {out.name} ({len(text)} 字)")
        except Exception as e:
            print(f"[!] {img.name}: {e}")

    merged = out_dir / "ALL_MERGED.txt"
    parts = []
    for txt in sorted(out_dir.glob("*.txt")):
        if txt.name == "ALL_MERGED.txt":
            continue
        parts.append(f"## {txt.stem}\n\n{txt.read_text(encoding='utf-8').strip()}\n")
    merged.write_text("\n".join(parts), encoding="utf-8")
    print(f"[✓] 合并 -> {merged}")


if __name__ == "__main__":
    main()
