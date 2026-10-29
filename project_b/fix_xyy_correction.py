import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')

# 1) 数据更正
p = ROOT / 'data' / 'research' / 'xyy_long_phrase.json'
d = json.loads(p.read_text(encoding='utf-8'))
d['correction'] = {
    "note": "23.2 秒系 CREPE 穿过换气缺口造成的假连续；能量口径复核为 14.2 秒",
    "energy_segments": {"94.2s_start": [0.0, 14.2], "247.4s_start": [0.0, 14.3]},
    "breath_gaps_94_2": [[14.19, 1.03, -49.5], [18.03, 0.67, -47.6]],
    "breath_insight": "气口只比中位能量低约 12–20 dB、时长 0.67–1.03 秒，人耳很难察觉",
}
p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')

# 2) 文档更正
doc = ROOT / 'docs' / '想游泳的星_长句实测_20261029.md'
s = doc.read_text(encoding='utf-8')
s = s.replace(
    "| 94.2s 起 | **23.2 秒** | 238.2 | 224.8 | 6% |",
    "| 94.2s 起 | ~~23.2 秒~~ → **14.2 秒**（能量复核） | 238.2 | 224.8 | 6% |")
s = s.replace(
    """## 三、还有更长的（待核）

94.2 秒处有一段 **23.2 秒** 连续发声（中位 238Hz），比"15 秒"更长。

**但它可能是多句连唱**（气口小于 0.2 秒被算法忽略），暂标「待核」，不作结论。""",
    """## 三、23.2 秒那条是假连续（已更正）

初筛在 94.2 秒处报 23.2 秒连续，**能量复核后是 14.2 秒**：

| 气口位置 | 时长 | 最低能量 | 相对中位 |
|---|---|---|---|
| t+14.19s | 1.03 秒 | −49.5 dB | −29 dB |
| t+18.03s | 0.67 秒 | −47.6 dB | −27 dB |

CREPE 在这些缺口里仍判为有声（追踪到残留共振），所以累加成了 23.2 秒。

**15 秒那句经同样复核为 14.3 秒**——与"15 秒不换气"的口径一致。

## 三之二、气口为什么听不出来

两处气口的能量只比演唱中位低 **12–20 dB**、时长 **0.67–1.03 秒**，
且被伴奏与混响填满——**人耳确实很难察觉**。

这本身就是一条可量化的观察：**他的换气点做得轻而短**，不是没有气口，是气口不显眼。""")
doc.write_text(s, encoding='utf-8')
print('文档与数据已更正')
