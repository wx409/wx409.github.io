#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大肥鱼反应模板（通用版）——给一段视频 + 几句台词，直接出成片。

用法（最简）
  python -X utf8 project_b\\reaction_template.py ^
     --clip "E:\\...\\某段.mp4" --start 138 --len 14 ^
     --line "0.5|等一下，这一句有点东西。" ^
     --line "8.0|他这里往下掉了一个八度。" ^
     --out "E:\\wx\\论文素材_王晰作传\\剪映素材\\反应_示例.mp4"

或台词写在 json：
  [{"at":0.5,"text":"..."},{"at":8.0,"text":"..."}]

结构：视频铺满（不裁脸、模糊填边）+ 大肥鱼左下角（自带轻微动作与嘴型循环）+ 字幕 + 配音
输出：1080×1920 / yuv420p / High / 音视频双流（三段式合成，失败可单独重跑）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import tempfile
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np

BASE = Path(r"E:\wx\论文素材_王晰作传")
ASSETS = BASE / "剪映素材"
CHAR = ASSETS / "char_alpha.mov"     # 透明角色（自带轻微动作/嘴型循环）
BG = ASSETS / "bg_tavern.png"
FONT = r"C:\Windows\Fonts\msyhbd.ttc"
FPS = 25
VOICE = "zh-CN-XiaoyiNeural"
ff = imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stderr or "")


