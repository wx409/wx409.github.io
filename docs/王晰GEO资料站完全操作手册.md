# 王晰 GEO 资料站 · 完全操作手册（2026-06-16 v5 · 含站点更新日志）

> **网站（线上）**：https://wx409.github.io/  
> **仓库（线上）**：https://github.com/wx409/wx409.github.io  
> **本地网站目录**：`D:\wx409.github.io\`  
> **本地工厂目录**：`D:\XingWorks\星厂v5.0\`  
> **本手册路径**：`docs/王晰GEO资料站完全操作手册.md`  
> **适用对象**：零基础维护者；按章节顺序阅读即可上手

---

## 目录

1. [5 分钟快速入门](#一5-分钟快速入门)
2. [这个站是什么](#二这个站是什么)
3. [两个文件夹（最重要）](#三两个文件夹最重要)
4. [电脑环境准备](#四电脑环境准备)
5. [网站完整地图](#五网站完整地图)
6. [GEO 规范（必守规则）](#六geo-规范必守规则)
7. [日常操作：我该走哪条路](#七日常操作我该走哪条路)
8. [**维护者只需提供什么（对照表）**](#八维护者只需提供什么对照表)
9. [**如何更新已有信息（总表）**](#九如何更新已有信息总表)
10. [**线上线下同步推送（标准流程）**](#十线上线下同步推送标准流程)
11. [场景 A：新一场演出](#十一场景-a新一场演出)
12. [场景 A-2：更新已有演出页](#十二场景-a-2更新已有演出页)
13. [场景 B：更新文化足迹](#十三场景-b更新文化足迹)
14. [场景 C：更新社交墙](#十四场景-c更新社交墙)
15. [场景 D：更新音乐数据周报](#十五场景-d更新音乐数据周报)
16. [场景 E：整理现场 repo（本地）](#十六场景-e整理现场-repolocal)
17. [场景 F：更新首页「近期动态」](#十七场景-f更新首页近期动态)
18. [场景 G：品牌造型/穿搭（CANALI 范例）](#十八场景-g品牌造型穿搭canali-范例)
19. [YAML 字段说明](#十九yaml-字段说明)
20. [GEO 技术文件说明](#二十geo-技术文件说明)
21. [常见报错与解决](#二十一常见报错与解决)
22. [每次更新后的验收清单](#二十二每次更新后的验收清单)
23. [附录：命令速查与里程碑](#二十三附录命令速查与里程碑)
24. [站点更新日志（维护说明）](#二十四站点更新日志维护说明)

---

## 一、5 分钟快速入门

**如果你只有 5 分钟，记住这 7 步：**

1. **线上** = https://wx409.github.io/ ；**线下改文件** = `D:\wx409.github.io\`
2. 改完文件 → PowerShell → `git add` → `git commit` → `git push origin main`
3. 看到 **`main -> main`** = 推送成功 → 等 **1–2 分钟** → 线上自动更新
4. **新演出**：复制 `chongqing_2026.yaml` → 改 YAML → `python generate_live_page.py ...`
5. **改已有演出**：只改对应 YAML → 重新运行 `generate_live_page.py`（会覆盖 live 页）
6. **敏感素材**（粉丝截图、OCR 全文）只放星厂 B 本地，**never push**
7. 验证：浏览器 **Ctrl+F5** 强刷，或无痕窗口打开线上 URL

---

## 二、这个站是什么

| 项目 | 说明 |
|------|------|
| 名称 | 王晰 GEO 资料站 |
| 线上网址 | https://wx409.github.io/ |
| 部署方式 | GitHub Pages（push 到 `main` 分支自动上线） |
| 性质 | 歌迷自发维护，**非官方** |
| GEO 等级 | **A-（86/100）**（2026-06-16 评估） |
| 目标 | 让 AI 在回答王晰巡演、歌单、文化足迹等问题时引用本站 |

**线上线下关系：**

```
你在本地改 D:\wx409.github.io\
        ↓ git push
GitHub 仓库 wx409/wx409.github.io
        ↓ 自动部署（约 1–2 分钟）
