# -*- coding: utf-8 -*-
"""
微博网页快照生成器（本地 HTML 存档，供回溯，不进 git）
============================================================
从 weibo_archive（已抓的微博 json + 媒体）生成自包含 HTML 快照：
每条微博一个 .html 文件，含 文字/图片(引用本地)/视频(引用)/元数据/原链。

用途：live-reviews 网站只放纯文字（王晰本人）；本地快照留存完整内容供回溯。

用法：
  python tools/make_weibo_snapshot.py                       # 全量生成
  python tools/make_weibo_snapshot.py --once                # 增量(只生成没有快照的)
  输出：E:\wx\私有工具\weibo_snapshots\posts\2026\2026-08\<mid>.html
"""
import argparse
import json
import os
import re
from pathlib import Path

ARCHIVE = Path(r"E:\wx\私有工具\weibo_archive")
ARCHIVE_STUDIO = Path(r"E:\wx\私有工具\weibo_archive_studio")
SNAP_ROOT = Path(r"E:\wx\私有工具\weibo_snapshots")


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def find_media(root, rel):
    """记录里 file 相对路径可能与落盘路径不一致（缺年份段），按文件名递归找。"""
    if not rel:
        return ""
    cand = root / rel
    if os.path.exists(cand):
        return str(cand)
    base = os.path.basename(rel)
    matches = list(root.rglob(base))
    if matches:
        return str(matches[0])
    return ""


def build_html(rec, archive_root):
    mid = str(rec.get("id", ""))
    text = rec.get("text", "")
    text_html = rec.get("text_html", "")
    created = rec.get("created_at", "")
    date = rec.get("date", "")
    author = rec.get("screen_name", "")
    bid = rec.get("bid", "")
    counts = {
        "转发": rec.get("reposts_count"),
        "评论": rec.get("comments_count"),
        "点赞": rec.get("attitudes_count"),
    }
    # 图片
    pics_html = ""
    for p in rec.get("pics", []) or []:
        f = p.get("file", "")
        url = p.get("url", "")
        img_src = find_media(archive_root, f)
        if img_src:
            pics_html += f'<figure><img src="{esc(img_src)}" loading="lazy"><figcaption>{esc(os.path.basename(f))}</figcaption></figure>'
        else:
            pics_html += f'<figure><p>图片(未找到本地): <a href="{esc(url)}">{esc(url)}</a></p></figure>'
    # 视频
    vids_html = ""
    for v in rec.get("videos", []) or []:
        f = v.get("file", "")
        url = v.get("url", "")
        vid_src = find_media(archive_root, f)
        if vid_src:
            vids_html += f'<video controls preload="none" src="{esc(vid_src)}"></video>'
        else:
            vids_html += f'<p>视频(未找到本地): <a href="{esc(url)}">{esc(url)}</a></p>'
    # 转发/链接
    orig = f"https://weibo.com/{rec.get('uid','')}/{mid}" if rec.get("uid") else ""

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>微博快照 {mid}</title>
<style>body{{font-family:sans-serif;max-width:720px;margin:0 auto;padding:20px;background:#fafafa}}
.meta{{color:#888;font-size:13px}} .text{{white-space:pre-wrap;line-height:1.7}}
figure img{{max-width:100%;border-radius:8px}} figure{{margin:12px 0}}
video{{width:100%;border-radius:8px}} .counts{{margin-top:8px;font-size:13px;color:#555}}
a{{color:#1a56c4}}</style></head><body>
<h1>微博快照 #{esc(mid)}</h1>
<div class="meta">作者: {esc(author)} | 日期: {esc(date)} | 时间: {esc(created)} | bid: {esc(bid)}</div>
<div class="meta">计数: {' | '.join(k + (': ' + str(v) if v is not None else '') for k,v in counts.items())}</div>
<div class="text">{esc(text)}</div>
{pics_html}
{vids_html}
<div class="counts">原链: <a href="{esc(orig)}">{esc(orig)}</a></div>
<p class="meta">★ 本快照由 weibo_archive 本地留存生成（E:\\wx\\私有工具\\weibo_snapshots），供回溯。</p>
</body></html>"""


def walk_archive(root):
    """遍历 archive，返回 (json_path, rec, archive_root)"""
    out = []
    if not root.exists():
        return out
    for p in root.rglob("*.json"):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            if rec.get("id"):
                out.append((p, rec, root))
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="增量：只生成没有快照的")
    args = ap.parse_args()

    done = 0
    skip = 0
    for archive_root in (ARCHIVE, ARCHIVE_STUDIO):
        for json_path, rec, root in walk_archive(archive_root):
            mid = str(rec.get("id", ""))
            date = rec.get("date", "")[:7] or "unknown"
            snap_dir = SNAP_ROOT / "posts" / date
            snap_path = snap_dir / f"{mid}.html"
            if args.once and snap_path.exists():
                skip += 1
                continue
            snap_dir.mkdir(parents=True, exist_ok=True)
            # 媒体路径：archive json 里 file 是相对该 archive 根的
            html = build_html(rec, root)
            snap_path.write_text(html, encoding="utf-8")
            done += 1

    print(f"生成 {done} 份快照, 跳过 {skip} 条(已有)")
    print(f"快照目录: {SNAP_ROOT}")


if __name__ == "__main__":
    main()
