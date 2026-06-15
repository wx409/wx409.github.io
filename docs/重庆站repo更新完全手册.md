# 重庆站「回」首站 repo 更新完全手册

> **场次**：2026.06.13 · 重庆 · 施光南大剧院 · 六巡「回」首站  
> **网站**：https://wx409.github.io/  
> **适用对象**：零基础，按 Step 1→7 顺序操作即可

---

## 一、整体流程（先看懂再动手）

```
你收集的链接（微博17+小红书5+视频7）
        ↓
data/chongqing2026_repos.csv  （主数据表，含标题/摘要措词）
        ↓
python tools/deploy_chongqing_repo.py   → 更新 live-reviews / repo / city-guides / gallery / links.csv
        ↓
保存图片 → python tools/image_ocr.py    → 歌单 OCR 转文字
        ↓
人工校对 → 补入 repo/2026.md 歌单章节
        ↓
python deploy.py 或 一键更新.bat         → 首页社交墙
        ↓
PowerShell git push                     → 上线 wx409.github.io
```

**本站原则**：不搬运原图/视频/全文，只提供**索引 + 一句摘要 + 原链**。  
**例外说明**：@不要总是哭唧唧 图频全面放开授权 → 仍只索引原链；@王晰工作室 官方图可引用但建议链回原博。

---

## 二、内容分解：每条链接对应哪个板块

| 板块 | 文件 | 放什么 |
|------|------|--------|
| 现场实录索引 | `live-reviews.html` | 全部 28 条，按「官方/视频/文字/图片/视角」分类列表 |
| 详细 repo 库 | `repo/2026.md` | 歌单、谁适合来听、每条摘要与链接 |
| 首页社交墙 | `index.html`（由 deploy.py 注入） | `data/links.csv` 里的标题+25字摘要卡片 |
| 城市攻略 | `city-guides.html` | 重庆站状态、座位反馈、跳转链接 |
| 视觉记录 | `gallery.html` | 工作室官方图 + 授权视频索引 |

---

## 三、28 条链接的标准措词（已写入 CSV，可直接用）

> **title** = 网站卡片标题（15 字内信息量）  
> **summary** = 社交墙/摘要（一句说清价值点）

### 微博文字 repo

| # | 作者 | title | summary |
|---|------|-------|---------|
| 1 | @柯烬 | 六巡重庆首站·池座5区听感记录 | 池座5区观演：聚焦现场整体氛围与听感，未逐首列歌单。 |
| 2 | @不要总是哭唧唧 | 大粉解读六巡「回」主题 | 从「回」字解读六巡立意与现场气质，偏主题感受型 repo。 |
| 3 | @为了防社死改名了 | 路人首听：原来王晰是这样一种风格 | 含歌单信息；引用——第一次来听演唱会的人就会知道，原来王晰是这样一种风格。 |
| 4 | @瑞儿啦啦啦 | 路人粉三首歌速记 | 路人视角记录三首现场曲目与听感，未标注座位。 |
| 5 | @第五炫明 | 偏专业向歌单简记 repo | 以简写歌名记录多首曲目，偏专业听感与编排观察。 |
| 9 | @panda是个小公举 | 池座5区·含歌名的现场 repo | 池座5区，记录含具体歌名的现场反馈。 |

### 微博图片 repo（需 OCR，Step 4）

| # | 作者 | title | 你要做的 |
|---|------|-------|---------|
| 6 | @王晰工作室 | 工作室官方现场图（可引用） | 保存现场图 → OCR 可选；gallery 已索引 |
| 10 | @邬尾 | 逐首详录·每首歌感受（图转文） | 截图保存 → OCR → 校对写入歌单 |
| 11 | @神经二条的pp阿豹 | 三楼视角 repo（图转文） | 同上，注意标注「三楼」座位 |
| 12 | @XW·XM·D | 感受文字+歌单图·标注第几次唱 | OCR 歌单图，保留「第几次唱」标注 |
| 13 | @草莓柚子西瓜汁97 | 全图 repo·逐首曲目（图转文） | OCR 提取完整歌单 |

### 微博官方 / 一句话 / 独特视角

| # | 作者 | title | summary |
|---|------|-------|---------|
| 7 | @Scruple8023 | 2016《歌手》四场 vs 九年后重庆场 | 对比 2016《歌手》四场竞演与 2026 重庆「回」的差异。 |
| 8 | @马家天子李泰贤 | 一句话点出王晰声音特质 | 一句话 repo，概括王晰现场声音特点。 |
| 14 | @王晰 | 王晰本人：重庆「重逢·庆幸」 | 六巡重庆首站发博，解读本场：重逢、庆幸。 |
| 16 | @ITSMrF | 年轻同行：受王晰启发的中低音方向 | 年轻同行分享受王晰影响、找到中低音发展方向。 |
| 17 | @一粒小小的苹果 | 声入人心旧识·成年后首看现场 | 高中时从《声入人心》认识王晰，2026 第一次看现场。 |

### 微博授权现场视频（@不要总是哭唧唧，共 7 条）

