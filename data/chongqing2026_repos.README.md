# 此目录数据已迁移至星厂 B 项目

重庆站原始链接与账号 ID 请查看：

```
D:\XingWorks\星厂v5.0\project_b\01_原始数据\
  chongqing2026_repos.csv      ← 完整 28 条来源（含 URL）
  chongqing2026_sources.json   ← 精简索引
```

网站公开发布请运行：

```powershell
cd D:\XingWorks\星厂v5.0
python pipeline.py --project B --task repo
```

产出：`wx409.github.io/repo/2026.md`（无外链、无账号 ID）