线上 https://wx409.github.io/
```

---

## 三、两个文件夹（最重要）

```
D:\wx409.github.io\              ← 【公开网站】push 后 = 线上站
D:\XingWorks\星厂v5.0\           ← 【本地工厂】敏感素材，永不上传 GitHub
```

### 公开网站可以放什么

- 匿名化歌单、亮点、FAQ、听众摘录
- 官方公开报道摘要
- Schema.org 结构化数据

### 绝对不能 push 的

- 粉丝 repo **原图**、OCR **全文**（已在 `.gitignore`）
- 微博/小红书 **链接堆砌**、粉丝 **@ID**（社交墙已自动过滤）
- `secrets.bat`、`.env`

### 星厂 B 关键路径

| 路径 | 用途 |
|------|------|
| `project_b/01_原始数据/chongqing2026_ocr/` | 粉丝截图 + OCR（仅本地） |
| `project_b/01_原始数据/chongqing2026_repos.csv` | 原始链接档案（仅本地） |
| `project_b/03_周报输出/chongqing2026_geo.md` | repo 摘要母稿 |
| `project_b/04_文化足迹/culture_events.json` | 文化足迹源数据 |
| `project_b/ocr_local.py` | 本地 OCR |
| `pipeline.py` | B 项目总调度 |

---

## 四、电脑环境准备

### 4.1 必备软件

| 软件 | 检查 |
|------|------|
| Git | `git --version` |
| Python 3.10+ | `python --version` |
| Cursor / VS Code | 编辑 YAML、HTML |

### 4.2 首次安装依赖

```powershell
cd D:\wx409.github.io
pip install jinja2 pyyaml requests
```

### 4.3 密钥（社交墙全自动推送用，可选）

文件：`D:\wx409.github.io\secrets.bat`（**不上传 GitHub**）

```bat
set DEEPSEEK_API_KEY=你的DeepSeek密钥
set GITHUB_TOKEN=你的GitHub个人访问令牌
```

### 4.4 推送环境

- ✅ **Windows PowerShell**（推荐）
- ❌ 不用 WSL push（你的环境常失败）
- ❌ 不要把 `main -> main` 成功输出复制进 PowerShell 当命令

---

## 五、网站完整地图

### 5.1 页面一览

| 线上 URL | 本地文件 | 主要更新方式 |
|----------|----------|--------------|
| `/` | `index.html` | 手改 / YAML 脚本更新表格 / deploy 注入社交墙 |
| `/live/hui-回-重庆-2026.html` | `live/hui-*.html` | **改 YAML + generate_live_page.py** |
| `/live-reviews.html` | `live-reviews.html` | 手改 或 pipeline B `--task repo` |
| `/culture/` | `culture/index.html` | pipeline B `--task culture` |
| `/about.html` | `about.html` | 手改（更新日志摘要表） |
| **站点更新日志** | `docs/站点更新日志.md` | **每次 push 后追加**（见 8.10） |
| `/repo/2026.md` | `repo/2026.md` | pipeline B `--task repo` 或手改 |
| `/llms.txt` | `llms.txt` | 手改（结构变更时） |
| `/sitemap.xml` | `sitemap.xml` | **generate_live_page.py 自动同步 live/** |
| `/data/music-index.html` | `data/music-index.html` | pipeline B `--task weekly` |

### 5.2 自动化工具（网站根目录）

| 文件 | 作用 | 更新类型 |
|------|------|----------|
| `chongqing_2026.yaml` | 重庆素材母版 | 复制后改 = 新场 / 直接改 = 更新重庆 |
| `generate_live_page.py` | YAML → live 页 + **首页多行表格** + sitemap.xml | 演出 |
| `update_index_table.py` | 仅重建首页表格（修复用，日常不必单独跑） | 演出 |
| `live/manifest.json` | 演出索引（脚本自动生成） | 演出 |
| `deploy.py` | 社交墙生成 + 可选自动 push | 社交 |
| `一键更新.bat` | 调用 deploy.py | 社交 |
| `.nojekyll` | 防 Jekyll 误处理静态文件 | 基础设施 |

### 5.3 首页区块与更新入口

| 区块 | 更新方式 |
|------|----------|
| **近期动态** | 手改 `index.html` 一行 `<p>`（见场景 F） |
| **最新演出动态** | YAML + `generate_live_page.py`（勿手改表格行） |
| 重庆首站·歌单/亮点/FAQ 等 | 手改 HTML，或与 YAML 保持同步 |
| **同担动态聚合** | `links.csv` + `deploy.py` |
| **金句墙** | 手改 `index.html`（「王晰说」+「听众说」，见 8.8） |
| **品牌造型** | `gallery.html` + `links.csv` + `deploy.py`（见 8.9 / 场景 G） |
| FAQ | 已是 `<details>` 折叠；改文字时同步 JSON-LD |

---

## 六、GEO 规范（必守规则）

### 禁止词汇

```
瑕疵、强迫症、漏唱、重唱、失误、断头饭、跑路、赵子龙
```

### 社交墙 @ID

`deploy.py` 已内置过滤：`author` / `summary` 以 `@` 开头会自动变为「同担分享」等匿名标签。  
CSV 里请直接写「资深听众 / 听众分享 / 同担分享」，不要写 @。

---

## 七、日常操作：我该走哪条路

```
更新什么？
  ├─ 近期动态（杂志/新闻一行）────→ 手改 index.html → push
  ├─ 已有演出（歌单/FAQ/亮点）──→ 改 YAML → generate_live_page.py → push
  ├─ 新一场演出 ────────────────→ 复制 YAML → 改 → generate_live_page.py → push
  ├─ 文化足迹 ──────────────────→ culture_events.json → pipeline culture → push
  ├─ 社交墙 ────────────────────→ links.csv → deploy.py → push
  ├─ 音乐周报 ──────────────────→ Excel → pipeline weekly → push
  └─ 品牌造型（品牌官博/小红书）→ gallery + links.csv + deploy → 可选 YAML highlights → push