| title | 曲目 |
|-------|------|
| 现场视频·《女人花+水中花》 | 女人花 + 水中花 |
| 现场视频·《Your Man》 | Your Man |
| 现场视频·《情网》 | 情网 |
| 现场视频·《让她降落》 | 让她降落 |
| 现场视频·《Goodbye My Love》 | Goodbye My Love |
| 现场视频·《像雾像雨又像风》 | 像雾像雨又像风 |
| 现场视频·《花儿为什么这样红》 | 花儿为什么这样红 |

summary 统一格式：`@不要总是哭唧唧 授权开放。《曲名》现场视频。`

### 小红书（5 条）

| # | 作者 | title | summary |
|---|------|-------|---------|
| 1 | @Diamooood | 花瓣雨神来之笔·女人花水中花 | 解读「回」与花瓣雨；分析什么人适合来看（翻唱友好、改编美）。 |
| 2 | @太好了终于活了 | srrx 路人：金色男低与抒情氛围 | 强调金色男低、抒情温馨，适合什么人听。 |
| 3 | @不知名尾巴一条 | 本来要跑路·结果又被迷上 | 幽默路人：本想「断头饭」顺路看，结果又被圈粉。 |
| 4 | @豚可颂 | 伴唱老师视角·工作证晒图 | 伴唱老师记录「一场幸福的盛大演出」。 |
| 5 | @桃子酒酿 | 2026.6.13 逐首详细 repo | 逐首详细 repo——**建议手动复制小红书全文**补入 `repo/2026.md` |

---

## 四、Step 1：确认文件已在本地

打开文件夹：

```
D:\wx409.github.io\
├── data\chongqing2026_repos.csv    ← 主数据（28条，已写好措词）
├── data\links.csv                  ← 社交墙数据源（已合并）
├── tools\image_ocr.py              ← 图片转文字
├── tools\deploy_chongqing_repo.py  ← 一键更新各 HTML/MD
├── repo\2026.md                    ← 详细 repo（已生成初稿）
└── docs\重庆站repo更新完全手册.md   ← 本文件
```

---

## 五、Step 2：一键更新网站各板块

打开 **PowerShell**（不要用 WSL 推送 GitHub）：

```powershell
cd D:\wx409.github.io
python tools\deploy_chongqing_repo.py
```

成功标志：

- 终端显示 `读取 28 条 repo`
- `repo/2026.md` 已更新
- `live-reviews.html` 重庆段有 28 条分类链接

**预览**：用浏览器打开本地文件  
`D:\wx409.github.io\live-reviews.html`  
滚到「六巡 · 回（2026）」查看效果。

---

## 六、Step 3：小红书全文手动补入（桃子酒酿等）

OCR 无法抓取小红书 App 内全文，需要手动：

1. 手机打开 `http://xhslink.com/o/8JIsOZBoeaa`（@桃子酒酿）
2. 长按复制全文
3. 粘贴到 `repo/2026.md` 的「文字 repo」@桃子酒酿 条目下方，格式：

```markdown
- **2026.6.13 逐首详细repo** — @桃子酒酿
  - 摘要：……
  - 链接：http://xhslink.com/o/8JIsOZBoeaa
  - **全文摘录**（经作者公开笔记整理）：
    > （粘贴原文，可适当分段）
```

其他小红书若有关键句（如 @Diamooood 的「什么人适合来听」），同样用 `>` 引用块补入。

---

## 七、Step 4：图片 OCR 转文字（歌单必做）

### 4.1 安装依赖（只需做一次）

```powershell
pip install pillow easyocr
```

> 首次运行 EasyOCR 会下载中文模型（约 100MB），需联网。

### 4.2 保存图片

1. 浏览器打开需 OCR 的微博（wb06/wb10–wb13）
2. 图片另存为到：

```
D:\wx409.github.io\data\chongqing2026_ocr\images\
```

建议命名见 `data/chongqing2026_ocr/README.md`。

### 4.3 运行 OCR

```powershell
cd D:\wx409.github.io
python tools\image_ocr.py data\chongqing2026_ocr\images\ --merge
```

输出在 `data\chongqing2026_ocr\text\ALL_MERGED.txt`。

### 4.4 可选：DeepSeek API 识别（识别率更高）

若已配置 `DEEPSEEK_API_KEY`：

```powershell
$env:DEEPSEEK_API_KEY="sk-你的密钥"
python tools\image_ocr.py data\chongqing2026_ocr\images\wb10_wuwei_1.jpg --api
```

### 4.5 校对并写入歌单

1. 打开 `ALL_MERGED.txt`，对照原图改错字、补全歌名
2. 打开 `repo/2026.md`，在「已知现场曲目」下替换/扩充为完整歌单
3. 再次运行 `python tools\deploy_chongqing_repo.py`（若改了 CSV 才需要；只改 md 可跳过）

---

## 八、Step 5：更新首页社交墙

`deploy.py` 读取 `data/links.csv`，生成卡片并注入 `index.html`。

