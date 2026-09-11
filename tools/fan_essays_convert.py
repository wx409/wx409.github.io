# -*- coding: utf-8 -*-
"""歌迷赏析：本地批量转 Markdown + 生成索引（全文仅本地，不进公开仓库）。

- .docx  → markitdown（已装）
- .wps   → LibreOffice headless 转 .docx 再 markitdown（本机 C:\\Program Files\\LibreOffice）
输出：
  <源目录>\\_转换_markdown\\*.md        全文（本地留存）
  <源目录>\\_转换_markdown\\_index.json 索引（供 project_b/build_fan_essays.py 读取）

用法：python -X utf8 tools/fan_essays_convert.py [--src "<源目录>"] [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DEFAULT_SRC = Path(r"E:\wx\论文素材_王晰作传\歌迷文章（含已发表）\2026年9月")
SOFFICE = Path(r"C:\Program Files\LibreOffice\program\soffice.exe")


def to_markdown(f: Path, out: Path, force: bool) -> bool:
    if out.exists() and not force:
        return True
    src = f
    tmp = None
    if f.suffix.lower() == ".wps":
        if not SOFFICE.exists():
            print(f"   ⚠ 需要 LibreOffice 才能转 .wps：{f.name}")
            return False
        d = Path(tempfile.mkdtemp(prefix="wps_"))
        r = subprocess.run([str(SOFFICE), "--headless", "--convert-to", "docx", "--outdir", str(d), str(f)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        cand = list(d.glob("*.docx"))
        if not cand:
            print(f"   ✗ .wps 转换失败：{f.name}｜{(r.stderr or '')[-80:]}")
            return False
        src, tmp = cand[0], d
    r = subprocess.run([sys.executable, "-m", "markitdown", str(src), "-o", str(out)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return r.returncode == 0 and out.exists()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    src = Path(a.src)
    out_dir = src.parent / "_转换_markdown"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for f in sorted(src.glob("*")):
        if f.suffix.lower() not in (".docx", ".wps") or f.name.startswith("~$") or "目录" in f.name:
            continue
        md = out_dir / (f.stem + ".md")
        if not to_markdown(f, md, a.force):
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        body = re.sub(r"\s+", " ", text)
        title = next((l.strip() for l in text.splitlines()
                      if len(l.strip()) > 4 and not l.strip().startswith(("*", "【", "#", "|"))), "")
        song = re.sub(r"^\d+", "", f.stem)
        song = re.sub(r"(王晰|Vitas|&|李琦|鞠红川)", "", song).replace("赏析", "").strip(" 《》&")
        rows.append({"file": f.name, "ext": f.suffix.lower(), "song": song,
                     "title": re.sub(r"\s+", " ", title)[:80], "chars": len(body),
                     "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d"),
                     "published_hint": bool(re.search(r"已发表|刊载|发表|公众号|知乎|豆瓣", text)),
                     "author_hint": (re.findall(r"作者[：:]\s*([^\s，。]{2,12})", text) or [""])[0],
                     "slug": f.stem, "md": str(md)})
    idx = out_dir / "_index.json"
    idx.write_text(json.dumps({"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                               "note": "歌迷赏析本地索引（全文仅本地，站点不转载）",
                               "count": len(rows), "items": rows}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"[OK] 转换/索引 {len(rows)} 篇 → {idx}")
    print("下一步：python -X utf8 project_b/build_fan_essays.py && project_b/build_academic.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