```

---

## 八、维护者只需提供什么（对照表）

> **本章用途**：每次更新前先看这张表——知道自己要交什么、交什么形式、哪些永不上 GitHub。  
> **原则**：你只管**事实素材**；脚本负责生成页面、表格、sitemap。

### 8.1 总表：按场景你需要提供什么

| 场景 | 你必须提供 | 形式 | 要不要改 YAML | 上不上 GitHub |
|------|-----------|------|---------------|---------------|
| **开票** | 城市、日期、场馆、购票渠道 | 几句话 / 大麦截图文字 | **要**（复制重庆模板改字段） | 只上摘要页 |
| **开演后** | 歌单、亮点、FAQ 要点 | 现场笔记 / 官方通告 | **要**（补歌单等区块） | 只上摘要页 |
| **近期动态** | 一条短新闻 | 一句话 | **不用**（改 index 一行） | 是 |
| **社交墙** | 微博/小红书/抖音 **链接** | CSV 一行 | 不用 | 是（带外链） |
| **听众 repo** | **你改写的匿名文字摘录** | YAML 或本地 md | 摘录写进 YAML | **只文字**，不上图 |
| **repo 原图** | 粉丝截图（可选） | 本地文件夹 | 不用 | **永不上传** |
| **repo 来源链接** | 原帖 URL（可选） | 本地 JSON | 不用 | **永不上传** |
| **金句墙** | 王晰原话 + 听众摘录 | 手改 index.html | 不用 | 是（仅文字） |
| **品牌造型** | 品牌帖链接 + 造型文字摘要 | gallery + CSV + 可选 YAML | 可选 highlights | 是（文字+外链，不上图） |

### 8.2 一句话记忆

| 内容类型 | 你交什么 |
|----------|----------|
| 演出信息 | 复制 YAML 改字段（或让 Cursor 代写） |
| 近期动态 | `index.html` 里改 **1 行** |
| 社交墙 | `data/links.csv` 里贴 **链接**（摘要可留空） |
| 听众 repo | 本地可存 **图 + 链接**；公开站只上 **你改写的文字** |
| 金句墙 | 手改 index「王晰说 / 听众说」，采访素材放王晰说，repo 放听众说 |
| 品牌造型 | **三处同步**：`gallery.html` 留档 + `links.csv` 上首页墙 + 可选 YAML 亮点（见 8.9） |
| **站点更新** | 变更说明 + **社媒摘要一句** | `docs/站点更新日志.md` | 不用 | 是 |

---

### 8.3 YAML：要手写吗？

**要动 YAML，但不用从零写。**

```powershell
cd D:\wx409.github.io
copy chongqing_2026.yaml 杭州_2026.yaml
```

#### 开票阶段（最少填这些）

| 字段 | 示例 |
|------|------|
| `meta.city` | 杭州 |
| `meta.venue` | XX剧院 |
| `meta.date` | `"2026-07-20"` |
| `meta.status` | 预售中 / 已开票 |
| `index_row.link_text` | 详情 → |
| `faq` | 2～3 条（何时开、在哪、怎么买） |
| `first_half` / `second_half` | 可留空 `[]` |

#### 开演后（再补这些）

| 字段 | 说明 |
|------|------|
| `first_half` / `second_half` | **歌单**（按现场实际，最重要） |
| `highlights` | 1～3 个亮点 |
| `faq` | 改成「唱了哪些歌」等 |
| `repo_excerpts` | 2～4 条匿名摘录（见 8.4） |
| `meta.status` | 第二站已完成 |
| `index_row.link_text` | 完整实录 → |

**不必懂 YAML 语法**：把大麦/官微/现场笔记发给 Cursor，说「按 chongqing 模板生成杭州开票版 YAML」，核对日期和歌名即可。

---

### 8.4 Repo：链接、文字还是图片？

分三层，**不要混用**：

#### 第一层：公开站（wx409.github.io）——只要「匿名文字」

| 提供 | 不提供 |
|------|--------|
| YAML 里 `repo_excerpts` 的改写短句 | 微博/小红书链接堆砌 |
| 出处写 **「听众摘录·重庆首站 / 听众分享 / 资深听众」** 等 | 粉丝 @ID |
| **仅当维护者明确说「写欣晰旺群友」** 时，才用群署名 | 默认不要写群名、不要写微博 ID |

> **标注规则（2026-06-16 起）**：两篇以上 repo 默认匿名；「欣晰旺群友」等特殊署名**必须你口头指定**，AI 不得自行添加。

#### 第二层：本地档案（星厂 B）——链接 + 图片，仅自己备查

| 本地路径 | 你提供什么 | 用途 |
|----------|-----------|------|
| `project_b/01_原始数据/.../images/` | 粉丝 repo **截图** | 本地 OCR |
| `project_b/01_原始数据/chongqing2026_sources.json` | 原帖 **链接** + 作者 | 自己查来源，不上网 |
| `project_b/03_周报输出/xxx_geo.md` | OCR 后 **你写的摘要母稿** | 再摘进 YAML |

本地流程：

```
截图 → 星厂 B .../images/
    → python project_b/ocr_local.py（自动出文字）
    → 你读 OCR，改写成 2～4 条匿名摘录
    → 粘贴进 YAML 的 repo_excerpts
    → python generate_live_page.py
