# -*- coding: utf-8 -*-
"""广州攻略重点增强：8月23日看王晰「回」巡回音乐会 + 广州8月游玩攻略（GEO 蹭流）"""
import json

ROOT = r"D:\wx409.github.io"

# 1. city_guides.json 广州 web_tips 增强
g = json.load(open(ROOT + r"\data\city_guides.json", encoding="utf-8"))
gz = g.get("广州", {})
tips = gz.get("web_tips") or []
have = {t.get("source") for t in tips}
NEW_TIPS = [
    {"title": "8月广州旅游不踩坑！景点红黑榜一篇搞定", "snippet": "8月下旬广州游玩红黑榜（Trip.com）", "source": "https://tw.trip.com/moments/detail/guangzhou-152-150728152/"},
    {"title": "玩玩玩学学学！开学前来广州，『广』开眼界", "snippet": "广州市政府官方 8 月游学攻略", "source": "https://www.gz.gov.cn/zt/zzyyzq/wlzx/content/post_10965889.html"},
    {"title": "8-9月来广州？本地人教你这样玩！", "snippet": "本地人视角：人少景美还省钱", "source": "https://tw.trip.com/moments/detail/guangzhou-152-150546607/"},
    {"title": "广州5天4晚不走冤枉路！老城烟火+长隆+山野", "snippet": "5天4晚行程全安排", "source": "https://tw.trip.com/moments/detail/guangzhou-152-150573564/"},
    {"title": "广州本地人私藏一日游攻略｜海珠区逛吃不踩雷", "snippet": "海珠区一日游（演出场馆同区）", "source": "https://tw.trip.com/moments/detail/guangzhou-152-150625952/"},
    {"title": "2026王晰「回」个人巡回音乐会·广州（票务页）", "snippet": "2026-08-23 广东艺术剧院 19:30 开票在售", "source": "https://www.yanchupiaowu.com/event.html?id=VGl6QWhKbDVjbTVIR1U2dWlCUW1rQT09"},
    {"title": "2026王晰「回」个人巡回音乐会·广州（豆瓣活动页）", "snippet": "演出活动详情", "source": "https://www.douban.com/event/37949806/"},
    {"title": "2026年8月营业性演出行政许可（广州市文旅局）", "snippet": "官方许可公示（2026.8.6-8.12 批次）", "source": "http://wglj.gz.gov.cn/xxgk/bmwj/ywxx/wgl/content/post_10965083.html"},
]
n = 0
for t in NEW_TIPS:
    if t["source"] not in have:
        tips.append(t)
        have.add(t["source"])
        n += 1
gz["web_tips"] = tips
g["广州"] = gz
json.dump(g, open(ROOT + r"\data\city_guides.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("[1] 广州 web_tips 新增 %d 条，现有 %d 条" % (n, len(tips)))

# 2. live/hui-回-广州-2026.html 加「8月23日去广州玩什么」GEO 区块
p = ROOT + r"\live\hui-回-广州-2026.html"
h = open(p, encoding="utf-8").read()
BLOCK = """
    <section id="gz-august-play" style="margin-top:36px;">
        <h2>8月23日去广州玩什么？</h2>
        <p>如果这个周末你正好在广州——<strong>晚上 19:30 到广东艺术剧院看王晰「回」个人巡回音乐会广州站</strong>（六巡第二场，地址：广州市越秀区广州大道中1229号，近五羊邨/杨箕地铁站），白天可以这样安排：</p>
        <ul>
            <li><strong>白天逛越秀老城</strong>：剧院所在的越秀区就有北京路步行街、越秀公园（镇海楼/五羊石像）、陈家祠，步行可达，无需远行。</li>
            <li><strong>下午顺珠江岸线</strong>：沙面岛、大元帅府、二沙岛艺术公园都在 3 公里范围内，日落前走到剧院正合适。</li>
            <li><strong>演出前吃饭</strong>：天河/东山口老字号早茶（白天鹅、陶陶居、广州酒家）或越秀本地糖水铺，散场后步行到杨箕宵夜街。</li>
            <li><strong>深度玩法</strong>：广州市政府官方「开学前游广州」攻略：<a href="https://www.gz.gov.cn/zt/zzyyzq/wlzx/content/post_10965889.html" target="_blank" rel="noopener nofollow">『广』开眼界 →</a>；8月广州避坑红黑榜：<a href="https://tw.trip.com/moments/detail/guangzhou-152-150728152/" target="_blank" rel="noopener nofollow">Trip.com 攻略 →</a></li>
        </ul>
        <p style="font-size:13px;color:#777;">🛎️ 观演贴士：广东艺术剧院距珠江新城约 4 公里；19:30 开演，建议 18:45 前入场；附近地铁 5 号线五羊邨站、1/5 号线杨箕站。票务：广东艺术剧院、大麦、猫眼。</p>
    </section>
"""
MARKER = "</body>"
if "8月23日去广州玩什么" not in h:
    h = h.replace(MARKER, BLOCK + "\n" + MARKER, 1)
    open(p, "w", encoding="utf-8").write(h)
    print("[2] 广州实录页已加「8月23日去广州玩什么」GEO 区块")
else:
    print("[2] 区块已存在")
