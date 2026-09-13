# tools/ —— 自动化分析管线（7.5）

## 它是什么

把「新增一个分析对象」从**手工流程**降为**一条队列记录**：
往 `data/analysis_queue.json` 加一条 → 管线自动下载音轨、跑与站内主口径**同一套**声学管线、回写结果 JSON。

```
tools/fetch.py     URL → 音频（仅音频轨）到 tmp/            # 不落库、不入库
tools/analyze.py   音频 → demucs 人声分离 → YIN 逐帧 F0 → 标准化 JSON
tools/queue_run.py     读 data/analysis_queue.json，批量跑 fetch→analyze，回写 status/result
```

## 快速用法

```bash
# 1) 单条直跑（测试用）
python -X utf8 tools/fetch.py "<视频URL>" --name test01
python -X utf8 tools/analyze.py tmp/test01.wav --json tmp/analysis/test01.json

# 2) 队列批量（推荐）
python -X utf8 tools/queue_run.py --status      # 看队列
python -X utf8 tools/queue_run.py               # 跑全部 pending
python -X utf8 tools/queue_run.py --only zhaopeng-01
```

队列条目字段：

```json
{"id": "zhaopeng-01", "url": "https://…", "singer": "赵鹏", "title": "外婆的澎湖湾",
 "year": 2010, "kind": "录音室", "age_band": "30–40", "status": "pending"}
```

`status` 流转：`pending → fetched → analyzed`（失败为 `failed` + `reason`，人工可接手）。

## 合规边界（必读）

- 音视频**仅用于个人研究**。
- **不二次分发、不入库、不嵌入页面**：素材只落在 `tmp/`（已在 `.gitignore`）。
- **只发布方法与结果数据**（逐曲指标、复核状态、口径说明）。
- 不绕过付费或访问权限限制，仅使用公开可访问的链接。
- 结果数据发布前须过复核门槛（稳定音口径）；未复核读数不得进入能力结论。

## 本机约束（血泪教训，勿改）

- `numba/llvmlite.dll` 与 `sphn` 的 `.pyd` 被「应用程序控制策略」阻止 → 不能走 `librosa.pyin`，
  也不能走 `python -m demucs` 子进程。解法：注入 `sphn` 桩 + `demucs.api.Separator`（进程内 API）。
- `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1`：用本地缓存模型，断网可跑。
- **CJK 路径**会让 demucs/ffmpeg 子进程失败（`Unspecified internal error`）——
  `analyze.py` 会先把输入复制成 ASCII 名再分离。
- 用 **soundfile** 读音频，不用 librosa（避免触发 numba）。

## 与站内主口径的关系

`tools/queue_run.py` 产出的是**待复核**结果：它保证口径一致（同分离模型、同 F0 估计器、同过滤门槛），
但**不自动写入站点的能力结论**。进入 `data/archive_vocal*.json` 或横向对比表前，
仍须走 `音域分析/低音复核_谐波列.py`（原始混音谐波列判定）与终裁表流程。

这正是横向对比（7.2）能成立的前提：口径一致 + 复核可见。