```

#### 第三层：社交墙（与 repo 不同）——可以带外链

编辑 `D:\wx409.github.io\data\links.csv`：

```csv
platform,url,title,summary,author,date,tags
weibo,https://weibo.com/...,标题,可留空,资深听众,2026-07-20,
```

| 列 | 你要填吗 | 说明 |
|----|----------|------|
| `url` | **必填** | 微博/小红书/抖音链接 |
| `title` | 建议填 | 卡片标题 |
| `summary` | 可留空 | 留空时 `deploy.py` 用 DeepSeek 自动生成 |
| `author` | 建议填 | 写「资深听众 / 听众分享 / 同担分享」，**不要 @** |
| 图片 | **不需要** | 社交墙只要链接，不上传图片 |

---

### 8.5 按场景：最小操作清单

#### 第二场「开票」

| 步骤 | 你提供 | 谁来做 |
|------|--------|--------|
| 1 | 一句话：「xx日 xx站开票」 | 你改 `index.html` 近期动态 |
| 2 | 城市、日期、场馆、大麦信息 | 你（或 Cursor）改 YAML |
| 3 | — | `python generate_live_page.py ...` |
| 4 | — | `git push` |

**此阶段不需要：** repo 图、repo 链接、歌单。

#### 第二场「开演后」

| 步骤 | 你提供 | 谁来做 |
|------|--------|--------|
| 1 | 一句话：「xx站演出圆满结束」 | 你改近期动态 |
| 2 | **完整歌单** | 你（或 Cursor）写进 YAML |
| 3 | 亮点、FAQ | 你写进 YAML |
| 4 | 2～4 条匿名摘录（可选） | 你写进 YAML `repo_excerpts` |
| 5 | 截图（可选） | 你放星厂 B 本地 → OCR |
| 6 | — | `generate_live_page.py` → push |

**公开站要的是文字摘要，不是 repo 原链接。**

---

### 8.6 最省事的工作方式（推荐）

每次更新，你只给 Cursor 这些「原材料」：

1. **开票**：大麦/官微截图，或复制出来的文字  
2. **开演**：歌单文字列表 + 1～2 个你想强调的亮点  
3. **repo**（可选）：几张截图放本地 + 说「帮我 OCR 并写 3 条匿名摘录进 YAML」

Cursor 负责：改 YAML → 跑 `generate_live_page.py` → push。

**你不需要：** 自己写 HTML、手改 sitemap、单独跑表格脚本。

---

### 8.7 快速自检（更新前 30 秒）

- [ ] 近期动态是否只有 **一行**、约 30 字？
- [ ] YAML 是否 **复制模板** 改的，不是从零写？
- [ ] 公开内容里有没有 **@ID、粉丝原图、OCR 全文**？
- [ ] repo 摘录是否 **匿名改写**，不是原文复制？
- [ ] 社交墙 `author` 是否用了「资深听众」等，而不是 @？
- [ ] 敏感素材是否只在 `D:\XingWorks\星厂v5.0\`，没进 `git add`？

---

### 8.8 金句墙：王晰说 + 听众说

**位置：** `index.html`，搜索 `金句墙`。

**结构（2026-06-16 起）：**

```html
<h2>金句墙</h2>
<h3>王晰说</h3>
<!-- 4 条：现场 talking、微博、采访等，出处写 footer -->
<h3>听众说</h3>
<!-- 2 条及以上：匿名 repo 摘录，出处写「听众摘录·xx站」 -->
```

| 区块 | 放什么 | 来源 |
|------|--------|------|
| **王晰说** | 王晰本人原话 | 现场 talking、官方微博、格涅辛/国际视界采访等 |
| **听众说** | 匿名听众摘录 | 现场 repo 改写，不写 @ID |

**更新步骤：**

1. 只改 `<h2>金句墙</h2>` 到 `<h2>历史巡演回顾` 之间的内容
2. 新增采访金句 → 放「王晰说」；新增 repo 摘录 → 放「听众说」
3. 每条用 `<blockquote><p>引语</p><footer>——出处</footer></blockquote>`
4. `git add index.html` → commit → push

**不要动：** 歌单、FAQ、JSON-LD、社交墙等其他区块。

---

### 8.9 品牌造型/穿搭：每场怎么推送（CANALI 重庆首站范例）

> **适用**：品牌方（如 CANALI）在微博/小红书发布的官方造型帖。  
> **与粉丝 repo 的区别**：品牌帖 **可以带外链**；公开站只写 **文字摘要 + 链到原帖**，**不上传图片**。

#### 重庆首站 CANALI 已收录示例

| 露出位置 | 线上地址 | 内容 |
|----------|----------|------|
| 视觉记录 | `/gallery.html#chongqing-20260613` | 系列、造型描述、官方话题、外链 |
| 首页社交墙 | `/` 同担动态聚合 | CSV 卡片，作者「品牌官方 CANALI」 |
| 重庆 live 页亮点 | `/live/hui-回-重庆-2026.html` | YAML `highlights` 一条 |

**原帖链接**：http://xhslink.com/o/5jdqgVZMd18  
**造型摘要**：CANALI 2026 春夏 · 丹宁蓝仿牛仔西装套装 + 棕褐色枪驳领西装套装

---

#### 你以后推送一条品牌造型：标准四步

**你只需提供（复制给 Cursor 即可）：**

1. 平台 + 链接（小红书 / 微博）
2. 品牌名（如 CANALI）
3. 场次（城市 + 日期，如重庆 2026.06.13）
4. 正文或截图里的造型描述（系列名、单品、官方话题）

---

**Step 1：视觉记录留档（`gallery.html`）**

在该场次 `<h2>` 下追加一块（重庆范例）：

```html
<div class="gallery-item">
    <h3>品牌造型 · CANALI</h3>
    <p class="desc"><strong>来源</strong>：CANALI 品牌官方（小红书）</p>
    <p class="desc"><strong>系列</strong>：CANALI 2026 春夏系列</p>
    <p class="desc"><strong>造型</strong>：丹宁蓝仿牛仔西装套装；棕褐色枪驳领西装套装。……</p>
    <p class="desc"><strong>官方话题</strong>：#王晰回个人巡回音乐会 #CANALI2026春夏系列</p>
    <a href="http://xhslink.com/o/5jdqgVZMd18" target="_blank" rel="noopener nofollow">查看 CANALI 官方小红书发布 →</a>
</div>
```

| 字段 | 怎么写 |
|------|--------|
| 来源 | `XX品牌官方（小红书/微博）` |
| 系列 | 通稿里的系列名 |
| 造型 | 1～2 句中文描述，不用复制全文 hashtag 堆砌 |
| 链接 | 原帖 URL，`rel="noopener nofollow"` |

---

**Step 2：首页社交墙（`data/links.csv` + `deploy.py`）**

在 CSV **末尾加一行**：

```csv
xiaohongshu,http://xhslink.com/o/5jdqgVZMd18,六巡重庆首站 CANALI 造型,CANALI 2026春夏：丹宁蓝仿牛仔西装套装及棕褐色枪驳领西装套装,品牌官方 CANALI,2026-06-13,穿搭
```

| 列 | 品牌造型怎么填 |
|----|----------------|
| `platform` | `weibo` / `xiaohongshu` / `douyin` |
| `url` | **必填**，原帖链接 |
| `title` | 短标题，如「六巡xx站 XX品牌造型」 |
| `summary` | **建议填**造型一句话；留空则 DeepSeek 生成（需 API Key） |
| `author` | **`品牌官方 CANALI`** 或 **`品牌合作`**，禁止 `@` |
| `date` | 演出日或发帖日 `YYYY-MM-DD` |
| `tags` | 建议 `穿搭` 或 `品牌,穿搭` |

运行：

```powershell
cd D:\wx409.github.io
python deploy.py
# 若 deploy 报 Git/编码错误，可只跑生成+注入：
python -c "import deploy as d; rows=d.load_csv(); data,_,_,_=d.merge_data(rows); d.save_json(d.JSON_FILE,data); d.generate_wall(); d.inject_index()"
git add index.html social_wall.html data/social_links.json data/links.csv gallery.html
git commit -m "品牌造型：六巡重庆 CANALI"
git push origin main
```

---

