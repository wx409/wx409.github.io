#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""接管调试浏览器：注入 XHR/fetch 钩子 → 刷新 → 滚动 → 读 window.__ids。"""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

IDS_TXT = Path(r"E:\wx\论文素材_王晰作传\抖音\video_ids.txt")
META = Path(r"E:\wx\论文素材_王晰作传\抖音\cdp_collect.json")

HOOK = r"""
window.__ids = new Set();
window.__api = 0;
(function(){
  function take(url, text){
    try{
      if(!url || url.indexOf('aweme/post') < 0) return;
      window.__api++;
      const j = JSON.parse(text);
      window.__aw = window.__aw || {};
      (j.aweme_list||[]).forEach(a=>{
        if(!a.aweme_id) return;
        const id = String(a.aweme_id);
        window.__ids.add(id);
        const v = a.video || {};
        const pa = (v.play_addr || {});
        const urls = (pa.url_list || []).filter(Boolean);
        window.__aw[id] = {
          desc: (a.desc || '').slice(0, 120),
          ct: a.create_time || 0,
          dur: (v.duration || 0) / 1000,
          url: urls[0] || ''
        };
      });
      window.__hasMore = j.has_more;
    }catch(e){}
  }
  const of = window.fetch;
  window.fetch = async function(...a){
    const r = await of.apply(this, a);
    try{ const u=(a[0]&&a[0].url)||a[0]||''; if(String(u).indexOf('aweme/post')>=0){
      const t = await r.clone().text(); take(String(u), t);} }catch(e){}
    return r;
  };
  const op = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(m,u){ this.__u=u; return op.apply(this,arguments); };
  const sd = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function(){
    const self=this;
    this.addEventListener('load', ()=>{ try{ take(String(self.__u||''), self.responseText); }catch(e){} });
    return sd.apply(this, arguments);
  };
})();
"""


def main() -> int:
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = b.contexts[0]
        ctx.add_init_script(HOOK)
        pg = next((x for x in ctx.pages if "douyin.com" in x.url), None) or ctx.new_page()
        print("载入:", pg.url[:70])
        pg.reload(wait_until="domcontentloaded", timeout=90000)
        time.sleep(5)

        for round_i in range(150):
            n = pg.evaluate("window.__ids ? window.__ids.size : -1")
            if round_i % 5 == 0:
                print(f"  轮{round_i}: 累计 {n}｜api 命中 {pg.evaluate('window.__api||0')}")
            if isinstance(n, int) and n >= 190:
                break
            pg.mouse.wheel(0, 2800)
            try:
                pg.evaluate('''() => {
                  const els=[...document.querySelectorAll('div')]
                    .filter(d=>d.scrollHeight>d.clientHeight+300);
                  els.forEach(d=>{ d.scrollTop = d.scrollHeight; });
                  window.scrollTo(0, document.body.scrollHeight);
                }''')
            except Exception:
                pass
            time.sleep(1.7)
            if round_i % 10 == 9:
                pg.keyboard.press("End")
                time.sleep(1.5)

        ids = pg.evaluate("window.__ids ? [...window.__ids] : []")
        aw = pg.evaluate("window.__aw || {}")
        more = pg.evaluate("window.__hasMore === undefined ? null : window.__hasMore")
        IDS_TXT.write_text("\n".join(ids) + "\n", encoding="utf-8")
        Path(r"E:\wx\论文素材_王晰作传\抖音\awemes.json").write_text(
            json.dumps(aw, ensure_ascii=False, indent=1), encoding="utf-8")
        META.write_text(json.dumps({"count": len(ids), "has_more": more,
                                    "api_hits": pg.evaluate("window.__api||0"),
                                    "at": time.strftime("%Y-%m-%d %H:%M")},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n共 {len(ids)} 个 ID｜has_more={more} → {IDS_TXT}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
