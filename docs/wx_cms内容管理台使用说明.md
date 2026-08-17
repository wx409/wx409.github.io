# 王晰档案站 · 内容管理台（wx_cms）使用说明

> 面向"以后持续更新巡演讯息 / 反馈 / 新歌 / 新专辑"的日常维护。
> 更新日期：2026-08-17 · 维护者：wx409

## 一句话

你只要在对话里用大白话说要改什么，AI 会用本地工具 `wx_cms` 完成：
**增删改查 → 重建受影响页面 → git 精确暂存 + 提交**，最后你手动 `git push origin main`。

## 工具在哪

- 本地脚本：`E:\wx\私有工具\wx_cms\wx_cms.py`（私有，**不上传 GitHub**）
- 备份/日志/改动记录：`D:\wx409.github.io\temp\wx_cms\`（已被 `.gitignore` 忽略，不会上传）
- GUI 面板：本应用「设置 → 王晰档案站」（状态看板 + 指令生成）

## 四类内容 → 改哪个文件 → 重建什么

| 内容 | 落点数据文件 | 页面 | 重建命令（regen 目标） |
|------|-------------|------|----------------------|
| 巡演讯息（官宣/开票等快讯） | `data/timeline.json` | timeline.html（运行时读取） | 无需重建 |
| 待确认候选 | `data/pending_events.json` | — | 无需重建 |
| 场次档案（新增/取消/改场馆） | `data/cities.json` | live-reviews.html | `regen live-reviews` |
| 现场反馈 repo | `data/live_repos.json` | live-reviews.html | `regen live-reviews` |
| 新歌 / 新专辑 | `data/albums.json` | discography.html（运行时读取） | 无需重建（可选 `regen songs entity`） |

## 常用命令速查

```bash
# 统一用 -X utf8 避免中文乱码
python -X utf8 "E:\wx\私有工具\wx_cms\wx_cms.py" overview      # 看全站状态

# 巡演讯息（时间轴）
python -X utf8 "E:\wx\私有工具\wx_cms\wx_cms.py" tour add --date 2026-09-20 --title "六巡「回」成都站·已官宣" --type tour
python -X utf8 "E:\wx\私有工具\wx_cms\wx_cms.py" tour remove --date 2026-09-20 --title 成都

# 场次档案（cities.json，注意：最终以长表为唯一事实源）
python -X utf8 "E:\wx\私有工具\wx_cms\wx_cms.py" show add --date 2026-09-20 --city 成都 --venue 成都城市音乐厅 --tour 六巡 --theme 回 --timeline
python -X utf8 "E:\wx\私有工具\wx_cms\wx_cms.py" show update --date 2026-09-20 --status cancelled

# 现场反馈
python -X utf8 "E:\wx\私有工具\wx_cms\wx_cms.py" repo add --date 2026-08-23 --title "广州站repo" --platform 微博 --url https://... --level verified

# 新专辑 / 新歌
python -X utf8 "E:\wx\私有工具\wx_cms\wx_cms.py" album add --name "新专辑" --release 2026-09
python -X utf8 "E:\wx\私有工具\wx_cms\wx_cms.py" song add --album "新专辑" --title "新歌名" --singer 王晰

# 重建受影响页面（可多个目标）
python -X utf8 "E:\wx\私有工具\wx_cms\wx_cms.py" regen live-reviews songs entity

# git 精确暂存 + 提交（绝不 add -A、绝不 push）
python -X utf8 "E:\wx\私有工具\wx_cms\wx_cms.py" commit -m "新增成都站 + 现场repo"
```

## 安全纪律（每次都要遵守）

1. **永不 `git push`**：工具只做 `git add 具体文件` + `git commit`，推送永远由你手动：
   `cd D:\wx409.github.io && git push origin main`（或双击 `一键部署推送.bat`）。
2. **永不 `git add -A`**：只精确暂存明确列出的站点内容文件。
3. **不碰密钥**：Cookie / `.env` / `secrets.bat` / `radio_proxy.py` 等一律不读不写不上传。
4. 每次写 JSON 前自动备份到 `temp\wx_cms\backups\`。

## 一个关键事实源提醒（重要）

`data/cities.json`、`data/setlists.json`、`map/index.html`、`live/index.html` 最终以
**「巡演歌单长表 xlsx」** 为唯一事实源（`E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx`）。
`wx_cms` 支持直接改 `cities.json` 应急（并会提示），但下次 `deploy_all.py`（从长表重生成）可能覆盖；
**要让地图/巡演目录永久同步，请把新场次也补进长表**。
