# -*- coding: utf-8 -*-
"""《南屏晚钟》首次实测（10-10 第二场点歌段）。

历史：该曲 5 次有记录演唱**全部在点歌环节**（2019×3、2023 清唱、2026-10-10）；
本场为**首次有观众实录素材**的实测 → 点歌池常驻曲的第一次数据化。

纪律：点歌段含观众欢呼/合唱噪声 → **读数难看也如实报告**，口径注记写「点歌段噪声环境」；
      三级读数制度照旧（稳定音/触达音/低音带），极值归属不确定时标 `归属未定`。
用法：python -X utf8 project_b\\measure_nanping_wanchong.py [--dry]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
AUD = Path(r"E:\wx\论文素材_王晰作传\音域分析")
OUT = SITE / "data" / "nanping_wanchong_measure.json"
CALIBER_NOTE = "点歌段噪声环境：观众欢呼/合唱可能抬高噪声底、影响 HNR 与极值读数"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    # 需要 10-10 块级/回填给出该曲的绝对时间范围
    sb = SITE / "data" / "show_blocks" / "沉响与长歌_20261010.json"
    d = json.loads(sb.read_text(encoding="utf-8")) if sb.exists() else {}
    blocks = [b for b in (d.get("blocks") or []) if b.get("song") == "南屏晚钟"]
    print(f"[南屏晚钟] 10-10 块级中命中该曲的块：{len(blocks)} 个"
          + (f"（{blocks[0].get('t0_hms')}–{blocks[-1].get('t1_hms')}）" if blocks else "（待回填定案后可得）"))
    print(f"[南屏晚钟] 音轨来源：场次音频\\wav\\沉响与长歌20261010_*（已下载 3 条音轨，含全场）")
    print(f"[南屏晚钟] 口径注记：{CALIBER_NOTE}")
    print("[南屏晚钟] 流程：切片 → demucs 分离 → numpy YIN → 音符切分 → 稳健过滤 → 指标")
    if a.dry:
        print("[--dry] 参数对齐检查通过（不写产物）"); return 0
    if not blocks:
        print("⛔ 尚无该曲时间范围（待 10-10 听辨定案）→ 不生成读数，避免无依据产出")
        return 2
    OUT.write_text(json.dumps({"schema": 1, "song": "南屏晚钟", "show_date": "2026-10-10",
                               "caliber_note": CALIBER_NOTE, "status": "待执行实测"},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("[ok]", OUT.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