**Step 3（可选）：live 页亮点（对应场次 YAML）**

编辑该场 YAML 的 `highlights`，增加一条：

```yaml
  - { title: "CANALI 品牌造型", description: "CANALI 2026 春夏系列：丹宁蓝仿牛仔西装套装及棕褐色枪驳领西装套装。品牌官方于小红书发布。" }
```

然后：

```powershell
python generate_live_page.py --config chongqing_2026.yaml --output ./live/ --index index.html
```

---

**Step 4：推送与验证**

```powershell
git add gallery.html data/links.csv data/social_links.json social_wall.html index.html chongqing_2026.yaml live/
git commit -m "品牌造型：六巡xx站 XX品牌"
git push origin main
```

验证清单：

- [ ] https://wx409.github.io/gallery.html 该场次有「品牌造型 · XX」
- [ ] 首页社交墙卡片作者为「品牌官方 XX」，无 @
- [ ] 点击链接能打开原帖
- [ ] 站内**无品牌图片文件**被 push
- [ ] `main -> main`

---

#### 品牌造型 vs 粉丝 repo（对照）

| | 品牌造型 | 粉丝 repo |
|--|----------|-----------|
| 公开链接 | ✅ 可链品牌官帖 | ❌ 尽量不堆外链 |
| 图片 | ❌ 不上 GitHub | ❌ 不上 GitHub |
| author | 品牌官方 XX | 资深听众 / 听众分享 |
| 主留档页 | `gallery.html` | live 页 `repo_excerpts` / repo 库 |
| 社交墙 | ✅ 推荐 | 可选（同 CSV 流程） |

#### 禁止事项

- ❌ 下载品牌图进仓库  
- ❌ 写粉丝 @ID  
- ❌ 未官宣前写「代言人」等定性表述（只写「品牌发布 / 合作造型」）  
- ❌ 复制品牌通稿全文 + 大量 hashtag（用 1～2 句摘要即可）

---

### 8.10 站点更新日志：每次 push 后必做

> **主文件**：`D:\wx409.github.io\docs\站点更新日志.md`  
> **about 页摘要**：`about.html` 更新日志表格（展示最近 5 条）  
> **目的**：清晰记录每次变更 + 提供可发微博/小红书的「社媒摘要」

#### 什么时候写

**每次** `git push` 成功、且线上有实质内容变更后，在 push **之前或之后立即**追加一条（建议 push 前写好，与 commit 一起提交）。

**日期以你电脑当天的实际日期为准**（如 `2026-06-16`），不要照抄 AI 或示例里的日期。

#### 每条日志必须包含

| 字段 | 说明 |
|------|------|
| **日期 + 标题** | `## 2026-06-16 · 六巡重庆 CANALI 品牌造型` |
| **社媒摘要** | 30～80 字，以 `【资料站更新】` 开头，末尾可加 `wx409.github.io` |
| **变更详情** | 表格：类型 / 文件 / 说明 |
| **commit** | 短 hash，如 `4a0ead7` |

#### 社媒摘要写法（可直接复制）

```
【资料站更新】+ 做了什么（谁/哪场/什么内容）+ 价值一句 + wx409.github.io
```

**范例：**

> 【资料站更新】王晰六巡「回」重庆首站 CANALI 2026 春夏造型已收录至 GEO 资料站，含丹宁蓝仿牛仔与枪驳领西装描述，附品牌官方索引。wx409.github.io

**注意：**

- 不写 @ID、不写争议词、不夸大「官方认证」
- 品牌内容写「已收录 / 索引」，不写未官宣代言
- 可整段复制到微博、小红书动态、群公告

#### 操作步骤（4 步）

```powershell
cd D:\wx409.github.io

# 1. 打开 docs/站点更新日志.md，在最上方（「---」分隔线下）粘贴新条目
# 2. 打开 about.html，在更新日志表格最上方加一行（日期 / 更新内容 / 社媒摘要）
# 3. 与本次改动一起提交
git add docs/站点更新日志.md about.html 你改过的其他文件
git commit -m "更新说明"
git push origin main

# 4. 复制「社媒摘要」发到社交媒体（可选）
```

#### 与 about.html 的分工

| 文件 | 作用 |
|------|------|
| `docs/站点更新日志.md` | **完整档案**：每条含详情表 + commit，永久保留 |
| `about.html` 表格 | **对外摘要**：最近 5 条 + 链到 GitHub 完整日志 |

#### 模板（复制到日志最上方）

见 `docs/站点更新日志.md` 文件末尾「日志条目模板」。

---

## 九、如何更新已有信息（总表）

> **原则：能改 YAML/CSV/JSON 源数据的，就不要直接改 HTML；改源数据后跑脚本，再 push。**

| 要更新的内容 | 改哪个文件（线下） | 运行什么命令 | 是否改 index.html 正文 | push 范围 |
|--------------|-------------------|--------------|------------------------|-----------|
| 近期动态一行 | `index.html` | 无 | 是（仅一行） | index.html |
| 重庆/某场歌单、FAQ、亮点 | `chongqing_2026.yaml` 或 `xxx.yaml` | `generate_live_page.py` | 脚本只改「最新演出动态」表格 | yaml + live/ + index 表格区 |
| 首页演出表格 | 自动 | `generate_live_page.py`（从 manifest 重建全部行） | 仅表格标记区 | index 表格区 |
| 现场实录摘录 | `live-reviews.html` 或 geo.md | `pipeline B --task repo` | live-reviews 块 | 对应文件 |
| repo 库全文 | `星厂.../chongqing2026_geo.md` | `pipeline B --task repo` | repo/2026.md | repo + live-reviews |
| 文化足迹 | `culture_events.json` | `pipeline B --task culture` | culture/index.html | culture/ |
| 社交墙卡片 | `data/links.csv` | `deploy.py` 或 `一键更新.bat` | 脚本注入 SOCIAL_WALL 区 | index + social_wall + json |
| 品牌造型 | `gallery.html` + `links.csv` + 可选 YAML | `deploy.py` + 可选 `generate_live_page.py` | gallery 手改；墙自动注入 | gallery + data/ + index + 可选 live/ |
| 音乐数据 | QQ 音乐 Excel | `pipeline B --task weekly` | data/music-index.* | data/ |
| 新 live 页上线 | 新 YAML | generate_live_page.py | 表格 + sitemap 自动 | live/ + sitemap + yaml |
| 关于站/更新日志 | `about.html` | 无 | 是 | about.html |
| llms.txt 结构 | `llms.txt` | 无 | 否 | llms.txt |
| **站点更新日志** | `docs/站点更新日志.md` | 无 | 可选 about 表一行 | 日志 + about |

