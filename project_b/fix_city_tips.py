# -*- coding: utf-8 -*-
"""为海口/珠海/厦门/鄂尔多斯 4 城补充 web_tips（子代理全网调研结果）"""
import json

ROOT = r"D:\wx409.github.io"
P = ROOT + r"\data\city_guides.json"

TIPS = {
    "海口": [
        {"title": "东方环球大剧院 地址·路线·周边", "snippet": "地址电话路线周边一键查", "source": "https://m.map.360.cn/m/search/detail/pid=fe6cebdeb74fd4ac"},
        {"title": "东方环球大剧院 交通·附近酒店", "snippet": "位置交通指引周边查询", "source": "https://m.city8.com/hk/movie/824asg6e1drjbd09ef"},
    ],
    "珠海": [
        {"title": "日月贝 停车收费标准", "snippet": "停车场收费信息汇总", "source": "http://zh.bendibao.com/tour/2023817/86837.shtm"},
        {"title": "日月贝 玩乐全攻略", "snippet": "交通美食懒人包", "source": "https://irtrips.tw/blogs/1468093"},
        {"title": "日月贝 交通路线机位", "snippet": "海边日落交通整理", "source": "https://tw.trip.com/moments/detail/zhuhai-27-149541974/"},
        {"title": "日月贝 保姆级攻略", "snippet": "日夜双景游玩攻略", "source": "https://tw.trip.com/moments/theme/poi-beishan-village-136165140-attraction-993137/#2"},
    ],
    "厦门": [
        {"title": "沧江剧院 公交指南", "snippet": "公交路线查询", "source": "https://xm.city8.com/movie/8a0taz72ak6lb5b25f_traffic"},
        {"title": "沧江剧院 周边配套", "snippet": "周边设施一览", "source": "https://xm.city8.com/movie/8a0taz72ak6lb5b25f_around"},
        {"title": "沧江剧院 门票·评论·营业", "snippet": "营业时间与点评", "source": "https://tw.trip.com/travel-guide/attraction/xiamen/cangjiang-theater-31823293"},
    ],
    "鄂尔多斯": [
        {"title": "鄂尔多斯大剧院 百科", "snippet": "场馆简介与位置（保利院线运营）", "source": "https://wapbaike.baidu.com/item/%E9%84%82%E5%B0%94%E5%A4%9A%E6%96%AF%E5%A4%A7%E5%89%A7%E9%99%A2/1578575"},
        {"title": "大剧院 停车场·交通指引", "snippet": "停车与交通指引", "source": "https://eeds.city8.com/transport/81h24n81d2hlb08e11"},
        {"title": "大剧院 实拍·游玩指南", "snippet": "游客实拍攻略", "source": "https://tw.trip.com/moments/poi-ordos-grand-theatre-10541039/#3"},
        {"title": "保利剧院管理公司 百科", "snippet": "保利运营方简介", "source": "https://baike.baidu.com/item/%E9%84%82%E5%B0%94%E5%A4%9A%E6%96%AF%E5%B8%82%E4%BF%9D%E5%88%A9%E5%89%A7%E9%99%A2%E7%AE%A1%E7%90%86%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8/63828387"},
    ],
}

g = json.load(open(P, encoding="utf-8"))
for city, tips in TIPS.items():
    if city not in g:
        print("跳过（无此城）:", city)
        continue
    existing = g[city].get("web_tips") or []
    urls = {t.get("source") for t in existing}
    added = 0
    for t in tips:
        if t["source"] not in urls:
            existing.append(t)
            urls.add(t["source"])
            added += 1
    g[city]["web_tips"] = existing
    print("%s: 已有 %d 条，新增 %d 条，共 %d" % (city, len(existing) - added, added, len(existing)))

json.dump(g, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[OK]")
