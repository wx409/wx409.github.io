"""每周关键数据备份（可指向网盘同步目录）

做什么
  · 打包「不可再生」的数据：站点 data/*.json、tavern 数据、dashboard 数据、指数索引目录
  · 排除一切凭据与音频（cookie / qqmusic.txt / .env / secrets / 音频），避免上传到网盘
  · 落盘为 <dest>/weekly/site_backup_YYYYMMDD_HHMM.zip，并按 --keep 保留最近 N 份
  · 打印清单与体积，失败有明确退出码

用法
  python -X utf8 project_b/backup_key_data.py                  # 默认 G:\\网站备份
  python -X utf8 project_b/backup_key_data.py --dest "D:\\备份"
  python -X utf8 project_b/backup_key_data.py --dry            # 只列清单不打包
"""
import argparse
import fnmatch
import os
import sys
import time
import zipfile

REPO = r"D:\wx409.github.io"
IDX = r"E:\wx\index_records"

DEFAULT_DEST = r"G:\网站备份"

# 要备份的目录/文件（存在才收）
SOURCES = [
    (os.path.join(REPO, "data"), ("*.json", "*.md")),
    (os.path.join(REPO, "tavern"), ("*.json",)),
    (os.path.join(REPO, "dashboard"), ("*.json",)),
    (os.path.join(REPO, "docs"), ("*.md",)),
    (REPO, ("llms.txt", "AGENTS.md", "sitemap.xml")),
]

# 严禁进备份（含凭据/隐私/大文件）
BLOCK_PATTERNS = [
    "*cookie*", "*Cookie*", "qqmusic.txt", ".env", "secrets*", "*secret*",
    "*.mp3", "*.m4a", "*.wav", "*.mp4", "*.flac", "*.aac", "*.webm",
    "*.log", "*.dpapi", "radio_cookie*",
]


def blocked(name):
    n = os.path.basename(name)
    return any(fnmatch.fnmatch(n, p) for p in BLOCK_PATTERNS)


def collect():
    files = []
    for base, patterns in SOURCES:
        if not os.path.isdir(base):
            continue
        for root, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs if d not in ("node_modules", "__pycache__", ".git", "temp", "logs")]
            depth = root[len(base):].count(os.sep)
            if depth > 3:
                dirs[:] = []
                continue
            for n in names:
                if not any(fnmatch.fnmatch(n, p) for p in patterns):
                    continue
                p = os.path.join(root, n)
                if blocked(p):
                    continue
                try:
                    if os.path.getsize(p) > 40 * 1024 * 1024:   # 单文件 >40MB 跳过
                        continue
                except OSError:
                    continue
                files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=DEFAULT_DEST)
    ap.add_argument("--keep", type=int, default=8, help="保留最近几份")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    files = collect()
    total = sum(os.path.getsize(f) for f in files)
    print("待备份 %d 个文件，约 %.1f MB" % (len(files), total / 1024 / 1024))
    if a.dry:
        for f in files[:15]:
            print("   ", f)
        if len(files) > 15:
            print("    …共 %d 个" % len(files))
        return 0

    if not os.path.isdir(a.dest):
        print("！备份目录不存在：%s" % a.dest)
        print("  请先创建（网盘同步目录 / 移动硬盘），或改用 --dest 指定其他路径")
        return 3

    outdir = os.path.join(a.dest, "weekly")
    os.makedirs(outdir, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M")
    out = os.path.join(outdir, "site_backup_%s.zip" % stamp)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in files:
            arc = os.path.join("D", os.path.relpath(f, "D:\\")) if f.startswith("D:\\") \
                else os.path.join("E", os.path.relpath(f, "E:\\"))
            z.write(f, arc)
        z.writestr("BACKUP_INFO.txt",
                   "王晰档案站关键数据备份\n时间: %s\n文件数: %d\n体积: %.1f MB\n"
                   "排除: cookie/qqmusic/.env/secrets/音频/日志\n" % (stamp, len(files), total / 1024 / 1024))

    size = os.path.getsize(out) / 1024 / 1024
    print("已生成 %s（%.1f MB）" % (out, size))

    zips = sorted((os.path.join(outdir, n) for n in os.listdir(outdir) if n.startswith("site_backup_") and n.endswith(".zip")),
                  key=os.path.getmtime, reverse=True)
    for old in zips[a.keep:]:
        try:
            os.remove(old)
            print("   清理旧备份", os.path.basename(old))
        except OSError:
            pass
    print("保留 %d 份：%s" % (min(len(zips), a.keep), ", ".join(os.path.basename(z) for z in zips[:a.keep])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