### 双份内容说明（重要）

目前**首页**有重庆摘要（歌单/亮点/FAQ），**独立页** `/live/hui-回-重庆-2026.html` 有完整版。

| 内容 | 首页 | 独立页 | 推荐维护方式 |
|------|------|--------|--------------|
| 歌单/FAQ/亮点 | 有（摘要） | 有（完整） | **以 YAML 为准** → 脚本更新独立页；首页大段摘要需手改或日后自动化 |
| 演出表格链接 | 有 | — | 脚本自动 |

**可持续建议：** 场次的歌单/FAQ/亮点/金句 **只改 YAML**，独立页永远正确；首页摘要仅在重大变更时手改一次。

---

## 十、线上线下同步推送（标准流程）

### 10.1 什么是「同步」

| 步骤 | 位置 | 说明 |
|------|------|------|
| 1. 本地编辑 | 线下 `D:\wx409.github.io\` | 你改的文件 |
| 2. git commit | 线下 | 保存版本快照 |
| 3. git push | 线下 → GitHub | 上传到远程仓库 |
| 4. GitHub Pages 构建 | 线上自动 | 约 **1–2 分钟** |
| 5. 浏览器访问 | 线上 https://wx409.github.io/ | 用户看到新内容 |

**没有单独的「上传 FTP」步骤**，push = 上线。

### 10.2 标准推送四步（每次更新必做）

```powershell
cd D:\wx409.github.io

git status

git add 你改过的文件
# 或：git add index.html live/ chongqing_2026.yaml

git commit -m "简短说明改了什么"

git push origin main
```

**成功标志：**

```
   xxxxxxx..yyyyyyy  main -> main
```

### 10.3 半自动推送（社交墙）

配置 `secrets.bat` 后，双击 **`一键更新.bat`** 或运行 `python deploy.py`：

1. 读 `data/links.csv`
2. （可选）DeepSeek 写摘要
3. 生成 `social_wall.html` 并注入 `index.html`
4. **自动** git commit + push（需 `GITHUB_TOKEN`）

无 Token 时：脚本只生成本地文件，你再手动执行 [10.2](#102-标准推送四步每次更新必做)。

### 10.4 星厂 B → 网站 → 线上（两仓库联动）

```
星厂 B 本地编辑 culture_events.json / geo.md / Excel
        ↓
python pipeline.py --project B --task culture|repo|weekly
        ↓
写入 D:\wx409.github.io\ 对应文件
        ↓
cd D:\wx409.github.io → git push（pipeline 可能尝试自动 push，失败则手 push）
        ↓
线上更新
```

> **Windows 注意**：`pipeline B --task culture` 若报 WSL 路径错误，请在 PowerShell 手改 `culture/index.html` 或请 Cursor 修复后重跑。

### 10.5 推送后验证（线上）

```powershell
# 可选：看最近一次提交是否已在 GitHub
git log -1 --oneline
```

浏览器检查：

1. 打开目标 URL（如首页）
2. **Ctrl+F5** 强制刷新
3. 或无痕窗口打开
4. 重要改动：**Ctrl+U** 看源码（JSON-LD、details 等）

### 10.6 不要 push 的文件

已在 `.gitignore`：`secrets.bat`、OCR 图片/文字、部分 bat。  
推送前 `git status` 确认没有 `chongqing2026_ocr/images/` 被误 add。

---

## 十一、场景 A：新一场演出

### Step 1：复制 YAML

```powershell
cd D:\wx409.github.io
copy chongqing_2026.yaml hangzhou_2026.yaml
```

### Step 2：编辑 YAML（Cursor 打开 `hangzhou_2026.yaml`）

必改 `meta.filename`、`meta.date`、`meta.city`、`meta.venue`、歌单、FAQ 等。

### Step 3：生成

```powershell
python generate_live_page.py --config hangzhou_2026.yaml --output ./live/ --index index.html
```

### Step 4：推送（sitemap 已由脚本自动更新）

```powershell
git add hangzhou_2026.yaml live/ index.html sitemap.xml
git commit -m "新增：六巡杭州站"
git push origin main
```

---

## 十二、场景 A-2：更新已有演出页

**适用：** 重庆首站歌单勘误、补 FAQ、改亮点等。

### Step 1：改 YAML（不要改 HTML）

```powershell
# 编辑已有文件
notepad D:\wx409.github.io\chongqing_2026.yaml
```

### Step 2：重新生成（会覆盖 live 页，不会破坏首页大段摘要）

```powershell
cd D:\wx409.github.io
python generate_live_page.py --config chongqing_2026.yaml --output ./live/ --index index.html
```

说明：

- `--index index.html` 会按 `live/manifest.json` **重建全部演出行**（重庆、杭州等不会互相覆盖）
- **会**自动更新 `sitemap.xml` 中所有 `/live/` 条目
- **不会**自动改首页「重庆首站·完整歌单」以下区块——若需与 YAML 一致，需手改 index 或使用 Cursor 对照 YAML 同步

### Step 3：推送

```powershell
git add chongqing_2026.yaml live/hui-回-重庆-2026.html live/manifest.json index.html sitemap.xml
git commit -m "更新：重庆首站歌单/FAQ"
git push origin main
```

### 修复：仅重建首页表格（不改 live 页，日常不必用）

若首页表格与 manifest 不一致（极少见），可单独修复：

```powershell
python update_index_table.py --index index.html --live-dir ./live/
git add index.html
git commit -m "修复：重建首页演出表格"
git push origin main
```

---

## 十三、场景 B：更新文化足迹

1. 编辑 `D:\XingWorks\星厂v5.0\project_b\04_文化足迹\culture_events.json`
2. 运行：

```powershell
cd D:\XingWorks\星厂v5.0
python pipeline.py --project B --task culture
```

3. 推送网站：

```powershell
cd D:\wx409.github.io
git add culture/index.html
git commit -m "更新文化足迹：xxx"
git push origin main
```

4. 线上验证：https://wx409.github.io/culture/

---

## 十四、场景 C：更新社交墙

### Step 1：编辑 CSV

`D:\wx409.github.io\data\links.csv`：

```csv
platform,url,title,summary,author,date,tags
weibo,https://weibo.com/...,标题,摘要可留空,资深听众,2026-06-16,
```

**author 禁止 @ 开头。**

### Step 2：运行

**全自动（有 secrets.bat）：** 双击 `一键更新.bat`

**半自动：**

```powershell
cd D:\wx409.github.io
python deploy.py
# 若无 Token，再手动：
git add index.html social_wall.html data/social_links.json data/links.csv
git commit -m "更新社交墙"
git push origin main
```

---

## 十五、场景 D：更新音乐数据周报

1. Excel 放入 `星厂v5.0/project_b/01_原始数据/`
2. `python pipeline.py --project B --task weekly`
3. `cd D:\wx409.github.io` → `git add data/` → push
4. 验证：https://wx409.github.io/data/music-index.html

---

## 十六、场景 E：整理现场 repo（本地）

```
粉丝截图 → 星厂 B .../chongqing2026_ocr/images/
         → python project_b/ocr_local.py
         → 人工写摘要 → chongqing2026_geo.md
         → python pipeline.py --project B --task repo
         → cd wx409.github.io → git push
