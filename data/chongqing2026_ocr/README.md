# 重庆站 OCR 图片存放说明

把需要转文字的图片按下面命名放入 `images/` 子文件夹，然后运行 OCR。

## 建议文件名（对应 chongqing2026_repos.csv 的 id）

| 文件名建议 | 对应 repo | 说明 |
|-----------|----------|------|
| wb06_studio.jpg | wb06 | 王晰工作室官方现场图 |
| wb10_wuwei_1.jpg | wb10 | @邬尾 逐首详录（可多图 wb10_wuwei_2.jpg …） |
| wb11_ppabao.jpg | wb11 | @神经二条的pp阿豹 三楼视角 |
| wb12_xwxmd.jpg | wb12 | @XW·XM·D 歌单图 |
| wb13_caomei.jpg | wb13 | @草莓柚子西瓜汁97 全图repo |

## 如何获取图片

1. 浏览器打开对应微博链接
2. 右键图片 →「图片另存为」
3. 保存到本目录 `images/`

## 运行 OCR

```powershell
cd D:\wx409.github.io
pip install pillow easyocr
python tools\image_ocr.py data\chongqing2026_ocr\images\ --merge
```

识别结果在 `text/` 目录；合并文件 `ALL_MERGED.txt` 供校对后写入 `repo/2026.md`。
