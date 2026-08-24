# -*- coding: utf-8 -*-
"""小红书入库 · 按歌曲归类版（2026-08-24 定稿）
============================================================
原则：
  - 站内纯文字、无链接、无 note_id（方案A，防假死链/隐私）
  - **按歌曲归类**：提到某首歌的评论归到该歌下（live-reviews.html 广州站展示为
    每首歌一个分组）；提多首歌/无法归类的单独放；≤20 字短评合并为「短评合集」；
    优美评论由人工挑选后另存（首页观众视角矩阵用）。
  - 本地已留存全文/图/视频（xhs_archive/按链接/）
输入：E:/wx/私有工具/xhs_archive/_by_links_summary.json
输出：live-reviews.html 广州站（按歌曲分组）+ temp/优美评论候选.md
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\wx409.github.io")
SUMMARY = Path(r"E:\wx\私有工具\xhs_archive\_by_links_summary.json")
HTML = ROOT / "live-reviews.html"
BEAUTY_OUT = ROOT / "temp" / "优美评论候选_广州站.md"
SHOW_DATE = "2026-08-23"

# 歌曲归类词典：歌名 -> 匹配关键词（标题/正文里出现即归类）
SONG_RULES = [
    ("橄榄树", ["橄榄树", "橄欖樹", "不要问我从哪里来"]),
    ("Your Man", ["your man", "Your Man", "yourman"]),
    ("情网", ["情网", "情網"]),
    ("夜色", ["夜色"]),
    ("月半弯", ["月半弯", "月半彎"]),
    ("Yesterday Once More", ["yesterday once more", "Yesterday Once More", "every shalalala"]),
    ("Close to You", ["close to you", "Close to You"]),
    ("让她降落", ["让她降落", "讓牠降落", "讓它降落", "她降落"]),
    ("一生守候", ["一生守候"]),
    ("心动", ["心动", "心動"]),
    ("像雾像雨又像风", ["像雾像雨", "像霧像雨"]),
    ("女人花+水中花", ["女人花", "水中花"]),
    ("花儿为什么这样红", ["花儿为什么这样红", "花兒為什麼這樣紅", "低音预警"]),
    ("平凡又美好的晚上", ["平凡又美好的晚上", "平凡又美好"]),
    ("Autumn Leaves", ["autumn leaves", "Autumn Leaves", "秋叶", "金色手麦"]),
    ("Besame Mucho", ["besame", "Besame"]),
    ("生日快乐", ["生日快乐", "生日快樂"]),
]
# 泛评论/整场关键词（无法归到单曲，单独放）
GENERAL_HINTS = ["巡演", "音乐会", "演唱会", "现场", "repo", "六巡", "个巡", "回"]


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def clean_text(it):
    """标题+正文 → 纯净文本（去话题、压缩空白）"""
    title = (it.get("title") or "").strip()
    desc = re.sub(r"\s+", " ", (it.get("desc") or "")).strip()
    text = (title + "。" + desc) if title and desc else (title or desc)
    text = re.sub(r"#\S+#", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[。．]+$", "", text)
    return text


def classify(text):
    """返回 (歌曲名列表, 是否泛评论)"""
    songs = []
    for name, kws in SONG_RULES:
        if any(k.lower() in text.lower() for k in kws):
            songs.append(name)
    if songs:
        return songs, False
    is_gen = any(k in text for k in GENERAL_HINTS)
    return [], is_gen


def main():
    if not SUMMARY.exists():
        print("汇总不存在"); return
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    items = [it for it in data.get("items", []) if it.get("ok")]
    print(f"抓取成功 {len(items)} 条")

    # 分类
    by_song = {}       # 歌名 -> [content]
    general = []       # 泛评论 (>=20字 单独)
    short = []         # <20字 合并
    for it in items:
        text = clean_text(it)
        if not text:
            continue
        author = (it.get("author") or "").strip()
        content = f"@{author}：{text}" if author else text
        songs, is_gen = classify(text)
        if songs:
            for s in set(songs):
                by_song.setdefault(s, []).append(content)
        elif is_gen:
            if len(text) >= 20:
                general.append(content)
            else:
                short.append(content)
        else:
            # 无关内容（不归类也不泛）→ 丢弃
            pass

    # 输出结构化报告（供插入页面）
    report = {"song_groups": by_song, "general": general, "short": short}
    out = ROOT / "temp" / "_xhs_classified.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"歌曲归类: {len(by_song)} 组")
    for s, lst in sorted(by_song.items()):
        print(f"  {s}: {len(lst)} 条")
    print(f"泛评论: {len(general)} 条 | 短评(<20字): {len(short)} 条")

    # 生成优美评论候选（人工挑选：情感丰富、描写生动的）
    beauty = []
    for it in items:
        text = clean_text(it)
        if len(text) >= 30:
            beauty.append(f"- @{it.get('author','')}：{text}")
    BEAUTY_OUT.write_text("\n".join(beauty), encoding="utf-8")
    print(f"优美评论候选 → {BEAUTY_OUT} ({len(beauty)} 条 ≥30字)")


if __name__ == "__main__":
    main()
