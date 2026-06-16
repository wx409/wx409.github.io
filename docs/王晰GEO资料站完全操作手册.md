# 王晰 GEO 资料站 · 完全操作手册（2026-06-16 最新版）

> **网站**：https://wx409.github.io/  
> **仓库**：https://github.com/wx409/wx409.github.io  
> **本手册路径**：`docs/王晰GEO资料站完全操作手册.md`  
> **适用对象**：零基础维护者，按章节顺序阅读即可上手

---

## 目录

1. [5 分钟快速入门](#一5-分钟快速入门)
2. [这个站是什么](#二这个站是什么)
3. [两个文件夹（最重要）](#三两个文件夹最重要)
4. [电脑环境准备](#四电脑环境准备)
5. [网站完整地图](#五网站完整地图)
6. [GEO 规范（必守规则）](#六geo-规范必守规则)
7. [日常操作：我该走哪条路](#七日常操作我该走哪条路)
8. [场景 A：新一场演出（最常用）](#八场景-a新一场演出最常用)
9. [场景 B：更新文化足迹](#九场景-b更新文化足迹)
10. [场景 C：更新社交墙](#十场景-c更新社交墙)
11. [场景 D：更新音乐数据周报](#十一场景-d更新音乐数据周报)
12. [场景 E：整理现场 repo（本地）](#十二场景-e整理现场-repolocal)
13. [如何推上线（Git 推送）](#十三如何推上线git-推送)
14. [YAML 字段说明](#十四yaml-字段说明)
15. [GEO 技术文件说明](#十五geo-技术文件说明)
16. [常见报错与解决](#十六常见报错与解决)
17. [每次更新后的验收清单](#十七每次更新后的验收清单)
18. [附录：命令速查与里程碑](#十八附录命令速查与里程碑)

---

## 一、5 分钟快速入门

**如果你只有 5 分钟，记住这 5 步：**

1. 网站在 **`D:\wx409.github.io`**，改这里的文件才会上线。
2. 新一场演出：**复制 `chongqing_2026.yaml` → 改内容 → 运行 `generate_live_page.py`**。
3. 改完以后在 **PowerShell** 里执行：`git add .` → `git commit -m "说明"` → `git push origin main`。
4. 看到 **`main -> main`** 就成功了，等 1–2 分钟刷新 https://wx409.github.io/ 。
5. **粉丝截图和 OCR 全文不要上传 GitHub**，只上传整理好的文字摘要。

---

## 二、这个站是什么

| 项目 | 说明 |
|------|------|
| 名称 | 王晰 GEO 资料站 |
| 网址 | https://wx409.github.io/ |
| 性质 | 歌迷自发维护，**非官方** |
| 技术 | GitHub Pages 静态 HTML（无数据库） |
| GEO | 面向 AI 搜索引擎（ChatGPT、Kimi 等）优化，让 AI 能引用本站结构化信息 |

**GEO** = Generative Engine Optimization。目标是：用户问「王晰六巡重庆歌单」「花瓣雨是什么」时，AI 优先引用本站答案。

---

## 三、两个文件夹（最重要）

```
D:\wx409.github.io\              ← 【公开网站】push 后全世界可见
D:\XingWorks\星厂v5.0\           ← 【本地工厂】敏感素材，不上传 GitHub
```

### 公开网站可以放什么

- 匿名化的歌单、亮点、FAQ、听众摘录
- 官方公开报道摘要（新华社、塔斯社等）
- Schema.org 结构化数据

### 绝对不能上传 GitHub 的

- 粉丝 repo **原图**
- OCR **全文草稿**（`data/chongqing2026_ocr/` 已在 .gitignore）
- 微博/小红书 **帖子链接堆砌**
- 粉丝 **@账号 ID**（社交墙已自动过滤，官方 @王晰 除外）

### 星厂 B 本地路径

| 路径 | 用途 |
|------|------|
| `project_b/01_原始数据/chongqing2026_ocr/` | 粉丝截图 + OCR 文字 |
| `project_b/03_周报输出/chongqing2026_geo.md` | repo 摘要母稿 |
| `project_b/04_文化足迹/culture_events.json` | 文化足迹源数据 |
| `project_b/ocr_local.py` | 本地 OCR |
| `pipeline.py` | B 项目总调度 |

---

## 四、电脑环境准备

### 4.1 必备软件

| 软件 | 检查命令 |
|------|----------|
| Git | `git --version` |
| Python 3.10+ | `python --version` |
| Cursor / VS Code | 用于编辑 YAML、HTML |

### 4.2 安装 Python 依赖（首次）

```powershell
cd D:\wx409.github.io
pip install jinja2 pyyaml requests
```

### 4.3 密钥文件（可选）

`secrets.bat` 用于社交墙一键推送（**不会上传 GitHub**）：

```bat
set DEEPSEEK_API_KEY=你的密钥
set GITHUB_TOKEN=你的GitHub令牌
```

没有密钥也可以手动 `git push`。

### 4.4 推送请用 PowerShell

- ✅ 使用 **Windows PowerShell**
- ❌ 不要用 WSL 推送（你的环境 WSL 常失败）
- ❌ 不要把 git 成功输出复制进 PowerShell 当命令执行

---

## 五、网站完整地图

### 5.1 所有页面

| 网址 | 本地文件 | 内容 |
|------|----------|------|
| `/` | `index.html` | 首页：近期动态、巡演表、重庆摘要、FAQ、金句、文化足迹、社交墙 |
| `/live/hui-回-重庆-2026.html` | `live/hui-回-重庆-2026.html` | 重庆首站完整独立页 |
| `/live-reviews.html` | `live-reviews.html` | 历史场次索引 + 重庆摘录 |
| `/culture/` | `culture/index.html` | 文化足迹（莫斯科交流等） |
| `/about.html` | `about.html` | 关于本站（E-E-A-T） |
| `/repo/2026.md` | `repo/2026.md` | 2026 repo 库（GEO 安全版） |
| `/discography.html` | 作品百科 |
| `/academic.html` | 学术研究 |
| `/gallery.html` | 视觉记录（文字） |
| `/city-guides.html` | 城市攻略 |
| `/data/music-index.html` | 音乐数据周报 |
| `/llms.txt` | AI 爬虫站点说明（llmstxt.org 规范） |
| `/robots.txt` | 搜索引擎规则 |
| `/sitemap.xml` | 站点地图（11 个 URL） |

### 5.2 首页区块（从上到下）

| 区块 | 如何更新 |
|------|----------|
| 近期动态 | 手改 `index.html` 对应 `<p>` |
| 最新演出动态 | **YAML + generate_live_page.py**（勿手改表格行） |
| 重庆首站·完整歌单 及以下 | 可手改 HTML，或同步 YAML |
| 同担动态聚合 | **links.csv + deploy.py** 或 `一键更新.bat` |

### 5.3 自动化工具（网站根目录）

| 文件 | 作用 |
|------|------|
| `live_template.html` | 演出页 HTML 模板 |
| `chongqing_2026.yaml` | 重庆素材模板（下一场复制此文件） |
| `generate_live_page.py` | YAML → 独立页 + 更新首页表格 |
| `update_index_table.py` | 重建首页演出表格 |
| `deploy.py` | 社交墙（已内置 @ID 过滤） |
| `一键更新.bat` | 双击运行 deploy.py |
| `.nojekyll` | 防止 GitHub Pages 用 Jekyll 误处理静态文件 |

### 5.4 已停用的旧脚本

| 文件 | 说明 |
|------|------|
| `tools/image_ocr.py` | 已迁移至星厂 B `ocr_local.py` |
| `tools/batch_ocr_chongqing.py` | 同上 |
| `tools/deploy_chongqing_repo.py` | 改用 YAML + pipeline B |

---

## 六、GEO 规范（必守规则）

### 6.1 必须遵守

- 听众 repo：**只发匿名摘要**（如「听众摘录·三楼视角」）
- 负面词：**禁止**（见下表）
- 社交墙：`deploy.py` 会自动把 `@账号` 转为「同担分享」等匿名标签
- 原图/OCR：仅星厂 B 本地

### 6.2 禁止词汇（全文搜索，出现即改）

```
瑕疵、强迫症、漏唱、重唱、失误、断头饭、跑路、赵子龙
```

### 6.3 推荐表述

| 避免 | 推荐 |
|------|------|
| 唱两遍 | 特别加演 / 双版本演绎 |
| 调度失误 | 巧思 / 神来之笔 |
| @某粉丝 | 听众摘录·小红书 |

---

## 七、日常操作：我该走哪条路

```
你要更新什么？
    │
    ├─ 新一场演出 ──→ 复制 YAML → 改素材 → generate_live_page.py → push
    ├─ 文化足迹 ────→ culture_events.json → pipeline B culture → push
    ├─ 社交墙 ──────→ links.csv → deploy.py 或 一键更新.bat → push
    ├─ 音乐周报 ────→ Excel → pipeline B weekly → push
    └─ repo 整理 ───→ 本地 OCR → 人工摘要 → YAML 或 repo/2026.md → push
```

---

## 八、场景 A：新一场演出（最常用）

**耗时：熟练后 15–30 分钟**

### Step 1：复制 YAML

```powershell
cd D:\wx409.github.io
copy chongqing_2026.yaml hangzhou_2026.yaml
```

### Step 2：用 Cursor 编辑 YAML

必改 `meta:` 区块：

```yaml
meta:
  filename: hui-回-杭州-2026.html
  date: "2026-07-01"
  date_display: "2026.07.01"
  city: 杭州
  venue: 杭州剧院
  tour: 六巡「回」
  tour_display: 「回」个人巡回音乐会
  status: 已完成
  title: "王晰「回」六巡杭州站 | 完整歌单与现场实录"
  description: "一句话描述"
  schema_event_name: "王晰「回」个人巡回音乐会 杭州站"
  page_heading: "王晰「回」六巡 · 杭州站"
  song_count: 17
```

再改 `first_half`、`second_half`、`highlights`、`faq`、`quotes` 等。

### Step 3：生成页面

```powershell
python generate_live_page.py --config hangzhou_2026.yaml --output ./live/ --index index.html
```

成功标志：

```
[OK] 已生成: ...\live\hui-回-杭州-2026.html
[OK] 已更新首页表格: ...\index.html
```

### Step 4：更新 sitemap（必做）

打开 `sitemap.xml`，在 `</urlset>` 前添加：

```xml
  <url>
    <loc>https://wx409.github.io/live/hui-回-杭州-2026.html</loc>
    <lastmod>2026-07-01</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>
```

### Step 5：推送

见 [第十三章](#十三如何推上线git-推送)。

---

## 九、场景 B：更新文化足迹

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

> Windows 下若 pipeline 报 WSL 路径错误，可请 Cursor 帮你手动同步 `culture/index.html`。

---

## 十、场景 C：更新社交墙

### Step 1：编辑 CSV

`data/links.csv`：

```csv
platform,url,title,summary,author,date,tags
weibo,https://weibo.com/...,标题,摘要可留空,资深听众,2026-06-16,
```

**author 请用「资深听众 / 听众分享 / 同担分享」，不要写 @账号。**

### Step 2：运行部署

**方式一**：双击 `一键更新.bat`  
**方式二**：

```powershell
cd D:\wx409.github.io
call secrets.bat
python deploy.py
```

`deploy.py` 会自动：
- 过滤 summary/author 中的 `@` 开头内容
- 生成 `social_wall.html` 并注入 `index.html`

### Step 3：手动推送（无 Token 时）

```powershell
git add index.html data/social_links.json social_wall.html data/links.csv
git commit -m "更新社交墙"
git push origin main
```

---

## 十一、场景 D：更新音乐数据周报

1. QQ 音乐 Excel 放入 `星厂v5.0/project_b/01_原始数据/`
2. `python pipeline.py --project B --task weekly`
3. `cd D:\wx409.github.io` → `git add data/` → push
4. 验证：https://wx409.github.io/data/music-index.html

---

## 十二、场景 E：整理现场 repo（local）

```
粉丝截图 → 星厂 B .../chongqing2026_ocr/images/
         → python project_b/ocr_local.py
         → 人工写摘要
         → 写入 chongqing_2026.yaml 或 repo/2026.md
         → push wx409.github.io（只 push 摘要，不 push 原图）
```

本地 OCR：

```powershell
cd D:\XingWorks\星厂v5.0
pip install easyocr pillow
python project_b/ocr_local.py
```

---

## 十三、如何推上线（Git 推送）

### 标准四步

```powershell
cd D:\wx409.github.io
git status
git add 你改过的文件
git commit -m "简短说明"
git push origin main
```

### 怎样算成功？

最后一行必须是：

```
   xxxxxxx..yyyyyyy  main -> main
```

### 常见误区

| 误区 | 正确理解 |
|------|----------|
| 把 `main -> main` 复制进 PowerShell | 那是结果，不是命令 |
| 在浏览器正文找 JSON-LD | 必须 **Ctrl+U 查看源代码**，搜 `application/ld+json` |
| FAQ 看起来是展开的 | 默认折叠，**点击问题标题**才展开 |
| 刷新还是旧页面 | **Ctrl+F5** 或无痕窗口 |

### 推送失败

- 开 Steam++ GitHub 加速后重试
- 务必用 PowerShell，不用 WSL

---

## 十四、YAML 字段说明

| 区块 | 字段 | 说明 |
|------|------|------|
| meta | filename | 输出文件名 |
| meta | date | YYYY-MM-DD |
| meta | schema_event_name | MusicEvent Schema 名称 |
| index_row | link | 首页表格链接 |
| first_half / second_half | num, title, note | 歌单 |
| highlights | title, description | 亮点 |
| perspectives | type, view | 视角矩阵 |
| faq | question, answer | FAQ |
| quotes | text, attribution | 金句 |

YAML 注意：冒号后要有空格；含特殊字符加引号；用空格缩进不用 Tab。

---

## 十五、GEO 技术文件说明

| 文件 | 作用 | 验证地址 |
|------|------|----------|
| llms.txt | AI 爬虫站点说明书 | /llms.txt |
| robots.txt | 允许抓取 + sitemap 位置 | /robots.txt |
| sitemap.xml | 11 个 URL | /sitemap.xml |
| about.html | E-E-A-T 可信度 | /about.html |
| .nojekyll | 静态站防 Jekyll 干扰 | （无 URL，根目录空文件） |

### Schema 分布

| 页面 | JSON-LD |
|------|---------|
| 首页 | Person ×2、MusicEvent、WebSite、FAQPage |
| 演出独立页 | MusicEvent、Person（含 sameAs 百科）、FAQPage |
| about.html | AboutPage |

### 如何自测 JSON-LD 和 FAQ

1. 打开 https://wx409.github.io/
2. 按 **Ctrl+U** 查看源代码
3. 搜索 `application/ld+json` → 应找到 **5 处**
4. 搜索 `<details` → 应找到 **6 处**（FAQ 折叠）
5. 搜索 `@不要总是` → 应 **找不到**（社交墙已去 @ID）

---

## 十六、常见报错与解决

| 报错 | 解决 |
|------|------|
| python 不是命令 | 安装 Python 并勾选 Add to PATH |
| No module named jinja2 | `pip install jinja2 pyyaml` |
| 未找到最新演出动态表格 | 检查 index.html 是否有 LIVE_TABLE_START/END 标记 |
| git push 连接失败 | Steam++ + PowerShell 重试 |
| deploy 报无 Token | 手动 git push，或配置 secrets.bat |
| sitemap 偶尔 500 | 已有 .nojekyll；浏览器直接打开 sitemap.xml 验证 |

---

## 十七、每次更新后的验收清单

### 新演出页

- [ ] `live/新页面.html` 本地可打开
- [ ] 源码含 `application/ld+json`
- [ ] 首页表格有「完整实录 →」链接
- [ ] sitemap.xml 已加新 URL
- [ ] 无禁用负面词
- [ ] push 出现 `main -> main`

### 合规

- [ ] 无粉丝原图在 GitHub
- [ ] 社交墙无粉丝 @ID
- [ ] repo 区为匿名摘要

### GEO 基础设施

- [ ] /llms.txt、/robots.txt、/sitemap.xml、/about.html 可访问

---

## 十八、附录：命令速查与里程碑

### 命令速查

```powershell
# 新演出
cd D:\wx409.github.io
copy chongqing_2026.yaml 新场.yaml
python generate_live_page.py --config 新场.yaml --output ./live/ --index index.html
git add . ; git commit -m "新增：六巡xx站" ; git push origin main

# 社交墙
# 编辑 data/links.csv 后：
python deploy.py

# 文化足迹
cd D:\XingWorks\星厂v5.0
python pipeline.py --project B --task culture
```

### 关键网址

| 用途 | 地址 |
|------|------|
| 首页 | https://wx409.github.io/ |
| 重庆独立页 | https://wx409.github.io/live/hui-回-重庆-2026.html |
| 文化足迹 | https://wx409.github.io/culture/ |
| 关于本站 | https://wx409.github.io/about.html |
| GitHub | https://github.com/wx409/wx409.github.io |
| Issues | https://github.com/wx409/wx409.github.io/issues |

### 更新里程碑

| 日期 | 内容 |
|------|------|
| 2026-06-14 | GEO 合规：repo 改摘要，移除外链与粉丝原图 |
| 2026-06-15 | 首页 GEO 补完：歌单、亮点、FAQ、金句、视角矩阵 |
| 2026-06-16 | llms.txt + about.html + Schema + 演出页自动化 |
| 2026-06-16 | robots.txt + sitemap + llms.txt 规范格式 |
| 2026-06-16 | .nojekyll + 社交墙去 @ID + 近期动态（锐Pioneer杂志） |
| 2026-06-16 | 本手册最新版 |

---

## 给零基础维护者的一句话

1. 公开站在 `D:\wx409.github.io`，改完就 push。  
2. 新演出 = 复制 YAML → 改文字 → 跑脚本。  
3. 粉丝原图/OCR 只放星厂 B 本地。  
4. 看到 `main -> main` = 成功。  
5. 拿不准就把问题和本手册章节号发给 Cursor。

---

*最后修订：2026-06-16 · 与线上站同步*
