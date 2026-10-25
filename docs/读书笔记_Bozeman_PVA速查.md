# 读书笔记 · Bozeman《Practical Vocal Acoustics》Study Guide（免费公开版）

> 来源：作者官网公开的 [PVA Study Guide Answer Key](http://www.kenbozeman.com/resources/PVA%20Study%20Guide%20Answer%20Key.pdf)（16 页，Q&A 体，Bozeman 本人作答）
> 本地：`temp/books/bozeman_study_guide.pdf`（.txt 已提取，32,030 字符）
> 定位：这不是全书，是**全书的问题清单 + 答案**，恰好最适合当"术语—判据"速查表。

## 一、六个能直接用的概念

### 1. 基频与谐波
- H1 = 基频 = 我们听到的音高；其余谐波是整数倍。
- 记号有两套（H1/H2… 与 1fo/2fo…），文献里并行，引用时说明用哪套。

### 2. F1、F2 是**可调的**，不是固定的
原话：*"Since they result from tube length and shape (cross-sectional area), they are changeable and therefore tunable."*
→ 这正是"低的要高唱"的物理入口：**改声道形状，就能把共振峰挪到谐波上。**

### 3. 低音的"提亮"机制：把 F1、F2 靠近，托住 1fo
原文提到 *"clustering F1 and F2 to boost 1fo"*。
→ 解释"低音为什么还能亮"时，比"质心比 0.996"更接近机制：**不是基频更强，是共振把基频与低次谐波一起托起来了。**

### 4. 男声换声（passaggio）的本质：F1 与 2fo 的交叉
- 传统"换声点"的位置，很大程度可由**元音的 F1 位置**解释，而不是纯喉部动作。
- 男声在 zona di passaggio 的处理是**关闭音色、翻过去（turning over）**，方法是"被动元音修饰"：保持 F1，让 2fo 超过它。

### 5. 被动 vs 主动元音修饰
- **被动**（vowel migration）：音高变、口型不变 → 元音自己"漂"。
- **主动**（active modification）：主动改口型 → 重新调 F1/F2。

### 6. SFC（singer's formant cluster）
- 男声"Open / Close"两种音色，**全程依赖 SFC**；
- **抬喉会破坏 SFC**：导致挤压、音色变浅、失去深度。

## 二、对我们这个项目意味着什么

| 我们的说法 | Bozeman 的对应概念 | 能不能测 |
|---|---|---|
| "低音是亮的" | F1/F2 clustering 托住 1fo、2fo | ✅ 可测 F1/F2 与 H1/H2 的相对位置 |
| "低的要高唱" | 通过声道形状调 F1/F2 | ✅ 可测（同一音高不同段落对比） |
| "换声点在哪" | zona di passaggio = F1 与 2fo 交叉区 | ⚠️ 需要逐音高扫 F1，工作量大 |
| "音色浅/挤" | 抬喉 → 失去 SFC | ⚠️ 可用 SFC 频段（2.8–3.2kHz）能量近似 |

## 三、空缺与下一步

- 这本是**古典/美声体系**的框架，直接套流行男低音要标注体系差异。
- 真要做"F1/F2 实测"，工具不必买书：
  - **Parselmouth**（[GitHub 1296★](https://github.com/YannickJadoul/Parselmouth)）：Praat 的 Python 封装，可直接提 F1/F2；
  - 本机已有 `librosa 0.11`（含 `lpc`），也可用 LPC 根估计共振峰，无需联网安装。
- 待办：在 B1 段（79–84s）与念诵段（60–65s）上各测一组 F1/F2，看是否落在 Bozeman 描述的"托住 1fo/2fo"位置上。
