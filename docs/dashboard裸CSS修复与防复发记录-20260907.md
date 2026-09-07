# dashboard 顶部吐 CSS —— 根因修复与防复发记录（2026-09-07）

> 触发：用户报告 `https://wx409.github.io/dashboard/` 页面最上方反复出现 HTML/CSS 渲染问题。
> 本文件记录完整根因链、本次修复动作、以及"以后不再出现"所需的纪律。

---

## 一、根因链（为什么"屡次出现"）

### 现象
`/dashboard/` 顶部渲染出一大段 CSS 源码文本（如 `*{margin:0;...}body{...}`）。
浏览器行为：`<head>` 内出现**未包在 `<style>` 里的非空白文本**时，HTML 解析器会当作正文开头，
把该文本渲染到页面最上方。

### 坏产物的结构形态（2026-09-06 线上可见）
```
114: <style>            ← 新精简规范 CSS
134: </style>           ← 提前闭合（错误）
135~335: 旧 CSS 裸文本   ← 未包裹，裸露在 <head> 里 → 被浏览器当正文渲染
336: </style>           ← 悬空闭合（多余）
337: </head>
```
即 `<style>` 开 1 次、闭 2 次：**配对被破坏**。

### 真正的原因（三层）
1. **模板曾含坏结构**：生成器 `HTML_TEMPLATE` 曾被改出"两套 CSS 叠加且配对破坏"的形态。
   磁盘文件已于 **2026-09-04 14:36** 修复为单 `<style>` 配对（新旧 CSS 合并在一段内，视觉不删）。
2. **daemon 常驻内存，改模板不生效（复发主因）**：采集生成器以 `pythonw` 常驻运行
   （计划任务 `QQMusicDashboardAutoStart` → `E:\wx\QQ音乐大屏生成器_GEO优化版_源码.py`）。
   日志显示实例 09-04 08:35 启动后一直运行到 09-07 09:03，**内存里一直装着修复前的旧模板**，
   期间每个批次都用坏模板重新生成坏产物并 git commit → 台式机 09-06 的产物级修复
   （aa0cb59/c75c376）被"再生成"覆盖，表现为**反复复发**。
3. **本地分支分叉 → push 一直失败**：台式机 09-06 push 了两笔只动 `dashboard/index.html` 的
   修复提交（aa0cb59、c75c376），笔记本本地另有 17 个自动部署提交未合流 → 每次
   `git push origin main` 都被拒（non-fast-forward），线上数据滞留、坏/好状态反复。

### 结论一句话
> **模板文件早修好了，但跑着的进程没重启，坏模板在内存里又生成了一天多的坏页面；
> 再加上笔记本与台式机分支分叉导致推送被拒——两个问题叠加 = "屡次报错"。**

---

## 二、本次修复动作（2026-09-07，笔记本侧）

| 动作 | 说明 |
|---|---|
| 生成器加防呆自检 `_html_structural_ok()` | `generate_dashboard()` 写 `index.html` 前校验：`<style>`/`</style>` 必须配对且 ≥1；`</head>` 前不允许任何裸文本；`<body>` 必须在 `</head>` 后。**不通过则保留上一版完好页面、阻止进入自动部署**，坏结构从此进不了 git/线上 |
| 模板现状核对 | `E:\wx\` 与仓库 `project_b\` 两副本 SHA256 一致；模板为单 `<style>` 配对（2537→2758），无二次 `.replace()` 破坏点 |
| 分支合流 | `git merge origin/main`：`dashboard/index.html` 冲突取笔记本最新版（09-07 数据 + 干净单 style 结构，CSS 视觉与台式机双段版等价）；连同 `data/notifications.json`、工具脚本、本记录一并提交 |
| 恢复推送 | 合流后 `git push origin main` 成功，线上恢复最新批次（消除 17 个滞留提交） |
| 重启 daemon | 重启 `QQMusicDashboardAutoStart`，让新代码（含自检）在常驻实例中生效 |
| 固化三查脚本 | `tools/verify_dashboard.py`：style 配对 / head 无裸文本 / body 位置，一键三查 |

---

## 三、防复发纪律（务必遵守）

1. **改了生成器模板/源码后，必须重启计划任务，否则不生效**：
   ```powershell
   Stop-ScheduledTask -TaskName QQMusicDashboardAutoStart   # 或先杀对应 pythonw 进程
   Start-ScheduledTask -TaskName QQMusicDashboardAutoStart
   ```
   判据：`E:\wx\qqmusic_dp_edge.log` 出现新的"服务已启动"行，且新实例首次重建产物通过三查。
2. **发布 dashboard 前先跑三查**：
   ```powershell
   python D:\wx409.github.io\tools\verify_dashboard.py
   ```
   退出码 0 才允许 push。生成器已内置同款自检（写文件前拦截）。
3. **唯一数据出口 / 唯一写入者**：`dashboard/` 目录只允许 QQ 音乐生成器写入；
   台式机补批请用**与笔记本一致的生成器副本**（勿用 `qqmusic_dashboard_整合修复版` 等旧版覆盖）。
4. **两台机器都要 push 时**：先 `git fetch`，若本地落后先 `git merge origin/main`（或 pull --rebase），
   禁止强推覆盖他人提交。
5. 敏感文件纪律不变：`radio_proxy.py / radio_cookie.json / .env / secrets.bat / 音频` 永不入库；
   提交前 `git status` 三查。

---

## 四、周末补批机制（台式机侧，另见《给笔记本DSH…》文档）

- 生成器整套 + 数据源（歌曲长表/指标/采集缓存）同步到台式机后，台式机可作为"按需补批执行机"。
- 本记录所在仓库已恢复可推送状态：台式机 `git pull` 即可拿到修复后的生成器快照
  （`project_b/QQ音乐大屏生成器_GEO优化版_源码.py`，含防呆自检）与全部最新数据。
- 台式机侧落地清单（需在台式机执行）：
  1. 同步生成器工程与数据源（移动硬盘/U 盘 或 Git 私有仓）；
  2. 生成器内 `WEBSITE_REPO` 指向台式机的 `D:\wx409.github.io`；
  3. 周末/晚间 `schtasks` 定时（如周六日 18:00）或一键 `.bat` 触发 `--rebuild` 补批；
  4. 每次补批后由生成器自动 commit+push（前提：先 `git pull` 保持与 origin 一致）。

## 五、文本挖掘管线（wx_textmine）接入备忘

- 管线产出（`master_timeline.json / event_song_edges.json / event_effects.json /
  挖掘报告.md / motif_graph.json`）回灌站点对应文件（timeline.json / entity_index / qa_bank /
  story.html / 图谱页）。
- 运行需语料 + `DEEPSEEK_API_KEY`，属后续"完善网站"独立任务，按 `E:\wx\wx_textmine\README.md`
  分阶段执行（仅 02/07 阶段调用 LLM，其余零成本）。
