# -*- coding: utf-8 -*-
"""按任务要求校正 sitemap.xml 核心 URL 的 lastmod/changefreq"""
import xml.etree.ElementTree as ET

P = r"D:\wx409.github.io\sitemap.xml"
LAST = "2026-08-16"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# URL 后缀 -> (changefreq)
RULES = {
    "https://wx409.github.io/": "weekly",
    "live-reviews.html": "weekly",
    "discography.html": "weekly",
    "academic.html": "monthly",
    "gallery.html": "monthly",
    "city-guides.html": "weekly",
    "dashboard/": "daily",
    "map/": "monthly",
    "tavern/": "weekly",
    "culture/": "monthly",
}

tree = ET.parse(P)
root = tree.getroot()
changed = 0
for url in root.findall("sm:url", NS):
    loc = url.findtext("sm:loc", default="", namespaces=NS)
    for suffix, freq in RULES.items():
        if loc == suffix or loc.endswith("/" + suffix.lstrip("/")) or loc.endswith(suffix):
            lm = url.find("sm:lastmod", NS)
            cf = url.find("sm:changefreq", NS)
            if lm is not None:
                lm.text = LAST
            if cf is not None:
                cf.text = freq
            changed += 1
            print("更新:", loc, "->", freq)
            break

tree.write(P, encoding="utf-8", xml_declaration=True)
print("[OK] 更新 %d 条" % changed)
