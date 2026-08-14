# 一键部署流水线 · deploy_all.py 使用说明

> **脚本位置**：`D:\wx409.github.io\project_b\deploy_all.py`  
> **适用场景**：巡演长表 / 数据更新后，需要同步刷新全站生成物  
> **维护原则**：长表是唯一事实源；一切生成物由脚本产出，不手改

---

## 一、这个脚本解决什么问题

本站有 **9 个生成脚本**，此前每次数据更新需要**手动按顺序逐个运行**，漏跑一个就会造成站内数据不一致（如地图更新了、故事页没更新）。

`deploy_all.py` 把 9 步串成**一条流水线**：

```
长表/数据更新
      │
      ▼
┌─────────────────────────────────────────────┐
│ 1. 敏感文件安全检查（有风险立即中止）          │
│ 2. generate_cities_json.py   → 地图          │
│ 3. generate_tour_index.py    → 巡演目录      │
│ 4. update_index_table.py     → 首页表格      │
│ 5. build_entity_index.py     → 跨站关系图谱   │
│ 6. generate_city_guides.py   → 22城攻略      │
│ 7. build_story.py            → 数据故事页    │
│ 8. _build_episodes.py        → 小酒馆逐字稿  │
│ 9. _build_songs_compact.py   → 小酒馆歌曲索引│
│10. build_music_index.py      → 音乐数据周报  │
│11. git add + git commit（自动）              │
│12. 提示手动 git push                         │
└─────────────────────────────────────────────┘
```

---

## 二、快速开始（3 种用法）

### 用法 1：完整部署（日常推荐）
```powershell
cd D:\wx409.github.io
python project_b\deploy_all.py
```
跑完全部 9 步 → 自动 git commit → 提示手动 push。

### 用法 2：只生成不提交（预览/调试）
```powershell
python project_b\deploy_all.py --no-git
```
生成所有页面，但**不执行 git commit**。适合先看效果再决定提交。

### 用法 3：自定义提交信息
```powershell
python project_b\deploy_all.py --commit "地图：新增XX城市数据"
```

---

## 三、流水线各步骤详解

| # | 脚本 | 产出 | 说明 |
|---|---|---|---|
| 1 | （安全检查） | — | 扫描工作区是否有 `radio_proxy` / `radio_cookie` / `secrets` / `.env` / 音频文件，**有则中止** |
| 2 | `E:\wx\私有工具\generate_cities_json.py` | `data/cities.json` + `map/index.html` | 地图数据与页面；**关键步骤** |
| 3 | `generate_tour_index.py` | `live/index.html` | 巡演目录（读长表场次 + dashboard 效应）；**关键** |
| 4 | `update_index_table.py` | 首页表格 | 首页"最新演出动态"表的效应列注入；**关键** |
| 5 | `project_b\build_entity_index.py` | `entity_index.json` | 跨站关系图谱（歌曲↔城市↔场馆↔EP）；**关键** |
| 6 | `project_b\generate_city_guides.py` | `data/city_guides.json` | 22 城攻略；**自动保留已有 web_tips**（搜索成果不丢）；**关键** |
| 7 | `project_b\build_story.py` | `story.html` | 数据故事页（跨城之王/酒馆之声等）；**关键** |
| 8 | `tavern\_build_episodes.py` | `tavern/ep/*.html`（106 页） | 小酒馆逐字稿页 + hasPart 切片锚点；**关键** |
| 9 | `tavern\_build_songs_compact.py` | `tavern/songs_compact.json` | 小酒馆歌曲索引（前端降级数据）；非关键 |
| 10 | `project_b\build_music_index.py` | `data/music-index.md` + `.html` | 音乐数据周报；非关键 |
| 11 | git commit | — | 自动 `git add -A` + commit（无变更时跳过） |
| 12 | 提示 push | — | 沙箱无法 ssh，需手动执行 |

> **关键步骤**（critical）：失败立即中止，避免半成品上线。  
> **非关键步骤**（非 critical）：失败只警告继续，如周报、歌曲索引等次要产物。

---

## 四、运行前提

