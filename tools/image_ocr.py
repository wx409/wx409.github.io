#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
王晰GEO站点 · 图片文字识别（OCR）

用途：把 repo 截图、歌单图里的文字转成 .txt，供 repo/2026.md 与现场实录引用。

用法：
  # 单张图片
  python tools/image_ocr.py path/to/image.jpg

  # 整个文件夹（批量）
  python tools/image_ocr.py data/chongqing2026_ocr/images/

  # 指定输出目录
  python tools/image_ocr.py image.jpg -o data/chongqing2026_ocr/text/

依赖（二选一，推荐 EasyOCR）：
  pip install pillow easyocr
  # 或
  pip install pillow paddlepaddle paddleocr

可选（识别率更高，需 API）：
  设置环境变量 DEEPSEEK_API_KEY，加 --api 使用 DeepSeek 视觉模型
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def log(msg: str) -> None:
    print(msg, flush=True)


def image_to_base64(path: Path) -> str:
    data = path.read_bytes()
    ext = path.suffix.lower().lstrip(".")
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{base64.b64encode(data).decode()}"


def ocr_easyocr(path: Path) -> str:
    import easyocr

    reader = easyocr.Reader(["ch_sim", "en"], gpu=False)
    lines = reader.readtext(str(path), detail=0, paragraph=True)
    return "\n".join(lines).strip()


def ocr_paddle(path: Path) -> str:
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    result = ocr.ocr(str(path), cls=True)
    lines = []
    for block in result or []:
        for line in block or []:
            if line and len(line) > 1:
                lines.append(line[1][0])
    return "\n".join(lines).strip()


def ocr_deepseek(path: Path) -> str:
    import requests

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY，无法使用 --api 模式")

    b64 = image_to_base64(path)
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "请识别这张图片中的全部中文和英文文字，按阅读顺序输出。"
                                "若是歌单，请每行一首歌名；保留序号和标注（如「第几次唱」）。"
                                "只输出识别文字，不要解释。"
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": b64}},
                    ],
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def pick_engine(prefer: str) -> str:
    if prefer != "auto":
        return prefer
    try:
        import easyocr  # noqa: F401

        return "easyocr"
    except ImportError:
        pass
    try:
        import paddleocr  # noqa: F401

        return "paddle"
    except ImportError:
        pass
    return "none"


def run_ocr(path: Path, engine: str, use_api: bool) -> str:
    if use_api:
        return ocr_deepseek(path)
    if engine == "easyocr":
        return ocr_easyocr(path)
    if engine == "paddle":
        return ocr_paddle(path)
    raise RuntimeError(
        "未安装 OCR 库。请运行: pip install easyocr pillow\n"
        "或设置 DEEPSEEK_API_KEY 后加 --api"
    )


def process_one(path: Path, out_dir: Path, engine: str, use_api: bool) -> Path:
    text = run_ocr(path, engine, use_api)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.txt"
    header = f"# OCR 来源: {path.name}\n\n"
    out_path.write_text(header + text + "\n", encoding="utf-8")
    log(f"[✓] {path.name} -> {out_path.name} ({len(text)} 字)")
    return out_path


def collect_images(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() in SUPPORTED else []
    return sorted(
        p for p in target.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED
    )


def merge_all_text(out_dir: Path) -> Path:
    """合并所有 OCR 结果为一份歌单汇总（供人工校对）"""
    parts = []
    for txt in sorted(out_dir.glob("*.txt")):
        if txt.name == "ALL_MERGED.txt":
            continue
        parts.append(f"## {txt.stem}\n\n{txt.read_text(encoding='utf-8').strip()}\n")
    merged = out_dir / "ALL_MERGED.txt"
    merged.write_text("\n".join(parts), encoding="utf-8")
    log(f"[✓] 已合并 -> {merged}")
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="repo 图片 OCR 转文字")
    parser.add_argument("input", help="图片文件或文件夹")
    parser.add_argument(
        "-o",
        "--output",
        default="data/chongqing2026_ocr/text",
        help="输出目录（默认 data/chongqing2026_ocr/text）",
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "easyocr", "paddle"],
        default="auto",
        help="本地 OCR 引擎",
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="使用 DeepSeek 视觉 API（需 DEEPSEEK_API_KEY）",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="完成后合并全部 txt 为 ALL_MERGED.txt",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    os.chdir(root)

    target = Path(args.input)
    if not target.exists():
        log(f"[X] 路径不存在: {target}")
        sys.exit(1)

    out_dir = Path(args.output)
    engine = pick_engine(args.engine)
    if engine == "none" and not args.api:
        log("[X] 请安装 easyocr 或使用 --api")
        sys.exit(1)

    images = collect_images(target)
    if not images:
        log(f"[X] 未找到图片: {target}")
        sys.exit(1)

    log(f"共 {len(images)} 张图片 | 引擎: {'deepseek-api' if args.api else engine}")
    for img in images:
        try:
            process_one(img, out_dir, engine, args.api)
        except Exception as e:
            log(f"[!] {img.name} 失败: {e}")

    if args.merge:
        merge_all_text(out_dir)

    log("\n下一步：人工校对 ALL_MERGED.txt，把歌单写入 repo/2026.md")


if __name__ == "__main__":
    main()