def ts(x):
    h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
    return "%d:%02d:%05.2f" % (h, m, s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", required=True, help="要反应的视频")
    ap.add_argument("--start", type=float, default=0, help="从源视频第几秒开始")
    ap.add_argument("--len", type=float, default=12, help="时长（秒）")
    ap.add_argument("--line", action="append", default=[], help='"时间|台词"，可多次')
    ap.add_argument("--lines-json", default="", help="或者给一个 json 文件")
    ap.add_argument("--out", required=True)
    ap.add_argument("--layout", choices=["pip", "full"], default="pip",
                    help="pip=视频全屏+角色左下；full=角色与视频左右分屏")
    ap.add_argument("--voice", default=VOICE)
    ap.add_argument("--char-scale", type=float, default=0.34, help="角色高度占画布比例")
    a = ap.parse_args()

    total = float(a.len)
    # 台词
    cues = []
    if a.lines_json:
        for it in json.loads(Path(a.lines_json).read_text(encoding="utf-8")):
            cues.append((float(it["at"]), str(it["text"])))
    for s in a.line:
        t, txt = s.split("|", 1)
        cues.append((float(t), txt))
    cues.sort()
    print("[台词]", cues if cues else "（无，只放视频）")

    tmp = Path(tempfile.mkdtemp(prefix="react_"))

    # ① 配音
    if cues:
        async def go():
            for i, (_, txt) in enumerate(cues):
                await edge_tts.Communicate(txt, a.voice, rate="+5%", pitch="+26Hz").save(str(tmp / ("v%d.mp3" % i)))
        try:
            asyncio.run(go())
        except Exception as e:
            print('[tts] 警告:', str(e)[:80])
        durs = []
        for i in range(len(cues)):
            _, e = run([ff, "-i", str(tmp / ("v%d.mp3" % i))])
            d = 0.0
            for l in e.splitlines():
                if "Duration" in l:
                    hh, mm, ss = l.split("Duration:")[1].split(",")[0].strip().split(":")
                    d = int(hh) * 3600 + int(mm) * 60 + float(ss)
            durs.append(d)
        print("[配音] 时长:", [round(d, 2) for d in durs])
    else:
        durs = []

    # ② 字幕
    srt = tmp / "s.srt"
    lines = []
    for i, ((at, txt), d) in enumerate(zip(cues, durs), 1):
        lines += [str(i), "%s --> %s" % (ts(at), ts(min(total, at + max(1.6, d + 0.2)))), txt, ""]
    srt.write_text("\n".join(lines), encoding="utf-8")

    # ③ 视频轨
    ch_h = int(1920 * a.char_scale)
    ch_w = int(ch_h * 629 / 820)
    v = tmp / "v.mp4"
    if a.layout == "pip":
        filt = (
            "[0:v]split=2[x][y];"
            "[x]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=26:2,eq=brightness=-0.12[bg];"
            "[y]scale=1080:-1[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[m];"
            f"[1:v]format=rgba,scale={ch_w}:{ch_h}[ch];"
            "[m][ch]overlay=%d:%d:format=auto[v1];"
            "[v1]subtitles='%s':force_style='FontName=Microsoft YaHei,Fontsize=20,"
            "PrimaryColour=&H00D8EAF5,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=230',"
            "format=yuv420p[v]" % (40, 1920 - ch_h - 40, str(srt).replace("\\", "/").replace(":", "\\:"))
        )
    else:
        filt = (
            "[0:v]split=2[x][y];"
            "[x]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=26:2,eq=brightness=-0.14[bg];"
            "[y]scale=1080:-1[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[m];"
            f"[1:v]format=rgba,scale={ch_w}:{ch_h}[ch];"
            "[m][ch]overlay=0:0:format=auto[v1];"
            "[v1]subtitles='%s':force_style='FontName=Microsoft YaHei,Fontsize=20,"
            "PrimaryColour=&H00D8EAF5,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=230',"
            "format=yuv420p[v]" % (str(srt).replace("\\", "/").replace(":", "\\:"))
        )
    rc, err = run([ff, "-y", "-ss", str(a.start), "-t", str(total), "-i", a.clip,
                   "-stream_loop", "-1", "-t", str(total), "-i", str(CHAR),
                   "-filter_complex", filt, "-map", "[v]", "-an",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                   "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0", str(v)])
    if rc != 0:
        print("视频失败:", err[-500:]); return 4
    print("[1/3] 视频轨 OK")

    # ④ 音轨：原声 + 配音（numpy 拼接，避免 ffmpeg 混音坑）
    n = int(total * 44100)
    buf = np.zeros((n, 2), dtype=np.float32)
    raw = subprocess.run([ff, "-v", "error", "-ss", str(a.start), "-t", str(total), "-i", a.clip,
                          "-f", "f32le", "-ac", "2", "-ar", "44100", "-"], capture_output=True).stdout
    cls = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)
    buf[:min(n, len(cls))] += cls[:n] * 0.85
    for (at, _), d, i in zip(cues, durs, range(len(cues))):
        t = subprocess.run([ff, "-v", "error", "-i", str(tmp / ("v%d.mp3" % i)),
                            "-f", "f32le", "-ac", "2", "-ar", "44100", "-"], capture_output=True).stdout
        ta = np.frombuffer(t, dtype=np.float32).reshape(-1, 2)
        i0 = int(at * 44100); i1 = min(n, i0 + len(ta))
        if i1 > i0:
            buf[i0:i1] += ta[: i1 - i0] * 1.15
    peak = float(np.abs(buf).max()) or 1.0
    buf = buf / peak * 0.9
    fade = int(1.0 * 44100)
    if n > fade:
        buf[-fade:] *= np.linspace(1, 0, fade)[:, None]
    wav = tmp / "a.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    print("[2/3] 音轨 OK")

    # ⑤ 合流
    rc, err = run([ff, "-y", "-i", str(v), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0",
                   "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                   "-movflags", "+faststart", "-shortest", a.out])
    if rc != 0:
        print("合流失败:", err[-400:]); return 4
    rc, dec = run([ff, "-v", "error", "-i", a.out, "-f", "null", "-"])
    _, info = run([ff, "-i", a.out])
    print("[3/3] 完成:", a.out)
    print("  解码:", (dec or "无错误")[:60])
    print("  ", [l.strip()[:90] for l in info.splitlines() if "Stream #" in l or "Duration" in l])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