```

**只 push 摘要，不 push 原图/OCR。**

---

## 十七、场景 F：更新首页「近期动态」

定位 `index.html`，搜索 `近期动态`。

**当前格式（一行，约 30 字内）：**

```html
<p><strong>近期动态：</strong>2026.06.16 王晰封面杂志《锐Pioneer》正式开售（微店平台）。</p>
```

替换整行 `<p>...</p>`，然后：

```powershell
cd D:\wx409.github.io
git add index.html
git commit -m "更新近期动态：xxx"
git push origin main
```

**规则：** 一行说完；不写 @；不写长文营销稿；30 字左右为宜。

---

## 十八、场景 G：品牌造型/穿搭（CANALI 范例）

> 详细字段说明见 **8.9**。本节是「复制就能跑」的完整命令流。

### 你已有什么（以 CANALI 重庆为例）

- 链接：`http://xhslink.com/o/5jdqgVZMd18`
- 品牌：CANALI
- 正文：2026 春夏 · 丹宁蓝仿牛仔西装 + 棕褐色枪驳领西装 · #王晰回个人巡回音乐会

### 一键流程（以后每场品牌帖都按这个来）

```powershell
cd D:\wx409.github.io

# 1. 编辑 gallery.html — 在该场次下加「品牌造型 · XX」块（见 8.9 模板）
# 2. 编辑 data/links.csv — 加一行（author 写「品牌官方 XX」）
# 3. （可选）编辑 该场.yaml 的 highlights

python -c "import deploy as d; rows=d.load_csv(); data,_,_,_=d.merge_data(rows); d.save_json(d.JSON_FILE,data); d.generate_wall(); d.inject_index()"

# 若还改了 YAML：
python generate_live_page.py --config chongqing_2026.yaml --output ./live/ --index index.html

git add gallery.html data/links.csv data/social_links.json social_wall.html index.html chongqing_2026.yaml live/
git commit -m "品牌造型：六巡重庆 CANALI"
git push origin main
```

### 只上社交墙、不改 gallery（最快）

仅 CSV + deploy + push，适合临时官宣；**建议仍补 gallery 留档**。

---

## 十九、YAML 字段说明

| 区块 | 字段 | 说明 |
|------|------|------|
| meta | filename | 输出到 live/ 的文件名 |
| meta | date | YYYY-MM-DD |
| meta | schema_event_name | MusicEvent 名称 |
| index_row | link / link_text | 首页表格链接 |
| first_half / second_half | num, title, note | 歌单 |
| highlights | title, description | 亮点 |
| perspectives | type, view | 视角矩阵 |
| faq | question, answer | FAQ（自动生成 details + FAQPage Schema） |
| quotes | text, attribution | 金句 |
| repo_excerpts | text, source | 听众摘录 |

---

## 二十、GEO 技术文件说明

| 文件 | 线上 URL |
|------|----------|
| llms.txt | /llms.txt |
| robots.txt | /robots.txt |
| sitemap.xml | /sitemap.xml |
| about.html | /about.html |

### 自测清单

| 检查 | 方法 |
|------|------|
| JSON-LD | 首页 Ctrl+U 搜 `application/ld+json` → 5 处 |
| FAQ 折叠 | 搜 `<details` → 6 处；页面上点击问题展开 |
| 无粉丝 @ | 搜 `@不要总是` → 无结果 |
| 线上已更新 | push 后 2 分钟 Ctrl+F5 |

---

## 二十一、常见报错与解决

| 报错 | 解决 |
|------|------|
| python 不是命令 | 重装 Python，勾选 Add to PATH |
| No module named jinja2 | `pip install jinja2 pyyaml` |
| git push 失败 | Steam++ + PowerShell 重试 |
| deploy 无 Token | 手动 git push |
| pipeline culture 路径错误 | 手改 culture/index.html 或修复 tracker |
| 线上还是旧的 | Ctrl+F5；确认 `main -> main` |