| 前提 | 说明 |
|---|---|
| Python 3.10+ | 已装（`python --version` 确认） |
| pandas / openpyxl | 长表读取依赖：`pip install pandas openpyxl` |
| 长表文件存在 | `E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx` |
| 生成器源目录 | `E:\wx\私有工具\generate_cities_json.py` 存在（脚本在 E 盘，不在仓库） |
| 无敏感文件 | 工作区不应出现 `tavern/radio_proxy.py` 等（脚本会拦截） |

---

## 五、安全机制

### 1. 敏感文件拦截
提交前扫描 `git status` 输出，匹配以下关键词**立即中止**：
```
radio_proxy / radio_cookie / secrets / .env / .mp3 / .flac
```
> 这是纪律第 3 条的自动化落地：敏感文件绝不进 git。

### 2. 失败处理策略
- **关键步骤失败** → 流水线中止（`exit code 2`），不会带着残缺数据提交
- **非关键步骤失败** → 警告后继续
- 每步输出写入 `temp/deploy_run.log`（UTF-8），避免 Windows 控制台 GBK 乱码

### 3. git 提交范围
- `git add -A`（全部变更）——但**敏感文件已被 .gitignore 和步骤 1 双重拦截**
- 无变更时 git commit 自动跳过（不算错误）

---

## 六、手动推送（流水线最后一步）

DSH 沙箱环境无法执行 `git push`（ssh 信号管道被拦截，Win32 error 5），**这是预期行为**，不是脚本 bug。

流水线结束后请手动执行：
```powershell
cd D:\wx409.github.io
git push origin main
```

推送成功标志：`main -> main`。等 1-2 分钟 GitHub Pages 生效。

---

## 七、数据流与依赖关系

```
巡演歌单长表（唯一事实源，xlsx）
      │
      ├──→ generate_cities_json.py ──→ cities.json ──→ map/index.html
      │                                          │
      │                                          └──→ city-guides.html（前端 fetch）
      ├──→ generate_tour_index.py ──→ live/index.html
      │
      └──→ build_entity_index.py ──→ entity_index.json ──→ 大屏搜索 / 城市攻略 / 故事页
                                                          └──→ story.html（build_story.py）
```

- **dashboard_data.json**（大屏自动生成）→ 提供效应/指数数据，流水线只读
- **entity_index.json** → 中间枢纽：歌曲↔城市↔场馆↔EP 关系，多个页面消费
- 流水线**不修改** dashboard 数据源（它是大屏生成器 auto_deploy 的领地）

---

## 八、常见问题（FAQ）

### Q1：运行报 `ModuleNotFoundError: pandas`
```powershell
pip install pandas openpyxl
```

### Q2：某个关键步骤失败，如何定位？
查看 `temp/deploy_run.log` 末尾，或直接跑单个脚本：
```powershell
python E:\wx\私有工具\generate_cities_json.py
```

### Q3：city_guides 的 web_tips 会被清空吗？
**不会**。步骤 6 会读取旧 `city_guides.json` 并保留已有 web_tips。只有手动删文件才会丢。

### Q4：跑完发现 story.html 数字没变？
正常。story 的数字来自 entity_index.json（步骤 5），若长表未变则结果相同。若确认长表变了但数字没变，检查步骤 5 是否成功（看日志）。

### Q5：为什么每次都要手动 push？
DSH 沙箱禁止 ssh 子进程（Win32 error 5）。这是环境限制，与脚本无关。

---

## 九、维护建议

1. **长表更新后**：直接跑 `python project_b\deploy_all.py`，一条命令完成全站同步
2. **只改了 YAML/live 页素材**：不需要流水线，单独跑 `python generate_live_page.py --config xxx.yaml`
3. **只改了小酒馆逐字稿**：单独跑 `python tavern\_build_episodes.py`
4. **新增城市**：需在 `E:\wx\私有工具\generate_cities_json.py` 的 `COORDS` 字典补经纬度，否则脚本提示缺坐标
5. **新增歌曲**：往链接清单 Excel 加行（第 4 列填链接），下次大屏批次自动纳入
6. **定期备份**：长表 + 歌曲信息表 + 生成器源码（E 盘）不在 git，需手动备份

---

## 十、版本记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-08-14 | v1.0 | 初始版本：9 步流水线 + 安全检查 + 自动提交 |

---

*本说明与 `docs/王晰GEO资料站完全操作手册.md` 配套使用；手册管全站操作，本文档只管部署流水线。*
