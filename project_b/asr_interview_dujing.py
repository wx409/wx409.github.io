# -*- coding: utf-8 -*-
"""访谈 6:40–7:40 转写（faster-whisper large-v3-turbo，本地，无网络）。"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WAV = Path(r"E:\wx\论文素材_王晰作传\音域分析\他人主导\音频\综艺"
           r"\BV1no4y1K7dP_经典咏流传《渡荆门送别》歌曲及访谈.wav")
OUT = Path(r"E:\wx\论文素材_王晰作传\原始材料\渡荆门送别_访谈_6m40-7m40.md")
START, END = 400.0, 460.0


def main() -> int:
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, info = m.transcribe(str(WAV), language="zh", beam_size=5, vad_filter=True,
                              clip_timestamps=[int(START), int(END)])
    rows = []
    for s in segs:
        rows.append({"t": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
    text = "".join(r["text"] for r in rows)
    lines = ["# 渡荆门送别 · 访谈 6:40–7:40 转写", "",
             "> 源：`E:\\wx\\私有工具\\bilibili_wangxi\\BV1no4y1K7dP_经典咏流传《渡荆门送别》歌曲及访谈.mp4`",
             "> 模型：faster-whisper **small**（本地、int8；large-v3-turbo 仅缓存了 refs、离线无权重）；**ASR 未人工校对**",
             f"> 片段：{START:.0f}–{END:.0f}s｜识别句数 {len(rows)}｜字数约 {len(text)}", "",
             "## 逐句（带时间戳）", ""]
    for r in rows:
        mm, ss = divmod(r["t"], 60)
        lines.append(f"- **{int(mm):02d}:{ss:04.1f}–{int(r['end']//60):02d}:{r['end']%60:04.1f}**　{r['text']}")
    lines += ["", "## 全文（连续）", "", text, "",
              "> 说明：标点与断句由模型给出，可能存在错字；引用前建议回听原片核对。"]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[OK]", OUT, "｜句数", len(rows), "｜字数", len(text))
    for r in rows:
        print(f"  {int(r['t']//60):02d}:{r['t']%60:04.1f}  {r['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
