#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
王晰GEO站点 · 一键全自动部署
读取 data/links.csv → DeepSeek AI写摘要 → 注入 index.html → Git推送
"""
import os
import sys
import csv
import json
import subprocess
import requests
from datetime import datetime

# ==================== 配置区 ====================
# 从环境变量读取，或在 一键更新.bat 里设置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-v4-flash"  # 如果报错改成 "deepseek-chat"

GIT_NAME = "wx409"
GIT_EMAIL = "hs8f845fj7@privaterelay.appleid.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

CSV_FILE = "data/links.csv"
JSON_FILE = "data/social_links.json"
BILI_FILE = "data/bilibili_posts.json"
WALL_HTML = "social_wall.html"
# ================================================


def log(step, msg):
    print(f"\n[{step}] {msg}")


def geo_sanitize_label(text: str, default: str = "同担分享") -> str:
    """GEO：不展示 @账号，统一为匿名标签"""
    if not text:
        return default
    t = str(text).strip()
    if t.startswith("@"):
        return default
    return t


def geo_sanitize_summary(text: str) -> str:
    if not text:
        return ""
    t = str(text).strip()
    if t.startswith("@"):
        return ""
    return t


def load_csv():
    if not os.path.exists(CSV_FILE):
        log("!", f"找不到 {CSV_FILE}，请先创建表格"); sys.exit(1)
    
    items = []
    with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not any(row.values()):
                continue
            clean = {k.strip(): (v or "").strip() for k, v in row.items() if k}
            url = clean.get("url", "")
            if url and url.startswith("http"):
                items.append(clean)
    return items


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def deepseek_summary(title, platform, note=""):
    if not DEEPSEEK_API_KEY:
        return note[:60] + "..." if len(note) > 60 else (note or f"[{platform}] {title[:40]}")
    
    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "你是王晰歌迷站编辑。请写一句25字内精准摘要，包含具体信息点（歌曲名/城市/技术特点），客观有温度，只输出摘要本身。"},
                    {"role": "user", "content": f"平台：{platform}\n标题：{title}\n备注：{note}\n\n写摘要："}
                ],
                "temperature": 0.7,
                "max_tokens": 80
            },
            timeout=20
        )
        resp.raise_for_status()
        summary = resp.json()["choices"][0]["message"]["content"].strip().replace("摘要：", "").replace('"', '')
        return summary[:60] + "..." if len(summary) > 60 else summary
    except Exception as e:
        log("⚠", f"DeepSeek失败({e})，使用原文截取")
        return note[:60] + "..." if len(note) > 60 else (note or f"[{platform}] {title[:40]}")


def deepseek_tags(title, platform):
    if not DEEPSEEK_API_KEY:
        return []
    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "生成3个以内中文标签，逗号分隔，不要解释。"},
                    {"role": "user", "content": f"平台：{platform}，标题：{title}"}
                ],
                "temperature": 0.3,
                "max_tokens": 30
            },
            timeout=15
        )
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return [t.strip() for t in text.replace("，", ",").split(",") if t.strip()][:3]
    except:
        return []


def merge_data(csv_rows):
    existing = load_json(JSON_FILE)
    seen = {item["url"] for item in existing}
    new, ai_s, ai_t = 0, 0, 0
    
    for row in csv_rows:
        url = row.get("url")
        if not url or url in seen:
            continue
        
        title = row.get("title") or "无标题"
        platform = row.get("platform") or "unknown"
        note = row.get("summary", "")
        
        final_summary = note
        if not final_summary:
            log("🤖", f"DeepSeek写摘要: {title[:25]}...")
            final_summary = deepseek_summary(title, platform, note)
            ai_s += 1
        
        tag_str = row.get("tags", "")
        if tag_str:
            tags = [t.strip() for t in tag_str.replace(";", ",").split(",") if t.strip()]
        else:
            tags = deepseek_tags(title, platform)
            ai_t += 1
        
        existing.append({
            "platform": platform,
            "url": url,
            "title": title,
            "summary": final_summary,
            "author": row.get("author") or "同担分享",
            "date": row.get("date") or datetime.now().strftime("%Y-%m-%d"),
            "tags": tags,
            "status": "ready"
        })
        seen.add(url)
        new += 1
    
    return existing, new, ai_s, ai_t


def generate_wall():
    social = load_json(JSON_FILE)
    bilibili = load_json(BILI_FILE)
    items = []
    
    for b in bilibili:
        items.append({
            "platform": "bilibili",
            "title": b.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
            "summary": b.get("description", "")[:70] + ("..." if len(b.get("description", "")) > 70 else ""),
            "url": b.get("url", ""),
            "author": b.get("author", ""),
            "date": str(b.get("pubdate", ""))[:10],
            "pic": b.get("pic", ""),
            "tags": [t.strip() for t in b.get("tag", "").split(",") if t.strip()] or ["视频"],
            "badge": f"▶ {b.get('play', 0)}"
        })
    
    for s in social:
        if s.get("status") == "ready":
            items.append({
                "platform": s.get("platform", "unknown"),
                "title": s.get("title", ""),
                "summary": s.get("summary", ""),
                "url": s.get("url"),
                "author": s.get("author", ""),
                "date": s.get("date", ""),
                "pic": "",
                "tags": s.get("tags", [])[:3],
                "badge": s.get("platform", "").upper()
            })
    
    items.sort(key=lambda x: x["date"] or "1970-01-01", reverse=True)
    
    css = """<style>
