# 王晰 GEO 资料站 · 完全操作手册（2026-06-17 最新版）

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
8. [**如何更新已有信息（总表）**](#八如何更新已有信息总表)
9. [**线上线下同步推送（标准流程）**](#九线上线下同步推送标准流程)
10. [场景 A：新一场演出](#十场景-a新一场演出)
11. [场景 A-2：更新已有演出页](#十一场景-a-2更新已有演出页)
12. [场景 B：更新文化足迹](#十二场景-b更新文化足迹)
13. [场景 C：更新社交墙](#十三场景-c更新社交墙)
14. [场景 D：更新音乐数据周报](#十四场景-d更新音乐数据周报)
15. [场景 E：整理现场 repo（本地）](#十五场景-e整理现场-repolocal)
16. [场景 F：更新首页「近期动态」](#十六场景-f更新首页近期动态)
17. [YAML 字段说明](#十七yaml-字段说明)
18. [GEO 技术文件说明](#十八geo-技术文件说明)
19. [常见报错与解决](#十九常见报错与解决)
20. [每次更新后的验收清单](#二十每次更新后的验收清单)
21. [附录：命令速查与里程碑](#二十一附录命令速查与里程碑)

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
| `/about.html` | `about.html` | 手改（更新日志） |
| `/repo/2026.md` | `repo/2026.md` | pipeline B `--task repo` 或手改 |
| `/llms.txt` | `llms.txt` | 手改（结构变更时） |
| `/sitemap.xml` | `sitemap.xml` | 新页面时手加 URL |
| `/data/music-index.html` | `data/music-index.html` | pipeline B `--task weekly` |

### 5.2 自动化工具（网站根目录）

| 文件 | 作用 | 更新类型 |
|------|------|----------|
| `chongqing_2026.yaml` | 重庆素材母版 | 复制后改 = 新场 / 直接改 = 更新重庆 |
| `generate_live_page.py` | YAML → live 页 + 首页表格 | 演出 |
| `update_index_table.py` | 重建首页演出表格 | 演出 |
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
  ├─ 新一场演出 ────────────────→ 复制 YAML → 改 → 脚本 → sitemap → push
  ├─ 文化足迹 ──────────────────→ culture_events.json → pipeline culture → push
  ├─ 社交墙 ────────────────────→ links.csv → deploy.py → push
  ├─ 音乐周报 ──────────────────→ Excel → pipeline weekly → push
  └─ repo 摘要（合规）──────────→ 本地 OCR → geo.md → pipeline repo → push
```

---

## 八、如何更新已有信息（总表）

> **原则：能改 YAML/CSV/JSON 源数据的，就不要直接改 HTML；改源数据后跑脚本，再 push。**

| 要更新的内容 | 改哪个文件（线下） | 运行什么命令 | 是否改 index.html 正文 | push 范围 |
|--------------|-------------------|--------------|------------------------|-----------|
| 近期动态一行 | `index.html` | 无 | 是（仅一行） | index.html |
| 重庆/某场歌单、FAQ、亮点 | `chongqing_2026.yaml` 或 `xxx.yaml` | `generate_live_page.py` | 脚本只改「最新演出动态」表格 | yaml + live/ + index 表格区 |
| 首页演出表格顺序 | 自动 | `update_index_table.py` | 仅表格标记区 | index 表格区 |
| 现场实录摘录 | `live-reviews.html` 或 geo.md | `pipeline B --task repo` | live-reviews 块 | 对应文件 |
| repo 库全文 | `星厂.../chongqing2026_geo.md` | `pipeline B --task repo` | repo/2026.md | repo + live-reviews |
| 文化足迹 | `culture_events.json` | `pipeline B --task culture` | culture/index.html | culture/ |
| 社交墙卡片 | `data/links.csv` | `deploy.py` 或 `一键更新.bat` | 脚本注入 SOCIAL_WALL 区 | index + social_wall + json |
| 音乐数据 | QQ 音乐 Excel | `pipeline B --task weekly` | data/music-index.* | data/ |
| 新 live 页上线 | 新 YAML | generate + **手改 sitemap.xml** | 表格自动 | live/ + sitemap + yaml |
| 关于站/更新日志 | `about.html` | 无 | 是 | about.html |
| llms.txt 结构 | `llms.txt` | 无 | 否 | llms.txt |

### 双份内容说明（重要）

目前**首页**有重庆摘要（歌单/亮点/FAQ），**独立页** `/live/hui-回-重庆-2026.html` 有完整版。

| 内容 | 首页 | 独立页 | 推荐维护方式 |
|------|------|--------|--------------|
| 歌单/FAQ/亮点 | 有（摘要） | 有（完整） | **以 YAML 为准** → 脚本更新独立页；首页大段摘要需手改或日后自动化 |
| 演出表格链接 | 有 | — | 脚本自动 |

**可持续建议：** 场次的歌单/FAQ/亮点/金句 **只改 YAML**，独立页永远正确；首页摘要仅在重大变更时手改一次。

---

## 九、线上线下同步推送（标准流程）

### 9.1 什么是「同步」

| 步骤 | 位置 | 说明 |
|------|------|------|
| 1. 本地编辑 | 线下 `D:\wx409.github.io\` | 你改的文件 |
| 2. git commit | 线下 | 保存版本快照 |
| 3. git push | 线下 → GitHub | 上传到远程仓库 |
| 4. GitHub Pages 构建 | 线上自动 | 约 **1–2 分钟** |
| 5. 浏览器访问 | 线上 https://wx409.github.io/ | 用户看到新内容 |

**没有单独的「上传 FTP」步骤**，push = 上线。

### 9.2 标准推送四步（每次更新必做）

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

### 9.3 半自动推送（社交墙）

配置 `secrets.bat` 后，双击 **`一键更新.bat`** 或运行 `python deploy.py`：

1. 读 `data/links.csv`
2. （可选）DeepSeek 写摘要
3. 生成 `social_wall.html` 并注入 `index.html`
4. **自动** git commit + push（需 `GITHUB_TOKEN`）

无 Token 时：脚本只生成本地文件，你再手动执行 [9.2](#92-标准推送四步每次更新必做)。

### 9.4 星厂 B → 网站 → 线上（两仓库联动）

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

### 9.5 推送后验证（线上）

```powershell
# 可选：看最近一次提交是否已在 GitHub
git log -1 --oneline
```

浏览器检查：

1. 打开目标 URL（如首页）
2. **Ctrl+F5** 强制刷新
3. 或无痕窗口打开
4. 重要改动：**Ctrl+U** 看源码（JSON-LD、details 等）

### 9.6 不要 push 的文件

已在 `.gitignore`：`secrets.bat`、OCR 图片/文字、部分 bat。  
推送前 `git status` 确认没有 `chongqing2026_ocr/images/` 被误 add。

---

## 十、场景 A：新一场演出

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

### Step 4：更新 sitemap.xml

在 `</urlset>` 前添加新 `<url>...</url>`。

### Step 5：推送（见第九章）

```powershell
git add hangzhou_2026.yaml live/ index.html sitemap.xml
git commit -m "新增：六巡杭州站"
git push origin main
```

---

## 十一、场景 A-2：更新已有演出页

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

- `--index index.html` 会更新「最新演出动态」表格那一块（`LIVE_TABLE_START/END` 之间）
- **不会**自动改首页「重庆首站·完整歌单」以下区块——若需与 YAML 一致，需手改 index 或使用 Cursor 对照 YAML 同步

### Step 3：推送

```powershell
git add chongqing_2026.yaml live/hui-回-重庆-2026.html live/manifest.json index.html
git commit -m "更新：重庆首站歌单/FAQ"
git push origin main
```

### 仅重建首页表格（不改 live 页）

```powershell
python update_index_table.py --index index.html --live-dir ./live/
git add index.html
git commit -m "重建首页演出表格"
git push origin main
```

---

## 十二、场景 B：更新文化足迹

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

## 十三、场景 C：更新社交墙

### Step 1：编辑 CSV

`D:\wx409.github.io\data\links.csv`：

```csv
platform,url,title,summary,author,date,tags
weibo,https://weibo.com/...,标题,摘要可留空,资深听众,2026-06-17,
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

## 十四、场景 D：更新音乐数据周报

1. Excel 放入 `星厂v5.0/project_b/01_原始数据/`
2. `python pipeline.py --project B --task weekly`
3. `cd D:\wx409.github.io` → `git add data/` → push
4. 验证：https://wx409.github.io/data/music-index.html

---

## 十五、场景 E：整理现场 repo（本地）

```
粉丝截图 → 星厂 B .../chongqing2026_ocr/images/
         → python project_b/ocr_local.py
         → 人工写摘要 → chongqing2026_geo.md
         → python pipeline.py --project B --task repo
         → cd wx409.github.io → git push
```

**只 push 摘要，不 push 原图/OCR。**

---

## 十六、场景 F：更新首页「近期动态」

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

## 十七、YAML 字段说明

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

## 十八、GEO 技术文件说明

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

## 十九、常见报错与解决

| 报错 | 解决 |
|------|------|
| python 不是命令 | 重装 Python，勾选 Add to PATH |
| No module named jinja2 | `pip install jinja2 pyyaml` |
| git push 失败 | Steam++ + PowerShell 重试 |
| deploy 无 Token | 手动 git push |
| pipeline culture 路径错误 | 手改 culture/index.html 或修复 tracker |
| 线上还是旧的 | Ctrl+F5；确认 `main -> main` |

---

## 二十、每次更新后的验收清单

### 通用

- [ ] `git push` 出现 `main -> main`
- [ ] 线上 URL Ctrl+F5 可见变更
- [ ] 无禁用负面词
- [ ] 无 OCR 原图被 push

### 演出更新

- [ ] YAML 与 live 页内容一致
- [ ] live 页源码含 JSON-LD
- [ ] 新场已加入 sitemap.xml

### 社交墙

- [ ] 无粉丝 @ID
- [ ] author 为「资深听众/听众分享/同担分享」

---

## 二十一、附录：命令速查与里程碑

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
# 编辑 新场.yaml + sitemap.xml
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

# ── 仅重建首页演出表 ──
python update_index_table.py --index index.html --live-dir ./live/
git add index.html ; git push origin main
```

### 关键网址

| 用途 | 地址 |
|------|------|
| 线上首页 | https://wx409.github.io/ |
| 重庆独立页 | https://wx409.github.io/live/hui-回-重庆-2026.html |
| 文化足迹 | https://wx409.github.io/culture/ |
| 手册（GitHub） | https://github.com/wx409/wx409.github.io/blob/main/docs/王晰GEO资料站完全操作手册.md |

### 更新里程碑

| 日期 | 内容 |
|------|------|
| 2026-06-14 | GEO 合规：repo 摘要化，移除粉丝原图 |
| 2026-06-15 | 首页 GEO 补完 |
| 2026-06-16 | llms.txt + about + Schema + 演出自动化 |
| 2026-06-16 | robots + sitemap + llms 规范格式 |
| 2026-06-16 | .nojekyll + 社交墙去 @ID |
| 2026-06-16 | FAQ 折叠 + GEO 基础设施修复 |
| 2026-06-17 | 近期动态精简；《锐Pioneer》杂志 |
| 2026-06-17 | **本手册 v2：新增「更新已有信息」+「线上线下同步推送」** |

---

## 给维护者的一句话

**改 YAML/CSV → 跑脚本 → git push → 等 2 分钟 → Ctrl+F5 看线上。**

敏感素材永远在星厂 B 本地；公开站只 push 摘要。

---

*最后修订：2026-06-17 · 与线上站同步 · GEO 等级 A-（86/100）*