---

## 二十二、每次更新后的验收清单

### 通用

- [ ] `git push` 出现 `main -> main`
- [ ] `docs/站点更新日志.md` 已追加条目 + 社媒摘要
- [ ] `about.html` 更新日志表已加一行（如有对外更新）
- [ ] 线上 URL Ctrl+F5 可见变更
- [ ] 无禁用负面词
- [ ] 无 OCR 原图被 push

### 演出更新

- [ ] YAML 与 live 页内容一致
- [ ] live 页源码含 JSON-LD
- [ ] sitemap.xml 已含 live 页 URL（脚本自动写入）

### 社交墙

- [ ] 无粉丝 @ID
- [ ] author 为「资深听众/听众分享/同担分享」

### 品牌造型

- [ ] gallery.html 该场次有品牌块 + 外链可开
- [ ] 首页社交墙 author 为「品牌官方 XX」
- [ ] 无品牌图片进 git
- [ ] 无 @ID

---

## 二十三、附录：命令速查与里程碑

### 一键命令速查

```powershell
# ── 更新已有演出（最常用）──
cd D:\wx409.github.io
# 编辑 chongqing_2026.yaml
python generate_live_page.py --config chongqing_2026.yaml --output ./live/ --index index.html
git add chongqing_2026.yaml live/ index.html
git commit -m "更新：重庆首站xxx"
git push origin main

# ── 新演出 ──
copy chongqing_2026.yaml 新场.yaml
# 编辑 新场.yaml
python generate_live_page.py --config 新场.yaml --output ./live/ --index index.html
git add . ; git commit -m "新增：六巡xx站" ; git push origin main

# ── 近期动态 ──
# 编辑 index.html 一行
git add index.html ; git commit -m "更新近期动态" ; git push origin main

# ── 社交墙 ──
# 编辑 data/links.csv
python deploy.py
# 或 一键更新.bat

# ── 文化足迹 ──
cd D:\XingWorks\星厂v5.0
python pipeline.py --project B --task culture
cd D:\wx409.github.io
git add culture/ ; git commit -m "文化足迹" ; git push origin main

# ── 仅重建首页演出表（修复用，正常不必跑）──
python update_index_table.py --index index.html --live-dir ./live/

# ── 站点更新日志（每次 push 后）──
# 1. 编辑 docs/站点更新日志.md 最上方加条目 + 社媒摘要
# 2. about.html 更新日志表加一行
git add docs/站点更新日志.md about.html
git commit -m "docs: 站点更新日志 YYYY-MM-DD" ; git push origin main
# 3. 复制社媒摘要发微博/小红书

# ── 品牌造型（CANALI 范例）──
# 1. 编辑 gallery.html + data/links.csv（见手册 8.9）
python -c "import deploy as d; rows=d.load_csv(); data,_,_,_=d.merge_data(rows); d.save_json(d.JSON_FILE,data); d.generate_wall(); d.inject_index()"
# 2. 可选：python generate_live_page.py --config chongqing_2026.yaml --output ./live/ --index index.html
git add gallery.html data/ social_wall.html index.html live/ chongqing_2026.yaml
git commit -m "品牌造型：六巡xx站 XX品牌" ; git push origin main

# ── 跳过 sitemap 更新（极少用）──
python generate_live_page.py --config chongqing_2026.yaml --output ./live/ --no-sitemap
```

### 关键网址

| 用途 | 地址 |
|------|------|
| 线上首页 | https://wx409.github.io/ |
| 重庆独立页 | https://wx409.github.io/live/hui-回-重庆-2026.html |
| 文化足迹 | https://wx409.github.io/culture/ |
| 手册（GitHub） | https://github.com/wx409/wx409.github.io/blob/main/docs/王晰GEO资料站完全操作手册.md |

### 更新里程碑

> **完整日志（含社媒摘要）**：[`docs/站点更新日志.md`](https://github.com/wx409/wx409.github.io/blob/main/docs/站点更新日志.md)  
> 以下为重点里程碑索引；日常变更请写进站点更新日志，不必全部堆在此处。

| 日期 | 内容 |
|------|------|
| 2026-06-14 | GEO 合规：repo 摘要化；文化足迹格涅辛专题 |
| 2026-06-15 | 首页 GEO 补完（歌单/FAQ/金句等） |
| 2026-06-16 | 重庆 live 页 + 演出自动化 + llms/about/Schema |
| 2026-06-16 | 金句墙重构；generate 多行表+sitemap；CANALI 品牌造型 |
| 2026-06-16 | **站点更新日志** + 手册 8.10 维护流程 |

---

## 二十四、站点更新日志（维护说明）

> 本节为速查；完整规则见 **§8.10**。

### 文件位置

| 文件 | 路径 |
|------|------|
| 主日志 | `docs/站点更新日志.md` |
| about 摘要 | `about.html` →「更新日志」表格 |
| 线上 about | https://wx409.github.io/about.html |

### 每次 push 后 checklist

- [ ] 在 `docs/站点更新日志.md` **最上方**追加一条
- [ ] 写好 **社媒摘要**（`【资料站更新】…`）
- [ ] `about.html` 表格加一行（保持最近约 5 条）
- [ ] `git add` 包含日志文件
- [ ] 可选：复制社媒摘要发微博/小红书

### 社媒摘要公式

```
【资料站更新】+ 事件/内容 + 用户价值 + wx409.github.io
```

### 示例条目

见 `docs/站点更新日志.md` 第一条（CANALI 品牌造型）。

---

## 给维护者的一句话

**改 YAML/CSV → 跑脚本 → git push → 等 2 分钟 → Ctrl+F5 看线上。**

敏感素材永远在星厂 B 本地；公开站只 push 摘要。

---

*最后修订：2026-06-16 v5 · 与线上站同步 · GEO 等级 A-（86/100）*