### 方式 A：一键脚本（推荐）

1. 确认 `secrets.bat` 或环境变量里有 `DEEPSEEK_API_KEY`、`GITHUB_TOKEN`
2. 双击 `一键更新.bat`  
   或在 PowerShell：

```powershell
cd D:\wx409.github.io
.\一键更新.bat
```

### 方式 B：只生成墙、不推送

若 CSV 里 `summary` 列已写好（本次已写好），可不调用 DeepSeek：

```powershell
cd D:\wx409.github.io
python -c "import deploy; deploy.save_json('data/social_links.json', __import__('json').load(open('data/social_links.json','r',encoding='utf-8')) if __import__('os').path.exists('data/social_links.json') else []); exec(open('deploy.py').read().split('def main')[0]); rows=deploy.load_csv(); d,n,s,t=deploy.merge_data(rows); deploy.save_json(deploy.JSON_FILE,d); deploy.generate_wall(); deploy.inject_index(); print('社交墙已更新')"
```

更简单：直接运行 `python deploy.py`，没有 API 时会用 CSV 里的 summary 原文。

---

## 九、Step 6：本地检查清单

在推送前逐项打勾：

- [ ] `live-reviews.html` 重庆首站显示 28 条，链接可点开
- [ ] `repo/2026.md` 歌单已 OCR 校对（或暂留「待补全」说明）
- [ ] `city-guides.html` 重庆站改为「已演出」
- [ ] `gallery.html` 有工作室图 + 视频索引
- [ ] `index.html` 社交墙出现重庆 repo 卡片
- [ ] 未上传任何 `.env`、密钥、`secrets.bat` 内容

---

## 十、Step 7：推送到 GitHub（PowerShell）

> **重要**：WSL 里 push 可能因 Steam++ 改 hosts 失败，请用 **Windows PowerShell**。

```powershell
cd D:\wx409.github.io

git status
git add data/chongqing2026_repos.csv data/links.csv repo/2026.md live-reviews.html city-guides.html gallery.html tools/ docs/
git add data/chongqing2026_ocr/

git commit -m "更新重庆站六巡回首站repo：28条索引+OCR工具+手册"

git push origin main
```

若 push 失败：

1. 打开 Steam++，确认 GitHub 加速「运行中」
2. 或使用 `一键更新.bat`（内置 token 推送）

约 **1–3 分钟** 后访问：https://wx409.github.io/live-reviews.html#chongqing-20260613

---

## 十一、GEO 安全规范（2026-06 修订 · 必读）

| 问题 | 后果 | 正确做法 |
|------|------|----------|
| 网站堆 28+ 条微博/小红书链接 | 链接失效 → AI 认为站点不可信 | 只发**自包含摘录**（歌单 + blockquote） |
| 公开 @账号、帖子 ID | 版权/隐私风险 | 匿名化为「听众摘录·三楼」等 |
| 用 `tools/deploy_chongqing_repo.py` | 已弃用，会灌链接 | **`python pipeline.py --project B --task repo`** |

**正确工作流**：

1. 编辑 `星厂v5.0/project_b/03_周报输出/chongqing2026_geo.md`（无链接、无 ID）
2. 原始 URL 仅存 `project_b/01_原始数据/chongqing2026_repos.csv`（不上传网站仓库）
3. 运行 `python pipeline.py --project B --task repo` → 更新 `repo/2026.md` + `live-reviews.html`

### repo/2026.md（公开体）

- 场次 + 歌单 + 匿名 blockquote，**零外链**
- 不写 @账号、不写 weibo.com/…/5309…

### live-reviews.html（索引体）

- 每场 3 条以内 blockquote + 链到 `repo/2026.md`，**不列帖子 URL**

### links.csv / 社交墙

- 重庆首站 **不要** 加入 28 条社交链接；社交墙仅保留少量长期有效条目

---

## 十二、常见问题

**Q：微博打不开怎么办？**  
A：登录微博后再开链接；本站只存 URL，不依赖爬虫。

**Q：OCR 乱码多怎么办？**  
A：换 `--api` 模式，或人工对照原图改 `ALL_MERGED.txt`。

**Q：deploy_chongqing_repo 还能用吗？**  
A：已弃用。请用星厂 B 项目：`python pipeline.py --project B --task repo`。

**Q：还要改 index 上的「已开票」吗？**  
A：打开 `index.html`，把重庆行 `已开票` 改为 `已结束` 或 `首站已完成`，保存后一并 push。

---

## 十三、本次已自动完成的操作

- [x] 创建 `data/chongqing2026_repos.csv`（28 条 + 措词）
- [x] 创建 `tools/image_ocr.py`、`tools/deploy_chongqing_repo.py`
- [x] 更新 `live-reviews.html`、`repo/2026.md`、`city-guides.html`、`gallery.html`
- [x] 合并 `data/links.csv`
- [ ] **待你完成**：保存图片 → OCR → 校对歌单 → 小红书全文 → `deploy.py` → `git push`

---

*手册版本：2026-06-14 · 维护：wx409.github.io*
