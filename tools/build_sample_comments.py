# -*- coding: utf-8 -*-
"""演出场次样本·评论全文+图片整合（本地私有，不进 git、不上公开站）
把已抓取的微博/小红书/B站/网页反馈全文与图片归档到 <show_dir>\评论全文\、<show_dir>\图片\
用法：
  python tools/build_sample_comments.py --date 2026-08-23 --city 广州
  python tools/build_sample_comments.py --show-dir "E:\wx\六巡\20260823广州站"
"""
import argparse, glob, io, json, os, re, sys
from datetime import datetime
from pathlib import Path

OUT = Path(r"E:\wx\六巡\20260823广州站\评论全文")
IMG = Path(r"E:\wx\六巡\20260823广州站\图片")
FB = Path(r"E:\wx\私有工具\show_feedback\20260823_广州")
XHS = Path(r"E:\wx\私有工具\xhs_archive")
WB = Path(r"E:\wx\私有工具\weibo_merged")
SHOW_DIR_DEFAULT = r"E:\wx\六巡\20260823广州站"

def w(name, text):
    (OUT / name).write_text(text, encoding="utf-8")
    print("[写] %s (%d 字符)" % (name, len(text)))

def main():
    if sys.stdout and getattr(sys.stdout, "buffer", None):
        try: sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception: pass
    global OUT, IMG, FB
    ap = argparse.ArgumentParser()
    ap.add_argument("--show-dir", default=SHOW_DIR_DEFAULT, help="场次素材目录（默认 E:\\wx\\六巡\\20260823广州站）")
    ap.add_argument("--date", default="20260823", help="演出日期 YYYYMMDD（用于定位 show_feedback 目录）")
    ap.add_argument("--city", default="广州", help="城市（用于定位 show_feedback 目录）")
    a = ap.parse_args()
    OUT = Path(a.show_dir) / "评论全文"
    IMG = Path(a.show_dir) / "图片"
    FB = Path(r"E:\wx\私有工具\show_feedback") / ("%s_%s" % (a.date, a.city))
    OUT.mkdir(parents=True, exist_ok=True)

    def after_show(name):
        """目录名 8 位日期前缀 >= 演出日（含演出日及之后 4 天内笔记）"""
        m = re.match(r"^(\d{8})", name)
        return bool(m and int(m.group(1)) >= int(a.date))
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    manifest = ["# 广州站（2026-08-23）六巡样本 · 评论全文归档", "",
                "> 本地私有存档（个人研究/作传素材），不公开。生成时间：%s" % stamp, ""]

    # ---- 微博 ----
    wb_all = []
    if (FB / "weibo_feedback.json").exists():
        for p in json.loads((FB / "weibo_feedback.json").read_text(encoding="utf-8")):
            wb_all.append("【%s】%s\nmid=%s uid=%s\n%s\n" % (
                p.get("created_at") or "?", p.get("keyword") or "观众反馈",
                p.get("mid", ""), p.get("uid", ""), p.get("text", "")))
    if wb_all:
        w("weibo_全文.txt", "\n".join(wb_all))
        manifest.append("- 微博：%d 条（含王晰本人 1 条）" % len(wb_all))

    # ---- 小红书（笔记目录 = 关键词目录下的子目录，或 按链接/ 下；取 content.txt 全文 + meta 统计） ----
    xhs_lines, seen = [], set()
    note_dirs = []
    for kd in glob.glob(str(XHS / "*")):
        if not os.path.isdir(kd):
            continue
        note_dirs += [x for x in glob.glob(kd + "/*") if os.path.isdir(x)]
    note_dirs += [x for x in glob.glob(str(XHS / "按链接" / "*")) if os.path.isdir(x)]
    for kd in sorted(note_dirs, reverse=True):
        name = os.path.basename(kd)
        is_dated = after_show(name)
        is_by_link = bool(re.match(r"^6a8[0-9a-f]{20}", name))
        if not (is_dated or is_by_link):
            continue
        ct = os.path.join(kd, "content.txt")
        mt = os.path.join(kd, "meta.json")
        if not os.path.exists(ct):
            continue
        txt = open(ct, encoding="utf-8").read().strip()
        if len(txt) < 10:
            continue
        meta = {}
        if os.path.exists(mt):
            try: meta = json.loads(open(mt, encoding="utf-8").read())
            except Exception: pass
        note_id = meta.get("note_id") or name.split("_")[0]
        if note_id in seen:
            continue
        seen.add(note_id)
        st = meta.get("stats") or {}
        xhs_lines.append("【%s】赞%s 藏%s 评%s\nnote_id=%s\n%s\n" % (
            meta.get("date") or "?", st.get("likes", "?"), st.get("collects", "?"),
            st.get("comments", "?"), note_id, txt))
    if xhs_lines:
        w("xhs_全文.txt", "\n".join(xhs_lines))
        manifest.append("- 小红书：%d 条（关键词目录 20260823~27，content.txt 全文 + 互动统计）" % len(xhs_lines))

    # ---- B站（39 视频：标题/UP/播放/发布时间/简介 + Top 评论） ----
    bili_lines = []
    if (FB / "bili_feedback.json").exists():
        for v in json.loads((FB / "bili_feedback.json").read_text(encoding="utf-8")):
            pub = datetime.fromtimestamp(v.get("pubdate") or 0).strftime("%Y-%m-%d %H:%M") if v.get("pubdate") else "?"
            bili_lines.append("【%s】播放%s | UP:%s | 发布:%s\n%s\n%s\n评论:\n%s\n" % (
                v.get("bvid", ""), v.get("play", "?"), v.get("author", "?"), pub,
                v.get("title", ""), v.get("desc") or "-",
                "\n".join("  - %s: %s (赞%s)" % (c.get("user", "?"), c.get("text", ""), c.get("like", 0))
                          for c in (v.get("comments") or [])) or "  （无评论）"))
    if bili_lines:
        w("bili_视频清单+评论.txt", "\n".join(bili_lines))
        manifest.append("- B站：%d 个视频（含标题/UP/播放/评论）" % len(bili_lines))

    # ---- 网页（Bing 兜底结果） ----
    bing_lines = []
    if (FB / "bing_feedback.json").exists():
        for h in json.loads((FB / "bing_feedback.json").read_text(encoding="utf-8")):
            bing_lines.append("%s\n%s\n%s\n" % (h.get("title", ""), h.get("url", ""), h.get("snippet", "")))
    if bing_lines:
        w("web_网页兜底.txt", "\n".join(bing_lines))
        manifest.append("- 网页兜底：%d 条（文旅局批文/豆瓣/虎扑/票务）" % len(bing_lines))

    w("_清单.md", "\n".join(manifest))

    # ---- 图片归档：xhs 笔记图（关键词目录+按链接）→ 图片\xhs\ ----
    def safe(n, limit=40):
        s = re.sub(r'[<>:"/\\|?*\r\n\t#]', "", n or "").strip()
        return s[:limit] or "note"

    n_img = 0
    for kd in note_dirs:
        name = os.path.basename(kd)
        is_dated = after_show(name)
        is_by_link = bool(re.match(r"^6a8[0-9a-f]{20}", name))
        if not (is_dated or is_by_link):
            continue
        pics = sorted(glob.glob(os.path.join(kd, "*.jpg")) + glob.glob(os.path.join(kd, "*.jpeg")) +
                      glob.glob(os.path.join(kd, "*.png")))
        if not pics:
            continue
        m24 = re.search(r"[0-9a-f]{24}", name)
        mdate = re.match(r"^(\d{8})_", name)
        if m24:
            note_id = m24.group(0)
        elif mdate:
            note_id = mdate.group(1)
        else:
            note_id = name.split("_")[0]
        title = safe(re.sub(r"^(\d{8})_|^[0-9a-f]{24}_", "", name), 30)
        dst_dir = IMG / ("xhs_link" if is_by_link else "xhs")
        dst_dir.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(pics, 1):
            ext = os.path.splitext(p)[1]
            dst = dst_dir / ("%s_%s_%02d%s" % (note_id, title, i, ext))
            if not dst.exists():
                import shutil
                shutil.copy2(p, dst)
                n_img += 1
    if n_img:
        print("[图] 复制 %d 张 -> %s" % (n_img, IMG))
        m = (OUT / "_清单.md").read_text(encoding="utf-8")
        (OUT / "_清单.md").write_text(m + "\n- 图片：%d 张（xhs 笔记图，含 CANALI 定制服装 6 张）\n" % n_img, encoding="utf-8")
    else:
        print("[图] 无新图片（可能已复制过）")

if __name__ == "__main__":
    main()
