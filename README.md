# wx409.github.io · 王晰 GEO 资料站

GitHub Pages: https://wx409.github.io

## 目录结构（与星厂 v5.0 B 项目对齐）

```
wx409.github.io/
├── index.html              # 首页（含同担动态聚合）
├── live-reviews.html       # 现场实录
├── discography.html        # 作品百科
├── academic.html           # 学术研究
├── gallery.html            # 视觉记录
├── city-guides.html        # 城市攻略
├── data/
│   ├── music-index.html    # 音乐数据周报（浏览器可读）
│   ├── music-index.md      # 音乐数据周报（源文件）
│   ├── weekly/             # 历史周报存档
│   ├── links.csv           # 社交链接输入（deploy.py）
│   └── social_links.json   # 社交链接数据
├── culture/
│   └── index.html          # 文化足迹（星厂 culture 任务部署）
├── repo/
│   └── 2026.md             # 现场 repo 库
└── deploy.py               # 社交墙一键更新（独立脚本）
```

## 两种更新方式

### 1. 星厂 v5.0 管道（推荐）

```bash
cd /mnt/d/XingWorks/星厂v5.0
source /mnt/d/XingWorks/venv/bin/activate

# 音乐数据周报（每周）
python3 pipeline.py --project B --task weekly

# 文化足迹（有新事件时）
python3 pipeline.py --project B --task culture
```

### 2. 社交墙（deploy.py）

编辑 `data/links.csv` 后，在网站目录运行 `python deploy.py`（需配置 DEEPSEEK_API_KEY 和 GITHUB_TOKEN）。

## 注意事项

- `.env` / `secrets.bat` 不要提交到 Git
- 文化足迹源数据：`星厂v5.0/project_b/04_文化足迹/culture_events.json`
