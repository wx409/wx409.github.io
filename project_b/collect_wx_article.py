# -*- coding: utf-8 -*-
"""微信公众号文章本地留存 + 离线 OCR —— 一条命令把「官宣/开票/开演」原文变成可检索的 Markdown。

为什么需要它：公众号文章正文常是**图片**（海报/长图），直接抓 HTML 只有标题和推荐位，
正文读不到。本脚本把图片抓到本地、用**本机离线 OCR** 识别，再拼成人读 Markdown，
原文 HTML 与图片一并归档（内容不出本机）。

OCR 引擎分工（2026-09-11 实测）：
  got    —— GOT-OCR2.0，1–3 秒/图，纯文本，适合海报速读（默认）
  mineru —— MinerU 3.4.5，首图约 48 秒（含模型加载），保留版面/表格/公式，适合信息密集长图

归档位置（默认）：E:\\wx\\论文素材_王晰作传\\原始材料\\微信文章\\<日期>_<标题>\\
  article.html   原文快照
  imgs/          正文图片
  ocr/           逐图 OCR 文本
  <日期>_<标题>.md   汇总 Markdown（含标题/发布时间/原文链接/正文）

用法：
  python -X utf8 project_b/collect_wx_article.py <url>
  python -X utf8 project_b/collect_wx_article.py <url> --engine mineru
  python -X utf8 project_b/collect_wx_article.py <url> --out "D:\\temp\\wx" --no-images
"""
from __future__ import annotations

import argparse
import html as H
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = Path(r"E:\wx\论文素材_王晰作传\原始材料\微信文章")
GOT_PY = r"D:\AI\GOT-OCR\venv\Scripts\python.exe"
GOT_BATCH = r"D:\AI\GOT-OCR\batch_ocr.py"
MINERU_EXE = r"D:\AI\MinerU-venv\Scripts\mineru.exe"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Referer": "https://mp.weixin.qq.com/"}


def fetch(url: str) -> str:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45).read().decode("utf-8", "replace")


def parse_article(h: str) -> dict:
    title = ""
    m = re.search(r'<meta property="og:title" content="([^"]*)"', h) or re.search(r'id="activity-name"[^>]*>\s*([^<]+)', h)
    if m:
        title = H.unescape(m.group(1)).strip()
    pub = ""
    m = re.search(r'var ct = "(\d+)"', h) or re.search(r'var create_time = "(\d+)"', h)
    if m:
        pub = datetime.fromtimestamp(int(m.group(1))).strftime("%Y-%m-%d %H:%M")
    account = ""
    m = re.search(r'var nickname\s*=\s*"([^"]*)"', h) or re.search(r'id="js_name"[^>]*>\s*([^<]+)', h)
    if m:
        account = H.unescape(m.group(1)).strip()
    body = ""
    m = re.search(r'id="js_content".*?</div>\s*(?=<script|<div id="js_tags)', h, re.S)
    if m:
        body = m.group(0)
    urls = re.findall(r'data-src="(https://mmbiz\.qpic\.cn/[^"]+)"', body or h)
    if not urls:
        urls = re.findall(r'(https://mmbiz\.qpic\.cn/mmbiz_[^"\'\s\\]+)', body or h)
    seen, imgs = set(), []
    for u in urls:
        u = u.replace("&amp;", "&")
        if u not in seen:
            seen.add(u)
            imgs.append(u)
    # 正文纯文字（图片型文章通常为空，非图片型文章可直接用）
    text = ""
    if m:
        t = re.sub(r"<[^>]+>", "\n", m.group(0))
        text = "\n".join(x.strip() for x in t.split("\n") if x.strip())
    return {"title": title, "published": pub, "account": account, "images": imgs, "text": text}


def slug(s: str, n: int = 40) -> str:
    s = re.sub(r'[\\/:*?"<>|\r\n]', "_", s).strip()
    return s[:n] or "article"


def ocr_got(img_dir: Path, txt_dir: Path) -> dict[str, str]:
    txt_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([GOT_PY, GOT_BATCH, "--input", str(img_dir), "--output", str(txt_dir)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = {}
    for f in sorted(txt_dir.glob("*.txt")):
        t = f.read_text(encoding="utf-8", errors="replace")
        t = re.sub(r"^#.*?\n(#.*\n)*", "", t)          # 去掉 GOT 的头部注释块
        out[f.stem] = t.strip()
    if not out:
        raise RuntimeError(f"GOT-OCR 未产出文本：{(r.stderr or r.stdout or '')[-400:]}")
    return out


def ocr_mineru(img_dir: Path, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([MINERU_EXE, "-p", str(img_dir), "-o", str(out_dir)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    got = {}
    for f in sorted(out_dir.glob("**/*.md")):
        got[f.stem] = f.read_text(encoding="utf-8", errors="replace").strip()
    if not got:
        raise RuntimeError(f"MinerU 未产出文本：{(r.stderr or r.stdout or '')[-400:]}")
    return got


def main() -> int:
    ap = argparse.ArgumentParser(description="公众号文章本地留存 + 离线 OCR")
    ap.add_argument("url")
    ap.add_argument("--engine", default="got", choices=["got", "mineru"])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--no-images", action="store_true", help="不下载图片（只存 HTML 快照）")
    a = ap.parse_args()

    h = fetch(a.url)
    info = parse_article(h)
    day = (info["published"] or datetime.now().strftime("%Y-%m-%d"))[:10]
    base = Path(a.out) / f"{day}_{slug(info['title'])}"
    (base / "imgs").mkdir(parents=True, exist_ok=True)
    (base / "article.html").write_text(h, encoding="utf-8")

    texts: dict[str, str] = {}
    if info["images"] and not a.no_images:
        for i, u in enumerate(info["images"], 1):
            dst = base / "imgs" / f"{i:02d}.jpg"
            if dst.exists():
                continue
            try:
                dst.write_bytes(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
            except Exception as e:
                print(f"  [WARN] 图片 {i} 下载失败 {type(e).__name__}")
        try:
            texts = ocr_got(base / "imgs", base / "ocr") if a.engine == "got" else ocr_mineru(base / "imgs", base / "ocr_mineru")
        except Exception as e:
            print(f"  [FAIL] OCR：{e}")
    elif info["text"]:
        texts = {"html_text": info["text"]}

    md = [f"# {info['title']}", "",
          f"- 发布：{info['published'] or '—'}｜公众号：{info['account'] or '—'}",
          f"- 原文：{a.url}",
          f"- 留存：{base}",
          f"- OCR 引擎：{a.engine if info['images'] else '无需（正文为文字）'}｜图片 {len(info['images'])} 张", ""]
    if info["text"]:
        md += ["## 正文（HTML 文本层）", "", info["text"], ""]
    if texts:
        md += ["## 正文（离线 OCR 逐图）", ""]
        for k in sorted(texts):
            if texts[k].strip():
                md += [f"### {k}", "", texts[k], ""]
    (base / f"{day}_{slug(info['title'])}.md").write_text("\n".join(md), encoding="utf-8")
    (base / "meta.json").write_text(json.dumps({
        "title": info["title"], "published": info["published"], "account": info["account"],
        "url": a.url, "images": info["images"], "engine": a.engine,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"[OK] {info['title']}")
    print(f"     发布 {info['published']}｜公众号 {info['account']}｜图片 {len(info['images'])} 张｜OCR {len(texts)} 段")
    print(f"[OK] {base}\\{day}_{slug(info['title'])}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
