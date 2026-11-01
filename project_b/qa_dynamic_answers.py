"""为 qa 页补充三条「数据现算」答案（峰值 / 城市场次 / 现场唱得最多）

用法：被 build_qa_page.py 调用，不单独跑。
数据源：
  · E:\\wx\\wx_textmine_out\\music_index_long.csv   （歌曲峰值）
  · data/archive_stage_tour.json                   （现场曲目行：tag/city/song）
"""
import json
from collections import Counter, defaultdict

import pandas as pd

CSV = r"E:\wx\wx_textmine_out\music_index_long.csv"
TOUR = r"D:\wx409.github.io\data\archive_stage_tour.json"


def peak_songs(top=5):
    df = pd.read_csv(CSV, usecols=["date", "song", "index"])
    df["index"] = pd.to_numeric(df["index"], errors="coerce")
    df = df.dropna(subset=["index"])
    g = df.groupby("song")["index"].max().sort_values(ascending=False)
    peak_all = df.loc[df["index"].idxmax()]
    lines = ["指数峰值最高的歌：**《%s》%d**（%s）。" % (peak_all["song"], int(peak_all["index"]), peak_all["date"])]
    lines.append("峰值前 %d：" % top + "、".join("《%s》%d" % (k, int(v)) for k, v in list(g.items())[:top]))
    lines.append("口径：追踪曲目池逐日指数（每日最终值）取每首最大值；峰值多发生在新专辑发行或节目播出当周，不等于长期热度；样本 %d 首、%d 天。"
                 % (df["song"].nunique(), pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").nunique()))
    return "\n\n".join(lines)


def city_shows(top=8):
    """按（城市 + 日期）去重，统计有现场素材的演出日；不宣称场次总数，避免与 64 场口径冲突。"""
    rows = json.load(open(TOUR, encoding="utf-8"))["rows"]
    pairs = {(r.get("city"), r.get("date")) for r in rows if r.get("city") and r.get("date")}
    c = Counter(city for city, _ in pairs)
    top_txt = "、".join("%s %d 次" % (k, v) for k, v in c.most_common(top))
    return ("按「城市 + 日期」去重，站内**有现场素材**的演出日共 %d 个，分布在 %d 座城市。\n\n"
            "出现最多：%s。\n\n"
            "口径：只统计有现场音视频素材的演出日，**不是全站场次总数**——全站场次为 64 场"
            "（六轮巡演 59 + 签唱会 5），两者不可混读。"
            % (len(pairs), len(c), top_txt))


def top_songs_onstage(top=8, min_shows=4):
    rows = json.load(open(TOUR, encoding="utf-8"))["rows"]
    song_shows = defaultdict(set)
    BAD = ("全场", "合集", "串烧", "片段", "talk", "talk_", "花絮", "谢幕")
    for r in rows:
        song = r.get("song") or ""
        if not song or not r.get("tag") or any(b in song for b in BAD):
            continue
        song_shows[song].add(r["tag"])
    c = Counter({k: len(v) for k, v in song_shows.items()})
    picked = [(k, v) for k, v in c.most_common(40) if v >= min_shows][:top]
    if not picked:
        picked = c.most_common(top)
    txt = "、".join("《%s》%d 场" % (k, v) for k, v in picked)
    return ("在站内收录的现场素材里，出现场次最多的歌是：%s。\n\n"
            "口径：按「曲名 × 场次标记」去重计次，仅统计有现场音视频素材的场次；不是完整巡演歌单的统计。"
            % txt)
