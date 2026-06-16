# 王晰 GEO 资料站 · 完全操作手册

> **版本**：2026-06-16（与当前线上站同步）  
> **网站**：https://wx409.github.io/  
> **仓库**：https://github.com/wx409/wx409.github.io  
> **适用对象**：零基础维护者，按章节顺序阅读即可

---

## 目录

1. [这个站是什么](#一这个站是什么)
2. [你需要知道的两个文件夹](#二你需要知道的两个文件夹)
3. [电脑环境准备（第一次必做）](#三电脑环境准备第一次必做)
4. [网站完整地图（每个页面干什么）](#四网站完整地图每个页面干什么)
5. [GEO 规范（什么能发、什么不能发）](#五geo-规范什么能发什么不能发)
6. [日常操作总览（我该用哪条路）](#六日常操作总览我该用哪条路)
7. [场景 A：新一场演出结束（最常用）](#七场景-a新一场演出结束最常用)
8. [场景 B：更新文化足迹](#八场景-b更新文化足迹)
9. [场景 C：更新社交墙 / 同担动态](#九场景-c更新社交墙--同担动态)
10. [场景 D：更新音乐数据周报](#十场景-d更新音乐数据周报)
11. [场景 E：整理现场 repo（本地备查）](#十一场景-e整理现场-repogeo-安全版)
12. [如何把修改推上线（Git 推送）](#十二如何把修改推上线git-推送)
13. [YAML 素材字段说明（演出页）](#十三yaml-素材字段说明演出页)
14. [技术基础设施说明（给 AI 看的）](#十四技术基础设施说明给-ai-看的)
15. [常见报错与解决](#十五常见报错与解决)
16. [验收清单（每次更新后对照）](#十六验收清单每次更新后对照)
17. [附录：文件清单与命令速查](#十七附录文件清单与命令速查)

---

## 一、这个站是什么

**王晰 GEO 资料站**是一个专为「生成式搜索引擎」（如 ChatGPT、Perplexity、Kimi 等）优化的**静态网站**。

| 项目 | 说明 |
|------|------|
| 正式网址 | https://wx409.github.io/ |
| 性质 | 歌迷自发维护，**非官方** |
| 技术 | GitHub Pages（纯 HTML，无数据库、无服务器） |
| 目标 | 让 AI 在回答「王晰巡演歌单」「重庆首站亮点」「王晰文化交流」等问题时，**优先引用本站** |
| 更新方式 | 本地改文件 → `git push` → 约 1–2 分钟自动上线 |

**GEO** = Generative Engine Optimization（生成式引擎优化），类似 SEO，但面向 AI 而不是传统百度/Google 排名。

---

## 二、你需要知道的两个文件夹

维护工作涉及**两个目录**，不要搞混：

```
D:\wx409.github.io\          ← 【公开网站】推上 GitHub，全世界可见
D:\XingWorks\星厂v5.0\       ← 【本地工厂】敏感素材、OCR、原始链接，不上传 GitHub
```

### 2.1 公开网站 `D:\wx409.github.io\`

这里面的内容会通过 GitHub 发布到 https://wx409.github.io/ 。

**可以放什么：**
- 匿名化的歌单、亮点、FAQ、听众摘录摘要
- 官方公开报道（新华社、塔斯社等）
- 结构化表格、Schema.org 标记

**绝对不能放什么：**
- 粉丝 repo **原图截图**
- OCR **全文草稿**
- 微博/小红书 **帖子链接堆砌**
- 粉丝 **@账号 ID**（除官方 @王晰 等公开渠道索引外，repo 区不写 ID）
- 「瑕疵」「漏唱」「断头饭」等负面争议词

### 2.2 本地工厂 `D:\XingWorks\星厂v5.0\`

| 路径 | 用途 |
|------|------|
| `project_b/01_原始数据/chongqing2026_repos.csv` | 原始链接档案（仅本地） |
| `project_b/01_原始数据/chongqing2026_ocr/` | 粉丝截图 + OCR 文字（仅本地） |
| `project_b/03_周报输出/chongqing2026_geo.md` | repo 摘要母稿 |
| `project_b/04_文化足迹/culture_events.json` | 文化足迹源数据 |
| `project_b/ocr_local.py` | 本地 OCR 脚本 |
| `pipeline.py` | B 项目总调度 |

---

## 三、电脑环境准备（第一次必做）

### 3.1 必备软件

| 软件 | 用途 | 检查命令 |
|------|------|----------|
| **Git** | 版本管理与推送 | 打开 PowerShell 输入 `git --version` |
| **Python 3.10+** | 运行自动化脚本 | `python --version` |
| **Cursor 或 VS Code** | 编辑 YAML / HTML | 图形界面即可 |
| **Steam++（可选）** | GitHub 网络加速 | 推送失败时使用 |

### 3.2 安装 Python 依赖（网站目录）

打开 **PowerShell**（推荐，不要用 WSL 推送），执行：

```powershell
cd D:\wx409.github.io
pip install jinja2 pyyaml requests
```

说明：
- `jinja2` + `pyyaml` → 演出页自动生成
- `requests` → 社交墙 AI 摘要（`deploy.py`）

### 3.3 配置密钥（社交墙自动推送用）

在 `D:\wx409.github.io\` 下应有 `secrets.bat`（**已在 .gitignore，不会上传 GitHub**）。

内容示例（向管理员索取真实密钥）：

```bat
set DEEPSEEK_API_KEY=你的DeepSeek密钥
set GITHUB_TOKEN=你的GitHub个人访问令牌
```

没有密钥也可以手动 `git push`，只是 `deploy.py` / `一键更新.bat` 无法自动推送。

### 3.4 打开项目的正确方式

1. 用 Cursor 打开文件夹：`D:\wx409.github.io`
2. 终端默认路径设为：`D:\wx409.github.io`
3. **推送一律用 Windows PowerShell**，不要用 WSL（你的环境 WSL 推送常失败）

---

## 四、网站完整地图（每个页面干什么）

### 4.1 页面导航表

| 网址路径 | 本地文件 | 内容 |
|----------|----------|------|
| `/` | `index.html` | **首页**：巡演动态表、重庆摘要、歌单、亮点、FAQ、金句、文化足迹摘要、社交墙 |
| `/live/hui-回-重庆-2026.html` | `live/hui-回-重庆-2026.html` | **重庆首站独立页**（完整版，含 Schema） |
| `/live-reviews.html` | `live-reviews.html` | 一巡～六巡历史场次索引 + 重庆摘录 |
| `/culture/` | `culture/index.html` | 文化足迹（莫斯科交流、格鲁吉亚、重庆都市艺术节等） |
| `/about.html` | `about.html` | 关于本站（维护团队、来源、审核原则） |
| `/repo/2026.md` | `repo/2026.md` | 2026 现场 repo 库（Markdown，GEO 安全版） |
| `/discography.html` | `discography.html` | 作品百科 |
| `/academic.html` | `academic.html` | 学术研究 |
| `/gallery.html` | `gallery.html` | 视觉记录（文字描述，无外链视频） |
| `/city-guides.html` | `city-guides.html` | 城市攻略 |
| `/data/music-index.html` | `data/music-index.html` | 音乐数据周报 |
| `/llms.txt` | `llms.txt` | 给 AI 爬虫的站点说明书 |
| `/robots.txt` | `robots.txt` | 搜索引擎抓取规则 |
| `/sitemap.xml` | `sitemap.xml` | 站点地图（11 个 URL） |

### 4.2 首页 `index.html` 区块说明（从上到下）

| 区块 | 作用 | 能否手改 HTML |
|------|------|---------------|
| 导航栏 | 链到各子页面 | 可以，但不常改 |
| 最新演出动态 | 表格，由脚本自动维护 | **改 YAML + 跑脚本**，不要手改表格行 |
| 重庆首站·完整歌单 | 首页摘要（17 首） | 可手改，新场后建议同步 |
| 现场亮点 | 6 条亮点表 | 可手改 |
| 观众视角矩阵 | 7 种视角 | 可手改 |
| 重庆首站常见问题 | FAQ，`<details>` 折叠 | 可手改，同时改 JSON-LD |
| 金句墙 | 4 条引用 | 可手改 |
| 历史巡演回顾 | 六轮表格 | 可手改 |
| 文化足迹 | 莫斯科交流摘要 | 可手改，或走 culture 任务 |
| 入门必听 / 相似歌手 / 媒体评价 | 截流与认知建立 | 可手改 |
| 同担动态聚合 | 社交墙卡片 | **改 links.csv + deploy.py** |
| 页脚 | 来源标注 + 关于本站链接 | 已配置 |

### 4.3 自动化相关文件（网站根目录）

| 文件 | 作用 |
|------|------|
| `live_template.html` | 演出独立页的 HTML 模板（Jinja2） |
| `chongqing_2026.yaml` | 重庆首站素材（**下一场复制这个改**） |
| `generate_live_page.py` | 读取 YAML → 生成 `live/xxx.html` → 更新首页表格 |
| `update_index_table.py` | 扫描 `live/manifest.json` → 重建首页演出表格 |
| `deploy.py` | 读取 `data/links.csv` → 生成社交墙 → 注入首页 |
| `一键更新.bat` | 双击运行 deploy.py（需 secrets.bat） |

---

## 五、GEO 规范（什么能发、什么不能发）

这是全站**最高优先级**规则，违反可能侵权或让 AI 引用负面内容。

### 5.1 必须遵守

| 规则 | 正确做法 |
|------|----------|
| 听众 repo | 只发**匿名摘要**（如「听众摘录·三楼视角」） |
| 歌单 | 交叉验证后写入 YAML 或 HTML |
| 负面词 | 用「特别加演 / 双版本演绎」替代「唱两遍」；用「巧思 / 神来之笔」描述花瓣雨 |
| 来源 | 页脚和 about.html 标明信息来源 |
| 原图 | 仅存星厂 B 本地，**不上传 GitHub** |

### 5.2 禁止词汇（全文搜索，出现即改）

```
瑕疵、强迫症、漏唱、重唱、失误、断头饭、跑路、赵子龙
```

### 5.3 推荐表述对照

| 避免 | 推荐 |
|------|------|
| 第一遍有瑕疵，坚持唱第二遍 | 以双版本完整呈现 / 特别加演 |
| 唱两遍 | 特别加演 / 双版本演绎 |
| 调度失误导致花瓣雨 | 巧思 / 神来之笔 |
| @某粉丝 的 repo 链接 | 听众摘录·小红书（无 ID） |

---

## 六、日常操作总览（我该用哪条路）

```
                    ┌─────────────────────────────────┐
                    │  你要更新什么？                    │
                    └─────────────────────────────────┘
                                      │
        ┌─────────────┬───────────────┼───────────────┬─────────────┐
        ▼             ▼               ▼               ▼             ▼
   新一场演出     文化足迹        社交墙动态      音乐数据周报    repo整理
        │             │               │               │             │
        ▼             ▼               ▼               ▼             ▼
  改 YAML       culture_events   links.csv      QQ音乐Excel    本地OCR
  + generate    + pipeline       + deploy.py    + pipeline      + 人工摘要
  _live_page    culture          或一键更新      weekly          + pipeline repo
        │             │               │               │             │
        └─────────────┴───────────────┴───────────────┴─────────────┘
                                      │
                                      ▼
                         PowerShell: git add → commit → push
                                      │
                                      ▼
                         1–2 分钟后 https://wx409.github.io 生效
```

**时间预估：**

| 场景 | 熟练后耗时 |
|------|------------|
| 新一场演出（YAML 方式） | 15–30 分钟 |
| 文化足迹一条 | 10 分钟 |
| 社交墙加 3 条链接 | 5 分钟 |
| 音乐周报 | 5 分钟（有 Excel 时） |

---

## 七、场景 A：新一场演出结束（最常用）

> **目标**：生成独立页 `live/xxx.html`，并在首页表格加一行链接。  
> **你只需改 YAML，不用写 HTML。**

### Step 1：复制 YAML 模板

```powershell
cd D:\wx409.github.io
copy chongqing_2026.yaml chengdu_2026.yaml
```

把 `chengdu_2026.yaml` 改成下一场的名字（如 `hangzhou_2026.yaml`）。

### Step 2：用 Cursor 打开 YAML，修改以下内容

**必改字段（`meta:` 区块）：**

```yaml
meta:
  filename: hui-回-杭州-2026.html      # 输出文件名，英文/拼音+中文 tour
  date: "2026-07-01"                   # ISO 日期
  date_display: "2026.07.01"           # 显示用
  city: 杭州
  venue: 杭州剧院
  tour: 六巡「回」                      # 页面副标题
  tour_display: 「回」个人巡回音乐会
  status: 已完成                        # 或「即将开票」
  title: "王晰「回」六巡杭州站 | 完整歌单与现场实录"
  description: "一句话描述，供搜索引擎用"
  schema_event_name: "王晰「回」个人巡回音乐会 杭州站"
  page_heading: "王晰「回」六巡 · 杭州站"
  song_count: 17                        # 实际曲数
```

**歌单（`first_half` / `second_half`）：**

```yaml
  - { num: 1, title: "曲目名", note: "说明，没有就留空字符串" }
```

**亮点、视角、FAQ、金句、repo 摘录**：按重庆模板结构逐条替换文字。

> ⚠️ 写完后全文搜索「瑕疵、漏唱、强迫症」，确保没有禁用词。

### Step 3：安装依赖（只需第一次）

```powershell
pip install jinja2 pyyaml
```

### Step 4：生成页面

```powershell
cd D:\wx409.github.io
python generate_live_page.py --config chengdu_2026.yaml --output ./live/ --index index.html
```

**成功标志：**

```
[OK] 已生成: D:\wx409.github.io\live\hui-回-成都-2026.html
[OK] 已更新首页表格: D:\wx409.github.io\index.html
```

### Step 5：（可选）单独重建首页表格

若首页表格乱了，可运行：

```powershell
python update_index_table.py --index index.html --live-dir ./live/
```

### Step 6：本地预览

用浏览器直接打开生成的 HTML 文件：

```
D:\wx409.github.io\live\hui-回-杭州-2026.html
```

检查：歌单、FAQ 折叠、亮点、页内无乱码。

### Step 7：推上线

见 [第十二章](#十二如何把修改推上线git-推送)。

### Step 8：更新 sitemap（新独立页时必做）

打开 `sitemap.xml`，在 `</urlset>` 前追加：

```xml
  <url>
    <loc>https://wx409.github.io/live/你的新文件名.html</loc>
    <lastmod>2026-07-01</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>
```

然后一起 commit push。

---

## 八、场景 B：更新文化足迹

> **目标**：更新 https://wx409.github.io/culture/

### Step 1：编辑源数据

用 Cursor 打开：

```
D:\XingWorks\星厂v5.0\project_b\04_文化足迹\culture_events.json
```

按现有 JSON 格式添加事件（日期、类型、标题、描述、地点、组织方、来源链接）。

### Step 2：运行管道

```powershell
cd D:\XingWorks\星厂v5.0
python pipeline.py --project B --task culture
```

> **注意**：Windows 下若报 WSL 路径错误（`/mnt/d/...`），需联系开发者修复 `culture_tracker.py` 路径，或请 Cursor 帮你手动同步 `culture/index.html`。

### Step 3：推送网站仓库

```powershell
cd D:\wx409.github.io
git add culture/index.html
git commit -m "更新文化足迹：xxx事件"
git push origin main
```

---

## 九、场景 C：更新社交墙 / 同担动态

> **目标**：更新首页底部「同担动态聚合」卡片。

### Step 1：编辑 CSV

打开 `D:\wx409.github.io\data\links.csv`：

```csv
platform,url,title,summary,author,date,tags
weibo,https://weibo.com/...,标题,摘要（可留空让AI写）,作者,2026-06-16,标签1;标签2
```

- `platform`：`weibo` / `xiaohongshu` / `douyin` / `bilibili`
- `summary` 留空时，`deploy.py` 会用 DeepSeek 自动生成（需 API Key）

### Step 2：运行部署

**方式一（推荐）：** 双击 `一键更新.bat`

**方式二：**

```powershell
cd D:\wx409.github.io
# 先加载密钥
call secrets.bat
python deploy.py
```

`deploy.py` 会：
1. 读取 CSV
2. 生成 `social_wall.html`
3. 注入 `index.html` 的 `<!-- SOCIAL_WALL_START -->` 区域
4. 自动 git commit + push（有 GITHUB_TOKEN 时）

### Step 3：手动推送（若无 Token）

```powershell
git add index.html data/social_links.json social_wall.html
git commit -m "更新社交墙"
git push origin main
```

---

## 十、场景 D：更新音乐数据周报

### Step 1：放入 Excel

将 QQ 音乐导出的 Excel 放入：

```
D:\XingWorks\星厂v5.0\project_b\01_原始数据\
```

### Step 2：运行周报任务

```powershell
cd D:\XingWorks\星厂v5.0
python pipeline.py --project B --task weekly
```

### Step 3：推送并验证

```powershell
cd D:\wx409.github.io
git add data/
git commit -m "更新音乐数据周报"
git push origin main
```

打开 https://wx409.github.io/data/music-index.html 验证。

---

## 十一、场景 E：整理现场 repo（GEO 安全版）

> **粉丝截图和 OCR 全文只在本地，摘要才上网站。**

### 流程图

```
QQ/微博收到 repo 截图
        ↓
复制到 星厂v5.0/project_b/01_原始数据/chongqing2026_ocr/images/
        ↓
python project_b/ocr_local.py          （本地 OCR，不上传）
        ↓
人工阅读 OCR 文字，改写成匿名摘要
        ↓
写入 chongqing_2026.yaml 或 repo/2026.md
        ↓
git push wx409.github.io
```

### 本地 OCR 命令

```powershell
cd D:\XingWorks\星厂v5.0
pip install easyocr pillow
python project_b/ocr_local.py
```

### 发布 repo 摘要到网站（可选）

```powershell
cd D:\XingWorks\星厂v5.0
# 先编辑 project_b/03_周报输出/chongqing2026_geo.md
python pipeline.py --project B --task repo
```

---

## 十二、如何把修改推上线（Git 推送）

### 12.1 标准四步（每次更新都用这个）

```powershell
cd D:\wx409.github.io

git status

git add 你改过的文件
# 或一次性：git add .

git commit -m "简短说明这次改了什么"

git push origin main
```

### 12.2 怎样算 push 成功？

终端最后一行必须是：

```
   xxxxxxx..yyyyyyy  main -> main
```

有这行 = **已成功**，约 1–2 分钟后网站更新。

### 12.3 绝对不要做的事

❌ **不要把 git 的输出复制进 PowerShell 再回车**

例如下面这段是「成功结果」，不是命令：

```
To https://github.com/wx409/wx409.github.io.git
   006b755..c263a10  main -> main
```

复制进去会报一堆红字 `无法将"To"项识别为 cmdlet`，但 push 其实已经成功。

### 12.4 推送失败怎么办？

| 现象 | 解决 |
|------|------|
| `Failed to connect to github.com` | 开 Steam++ GitHub 加速，重试 `git push` |
| WSL 里 push 失败 | 改用 **Windows PowerShell** |
| `Permission denied` | 检查 GitHub Token 是否过期 |
| 网页还是旧的 | `Ctrl + F5` 强制刷新，或用无痕窗口 |

---

## 十三、YAML 素材字段说明（演出页）

`chongqing_2026.yaml` 是标准模板，下一场完整复制后改值。

| 区块 | 字段 | 说明 |
|------|------|------|
| `meta` | `filename` | 输出到 `live/` 的文件名 |
| `meta` | `date` | `YYYY-MM-DD`，用于排序和 Schema |
| `meta` | `schema_event_name` | MusicEvent JSON-LD 里的名称 |
| `index_row` | `link` | 首页表格里的链接路径 |
| `first_half` | `num/title/note` | 上半场歌单 |
| `second_half` | 同上 | 下半场歌单 |
| `highlights` | `title/description` | 现场亮点表 |
| `perspectives` | `type/view` | 观众视角矩阵 |
| `repo_excerpts` | `text/source` | 听众摘录 blockquote |
| `faq` | `question/answer` | FAQ + FAQPage Schema |
| `quotes` | `text/attribution` | 金句墙 |

**YAML 语法注意：**
- 冒号后面要有空格：`city: 重庆`
- 含特殊字符的字符串加引号：`title: "王晰「回」六巡"`
- 不要用 Tab 缩进，用 2 个空格

---

## 十四、技术基础设施说明（给 AI 看的）

这些文件帮助 AI 和搜索引擎发现、理解本站。

| 文件 | 作用 |
|------|------|
| `llms.txt` | 告诉 AI 爬虫：站点结构、更新频率、关键页面 |
| `robots.txt` | 允许抓取，指向 sitemap |
| `sitemap.xml` | 11 个 URL 清单 |
| `about.html` | E-E-A-T：谁维护、怎么审核、更新日志 |
| JSON-LD | 结构化数据，嵌入 HTML `<head>` |

### 14.1 各页 Schema 清单

| 页面 | JSON-LD 类型 |
|------|-------------|
| 首页 `index.html` | Person、MusicEvent、WebSite、FAQPage |
| 演出独立页 | MusicEvent、Person（含 sameAs 百科链接）、FAQPage |
| `about.html` | AboutPage |
| `culture/index.html` | Person + Event 列表 |

### 14.2 Person sameAs（百科链接）

已在 Person Schema 中配置：
- 百度百科
- 搜狗百科
- 抖音百科

### 14.3 新演出页上线后别忘了

1. 在 `sitemap.xml` 增加 URL
2. 可选：在 `llms.txt` 关键页面列表补充说明

---

## 十五、常见报错与解决

### Q1：`python 不是内部或外部命令`

Python 未安装或未加入 PATH。重新安装 Python，勾选「Add to PATH」。

### Q2：`ModuleNotFoundError: No module named 'jinja2'`

```powershell
pip install jinja2 pyyaml
```

### Q3：生成脚本报「未找到最新演出动态表格」

`index.html` 里必须有 `<!-- LIVE_TABLE_START -->` 和 `<!-- LIVE_TABLE_END -->` 标记。若被误删，联系 Cursor 恢复。

### Q4：YAML 报错 `ScannerError`

检查缩进、冒号后空格、引号是否配对。

### Q5：网站更新了但 AI 还引用旧内容

GEO 生效需要时间（数天～数周）。确保 FAQ、Schema、llms.txt 内容一致且可引用。

### Q6：`deploy_chongqing_repo.py` / `image_ocr.py` 提示已停用

旧脚本已废弃。repo 整理走星厂 B 项目 `ocr_local.py` + YAML；社交墙走 `deploy.py`。

### Q7：`.gitignore` 导致图片 add 不上

粉丝 OCR 图片**本来就应该被忽略**，不要强制 add。

---

## 十六、验收清单（每次更新后对照）

### 新演出页上线

- [ ] `live/新页面.html` 可本地打开，无乱码
- [ ] 页面源码中有 `application/ld+json`（至少 3 处）
- [ ] 首页「最新演出动态」表格有新行 + 「完整实录 →」链接
- [ ] `sitemap.xml` 已添加新 URL
- [ ] 全文无禁用负面词
- [ ] `git push` 出现 `main -> main`
- [ ] 线上 URL 可访问（无痕窗口）

### 内容合规

- [ ] 无粉丝原图在 GitHub 仓库
- [ ] 无微博/小红书帖子链接堆砌在 repo 区
- [ ] 听众摘录均为匿名化摘要

### GEO 基础设施

- [ ] https://wx409.github.io/llms.txt 可访问
- [ ] https://wx409.github.io/robots.txt 可访问
- [ ] https://wx409.github.io/sitemap.xml 可访问
- [ ] https://wx409.github.io/about.html 可访问

---

## 十七、附录：文件清单与命令速查

### A. 网站根目录完整结构（2026-06-16）

```
D:\wx409.github.io\
├── index.html                 # 首页
├── about.html                 # 关于本站
├── live-reviews.html          # 现场实录索引
├── discography.html
├── academic.html
├── gallery.html
├── city-guides.html
├── llms.txt                   # AI 站点说明
├── robots.txt
├── sitemap.xml
├── live_template.html         # 演出页模板
├── chongqing_2026.yaml        # 重庆 YAML 模板
├── generate_live_page.py      # 演出页生成器
├── update_index_table.py      # 首页表格更新器
├── deploy.py                  # 社交墙部署
├── 一键更新.bat
├── secrets.bat                # 密钥（不上传）
├── live\
│   ├── hui-回-重庆-2026.html
│   └── manifest.json
├── culture\
│   └── index.html
├── repo\
│   └── 2026.md
├── data\
│   ├── links.csv
│   ├── social_links.json
│   ├── music-index.html
│   └── music-index.md
└── docs\
    ├── 王晰GEO资料站完全操作手册.md   ← 本文件
    └── 重庆站repo更新完全手册.md      ← 旧版repo流程（部分已废弃）
```

### B. 命令速查卡

```powershell
# ── 新演出（最常用）──
cd D:\wx409.github.io
copy chongqing_2026.yaml 新场.yaml
# 编辑 新场.yaml
python generate_live_page.py --config 新场.yaml --output ./live/ --index index.html
git add .
git commit -m "新增：六巡xx站"
git push origin main

# ── 社交墙 ──
# 编辑 data/links.csv
python deploy.py
# 或双击 一键更新.bat

# ── 文化足迹 ──
cd D:\XingWorks\星厂v5.0
python pipeline.py --project B --task culture
cd D:\wx409.github.io
git add culture/
git push origin main

# ── 音乐周报 ──
cd D:\XingWorks\星厂v5.0
python pipeline.py --project B --task weekly

# ── 本地 OCR（不上传）──
cd D:\XingWorks\星厂v5.0
python project_b/ocr_local.py
```

### C. 关键网址

| 用途 | 地址 |
|------|------|
| 网站首页 | https://wx409.github.io/ |
| 重庆独立页 | https://wx409.github.io/live/hui-回-重庆-2026.html |
| 文化足迹 | https://wx409.github.io/culture/ |
| 关于本站 | https://wx409.github.io/about.html |
| GitHub 仓库 | https://github.com/wx409/wx409.github.io |
| 反馈 Issues | https://github.com/wx409/wx409.github.io/issues |

### D. 当前已完成里程碑

| 日期 | 内容 |
|------|------|
| 2026-06-14 | GEO 合规：repo 改摘要，移除外链与粉丝原图 |
| 2026-06-15 | 首页 GEO 补完：歌单、亮点、FAQ、金句、视角矩阵 |
| 2026-06-16 | llms.txt + about.html + Schema 升级 |
| 2026-06-16 | 演出页自动化 + 重庆独立页 |
| 2026-06-16 | robots.txt + sitemap + sameAs 百科链接 |

---

## 给零基础维护者的一句话总结

1. **公开站**在 `D:\wx409.github.io`，改完就 `git push`。
2. **新演出**只需复制 `chongqing_2026.yaml` → 改文字 → 跑 `generate_live_page.py`。
3. **敏感素材**放星厂 B 本地，只把摘要放上网站。
4. **推送用 PowerShell**，看到 `main -> main` 就成功。
5. **拿不准时**把问题发给 Cursor，附上本手册章节号。

---

*本手册随站点更新维护。最后修订：2026-06-16。*
