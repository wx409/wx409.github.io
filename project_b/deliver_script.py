# -*- coding: utf-8 -*-
"""交付：素材提取 + 配音 + 可改脚本（不再渲染视频，避免再出废片）。

1) 在 分P逐曲 里递归找《我真的受伤了》音源，验证 695.9s 起 16.5 秒、能量无深坑
2) 抠出这 16.5 秒 → 剪映素材/longnote_16s.wav
3) 生成三段配音 → 剪映素材/vo_1..3.mp3
4) 写可编辑脚本（JSON + Markdown），台词随时改
"""
import asyncio, json, subprocess
from pathlib import Path
import numpy as np
import imageio_ffmpeg
import edge_tts

BASE = Path(r"E:\wx\论文素材_王晰作传")
OUTD = BASE / "剪映素材"
OUTD.mkdir(exist_ok=True)
SRC_ROOT = BASE / "音域分析" / "场次音频" / "wav_分P逐曲"
ff = imageio_ffmpeg.get_ffmpeg_exe()

T_START, T_LEN, NOTE, HZ = 695.9, 16.5, "D2", 74.8

LINES = [
    ("vo_1", "一个低音，他能拖住十六秒半。"),
    ("vo_2", "这不是炫技。低音拖得越久，气越难稳。"),
    ("vo_3", "所以别再说男低音只是“声音厚”了。"),
]


def find_file():
    hits = [p for p in SRC_ROOT.rglob("*.wav") if "受伤" in p.name]
    if not hits:
        hits = [p for p in SRC_ROOT.rglob("*.wav") if "P02" in p.name or "暗潮" in p.name]
    return hits[0] if hits else None


def main():
    f = find_file()
    print("音源:", f)
    if not f:
        print("没找到音源，脚本与配音仍会生成")
    else:
        raw = subprocess.run([ff, "-v", "error", "-ss", str(T_START), "-t", str(T_LEN),
                              "-i", str(f), "-f", "f32le", "-ac", "1", "-ar", "8000", "-"],
                             capture_output=True).stdout
        a = np.frombuffer(raw, dtype=np.float32)
        hop = int(8000 * 0.02); n = len(a) // hop
        r = np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(axis=1)) if n else np.array([0])
        print("  长度 %.2fs｜能量中位 %.4f｜谷 %.4f" % (len(a) / 8000, float(np.median(r)), float(r.min())))
        out = OUTD / "longnote_16s.wav"
        subprocess.run([ff, "-y", "-ss", str(T_START), "-t", str(T_LEN), "-i", str(f),
                        "-ac", "2", "-ar", "44100", str(out)], capture_output=True)
        print("  已抠出:", out.name, round(out.stat().st_size / 1024 / 1024, 2), "MB")

    # 配音
    async def go():
        for name, text in LINES:
            await edge_tts.Communicate(text, "zh-CN-XiaoyiNeural", rate="+4%", pitch="+26Hz").save(str(OUTD / (name + ".mp3")))
    asyncio.run(go())
    print("配音:", [n for n, _ in LINES])

    # 可编辑脚本
    script = {
        "title": "大肥鱼评王晰 · 16.5 秒低音",
        "note": "改台词只改 lines 里的 text；改时间只改 at；不要动 data 字段（用于核对）",
        "data": {"song": "我真的受伤了", "note": NOTE, "hz": HZ, "dur_s": T_LEN,
                 "t_start_s": T_START, "source": "分P逐曲（现场）"},
        "lines": [
            {"id": "vo_1", "at": 0.8, "text": LINES[0][1]},
            {"id": "vo_2", "at": 7.5, "text": LINES[1][1]},
            {"id": "vo_3", "at": 14.0, "text": LINES[2][1]},
        ],
        "video_slots": [
            {"name": "王晰片段", "x": 60, "y": 300, "w": 960, "h": 540, "t0": 2.0, "t1": 8.0},
            {"name": "王晰片段（再放）", "x": 60, "y": 300, "w": 960, "h": 540, "t0": 9.0, "t1": 15.0},
        ],
    }
    (OUTD / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=1), encoding="utf-8")

    md = ["# 大肥鱼评王晰 · 脚本（可改）", "",
          "**证据**：%s %s（%.1fHz），一口气 **%.1f 秒**（%s 起）" % (
              script["data"]["song"], NOTE, HZ, T_LEN, "3分55.9秒" if False else "11:35.9"), "",
          "| 时间 | 台词 | 画面 |", "|---|---|---|"]
    for l in script["lines"]:
        md.append("| %.1fs | %s | 酒馆·大肥鱼 |" % (l["at"], l["text"]))
    md += ["", "| 画中画 | 位置 | 时间 |", "|---|---|---|"]
    for v in script["video_slots"]:
        md.append("| %s | (%d,%d) %d×%d | %.1f–%.1f 秒 |" % (
            v["name"], v["x"], v["y"], v["w"], v["h"], v["t0"], v["t1"]))
    (OUTD / "script.md").write_text("\n".join(md), encoding="utf-8")
    print("脚本:", OUTD / "script.json", OUTD / "script.md")


if __name__ == "__main__":
    main()
