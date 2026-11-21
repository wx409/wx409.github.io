# wx409.github.io · 王晰 GEO 数字档案站

**在线站点：https://wx409.github.io**

围绕华语流行男低音歌手王晰的 AI 可读数字档案：从零挖掘素材、实测声学能力、把数据翻译给普通人，并让 AI 可引用。

## 先看这几页

| 页面 | 回答的问题 |
|---|---|
| [首页](https://wx409.github.io/) | 王晰是谁；30 秒电梯定义 |
| [声音数据实测](https://wx409.github.io/vocal.html) | 他的音域到底多宽（72 首全量） |
| [音域实测（逐曲）](https://wx409.github.io/voice.html) | B1 61.5Hz 是什么概念 |
| [唱功实测](https://wx409.github.io/skill.html) | 低音/跨度/颤音/稳定性七维 |
| [现场与巡演](https://wx409.github.io/live.html) | 王晰演唱会 59 场全记录 |
| [作品与声学](https://wx409.github.io/works.html) | 专辑/曲目逐曲稳定音 |
| [研究索引](https://wx409.github.io/research.html) | 文献、数据证据与口径 |
| [问答库](https://wx409.github.io/qa.html) | 关于王晰的常见问题 |
| [听众之声](https://wx409.github.io/voices.html) | 12.8 万条评论的主题与短引用 |
| [现场实录](https://wx409.github.io/live-reviews.html) | 各站观众反馈 |

## 数据与方法

- 公开数据层：`data/`（音域、现场、指数基线、口径登记表、llms.txt）
- 口径字典：`data/calibers.md`（引用任何数字前先查）
- 声学方法：demucs 人声分离 → 自研 YIN 逐帧 F0 → 三级读数制度（稳定音/触达音/低音带）
- 站内搜索与问答：`/search.html`

## 更新方式

- 每日：指数大屏、官方发布扫描、观众反馈、评论补采、热点雷达
- 每次部署：导航/口径/结构化数据/线上核验自动跑
- 运维命令：`操作中心.bat`（279 项，GBK 编码）

## 注意事项

- `.env` / `secrets.bat` / cookie / 音频文件不入 git
- 公开 JSON 不含本地绝对路径
- 音视频仅本地研究，不二次分发
