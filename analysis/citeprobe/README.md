# AI / 搜索可见性探测

回答一个问题：**问 AI 一个关于王晰的问题，它会不会引用 `wx409.github.io`？**

## 现状（2026-11-14 基线）

8 个问题，**命中 0**。AI 引用的是豆瓣、知乎、虎扑、B 站、维基百科、公众号 —— 没有你。
详见 `LATEST.md`。

## 三种运行模式

| 模式 | 怎么跑 | 依赖 | 状态 |
|---|---|---|---|
| `reminder`（在用） | 每月 1 日 09:00 由 DSH 提醒我，我用 `web_search` 跑 20 题并写结果 | DSH 自身 | **可用** |
| `llm` | 直接调 DeepSeek 的 Anthropic 兼容接口 + `web_search_20250305` 工具 | 一个 `DEEPSEEK_API_KEY` | 待 key |
| `bing-html` | 抓 `cn.bing.com` 搜索页解析 | 无 | **实测被反爬降级，已加护栏** |

`probe.py` 现在跑的是 `bing-html`：如果不同查询返回的竞争域名完全相同，判定为降级页，**拒绝写历史**并以退出码 2 结束（避免把"被反爬"记成"0 命中"）。

## 加 key 后怎么切

1. 把 key 写进环境变量 `DEEPSEEK_API_KEY`（用户级即可）；
2. 照 `probe.py` 里 `llm` 模式的注释，把 `main()` 的取数函数换成 `llm_search(q)`：
   - `POST https://api.deepseek.com/anthropic/v1/messages`
   - `headers`: `x-api-key`、`anthropic-version: 2023-06-01`
   - `body.tools = [{"type":"web_search_20250305","name":"web_search","max_uses":3}]`
   - 从响应里取 `web_search_tool_result` 的 `url` 列表
3. 这样就能完全无人值守，不再依赖我手动跑。

## 每月自动流程

```
09:00（每月 1 日）→ DSH 提醒 → 我跑 20 题 → 写 history/ + LATEST.md
                                   → 有变化就调 project_b/notify.py
                                     （落在 data/notifications.json，站点 /notifications.html 可见）
```

## 文件

| 文件 | 作用 |
|---|---|
| `probe.py` | 探测器（标准库，无第三方依赖） |
| `run_probe.cmd` | 计划任务入口（已注册 `wx409_cite_probe`，每月 1 日 09:00） |
| `state.json` | 上一轮结果（用于对比变化） |
| `history/` | 每轮快照 |
| `LATEST.md` | 人看的最新报告 |
| `probe.log` | 计划任务的输出 |

## 改题

只改 `probe.py` 顶部的 `QUERIES` 列表，别的地方不用动。