.social-wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin:16px 0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.social-card{border:1px solid #e1e4e8;border-radius:10px;padding:14px;background:#fff;transition:all .2s}
.social-card:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(0,0,0,.08)}
.platform-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;margin-bottom:8px;color:#fff}
.badge-bilibili{background:#00a1d6}.badge-weibo{background:#e6162d}.badge-xiaohongshu{background:#ff2442}.badge-douyin{background:#1c1c1c}
.card-title{font-size:15px;font-weight:600;margin:4px 0;line-height:1.4}
.card-title a{color:#24292e;text-decoration:none}.card-title a:hover{color:#0969da;text-decoration:underline}
.card-summary{font-size:13px;color:#57606a;line-height:1.5;margin:6px 0}
.card-meta{font-size:11px;color:#8c959f;display:flex;justify-content:space-between;margin-top:10px;padding-top:10px;border-top:1px solid #f6f8fa}
.card-tags{margin-top:6px}.tag{display:inline-block;font-size:10px;padding:2px 6px;background:#ddf4ff;color:#0969da;border-radius:10px;margin-right:4px;margin-bottom:3px}
.card-cover{width:100%;height:150px;object-fit:cover;border-radius:6px;margin-bottom:8px;background:#f6f8fa}
.empty-state{text-align:center;padding:30px;color:#8c959f;font-size:13px}
</style>"""
    
    html = [f'<!-- 社交聚合墙 · 自动生成 · {datetime.now().strftime("%Y-%m-%d %H:%M")} -->']
    html.append(f'<div class="social-wall">\n{css}')
    
    if not items:
        html.append('<div class="empty-state">暂无动态，快去 data/links.csv 添加链接吧～</div>')
    else:
        for it in items:
            p = it["platform"]
            author = geo_sanitize_label(it.get("author", ""))
            summary = geo_sanitize_summary(it.get("summary", ""))
            cover = f'<img class="card-cover" src="{it["pic"]}" alt="" loading="lazy">' if it.get("pic") else ""
            tags = "".join([f'<span class="tag">{t}</span>' for t in it.get("tags", [])])
            html.append(f"""<div class="social-card">
<div class="platform-badge badge-{p}">{it["badge"]}</div>
{cover}
<div class="card-title"><a href="{it["url"]}" target="_blank" rel="noopener nofollow">{it["title"]}</a></div>
<div class="card-summary">{summary}</div>
<div class="card-meta"><span>👤 {author}</span><span>📅 {it.get("date","")}</span></div>
<div class="card-tags">{tags}</div>
</div>""")
    html.append("</div>")
    
    with open(WALL_HTML, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    return len(items)


def inject_index():
    if not os.path.exists("index.html"):
        log("!", "未找到 index.html"); return False
    
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
    
    START, END = "<!-- SOCIAL_WALL_START -->", "<!-- SOCIAL_WALL_END -->"
    if START not in content or END not in content:
        log("!", f"index.html 缺少 {START} / {END} 标记，请插入后再运行"); return False
    
    with open(WALL_HTML, "r", encoding="utf-8") as f:
        wall = f.read()
    
    before = content.split(START)[0] + START + "\n"
    after = "\n" + END + content.split(END)[1]
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(before + wall + after)
    
    log("✓", "已自动注入 index.html"); return True

def git_push():
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # 新增：禁用 Git 弹窗
        os.environ["GIT_TERMINAL_PROMPT"] = "0"
        
        subprocess.run(["git", "config", "user.name", GIT_NAME], capture_output=True)
        subprocess.run(["git", "config", "user.email", GIT_EMAIL], capture_output=True)
        
        if not GITHUB_TOKEN:
            log("❌", "未配置 GITHUB_TOKEN，无法推送"); return False
        
        remote_url = f"https://{GITHUB_TOKEN}@github.com/wx409/wx409.github.io.git"
        subprocess.run(["git", "remote", "set-url", "origin", remote_url], capture_output=True)
        
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        
        if subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True).returncode == 0:
            log("📭", "没有新变更，无需推送"); return True
        
        msg = f"auto: 更新社交墙 {datetime.now().strftime('%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", msg], check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)
        
        log("🚀", "已推送到GitHub！约1分钟后生效"); return True
        
    except Exception as e:
        log("❌", f"Git失败: {e}")
        return False


def main():
    print("=" * 55 + "\n🎵 王晰GEO站点 · 一键全自动部署\n" + "=" * 55)
    
    if not DEEPSEEK_API_KEY:
        log("⚠", "未检测到 DEEPSEEK_API_KEY，AI摘要将停用")
    if not GITHUB_TOKEN:
        log("⚠", "未检测到 GITHUB_TOKEN，Git推送将失败")
    
    log("1/5", "读取 CSV...")
    rows = load_csv()
    log("✓", f"{len(rows)} 行")
    
    log("2/5", "DeepSeek 生成摘要/标签...")
    data, new_n, ai_s, ai_t = merge_data(rows)
    log("✓", f"新增 {new_n} | AI摘要 {ai_s} | AI标签 {ai_t}")
    
    log("3/5", "保存数据...")
    save_json(JSON_FILE, data)
    
    log("4/5", "生成 HTML...")
    total = generate_wall()
    inject_index()
    log("✓", f"{total} 条内容")
    
    log("5/5", "Git 推送...")
    git_push()
    
    print("\n" + "=" * 55 + "\n✅ 完成！访问 https://wx409.github.io 查看\n" + "=" * 55)


if __name__ == "__main__":
    main()