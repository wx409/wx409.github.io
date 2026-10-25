# 24 窗听辨说明（给真实听者）

> 目录：`data/research/experiments/exp-20261025-01/adjudication/`
> 每个窗口一目录：`materials/adj-XX/`

## 一句电脑能做的、一句只能人做的

- 电脑已完成：抽 24 窗、切音频、算谐波列、导出两候选 F0 轨迹。
- **只有人能做**：判断这段到底是谁在唱、哪个候选 F0 更合理。

## 每个窗口只看两件事

### A. 归属（是不是目标歌手）

填 `target_singer` / `not_target_singer` / `accompaniment_or_other_voice` / `unclear`。

判断依据：**听** `clip_context.wav`（前后各 1 秒语境），不要只听几毫秒的代表帧。
低音段里贝斯、和声、观众声都可能抢戏；分不清就填 `unclear`。

### B. F0 判读（候选 A vs 候选 B）

填 `candidate_A_more_reasonable` / `candidate_B_more_reasonable` /
`both_reasonable_small_difference` / `both_unreliable` / `unresolved`。

判断依据：

1. **先听**：哪个音高与听到的低音更接近；
2. **再看谐波**：打开 `harmonics.json`，看候选 A/B 的 1/2/3/4/6 次谐波是否都有峰；
   - 有完整谐波列（1f0、2f0、3f0 都在）→ 该候选更可能是真音；
   - 只有 3f0/6f0 而缺 1f0/2f0 → 典型次谐波错误；
3. 相差只有**几十音分**且没有独立参考时，**不要硬选**，用 `both_reasonable_small_difference`；
4. 拿不准就 `unresolved`——**允许不判，不允许编**。

## 三条纪律

1. **裁决前不要打开** `candidate_mapping.private.json`（它会告诉你 A/B 是谁）；
2. 每份表单必须填 **reviewer** 与 **review_date**，脚本不代填；
3. **可以分批听**，不必一口气 24 窗。疲劳时对低音八度和归属的判断最容易变得随意。

## 填完之后

把 24 份 `form.json` 里的字段填实（`status` 改为 `done`），再交给 DSH 回填裁决、解映射、重跑汇总。
在那之前：不扩样、不输出"筛查价值"结论、不改任何发布规则。
