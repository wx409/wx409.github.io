# -*- coding: utf-8 -*-
"""把「现场稳定性」一节插进 analysis-v2.html（幂等）。

python 进程写不进 dashboard/（ACL），所以：读原文件 → 写 analysis/out/analysis-v2.html → PowerShell 复制回去。
"""
from pathlib import Path

SITE = Path(r"D:\wx409.github.io")
SRC = SITE / "dashboard" / "analysis-v2.html"
TMP = Path(__file__).resolve().parent / "out" / "analysis-v2.html"

SECTION = """  <h2>五、现场能撑到什么程度</h2>
  <p class="q">问：同一首歌在不同场次，最低音抖多少？这算「稳」吗？</p>
  <div id="c5" class="chart" style="height:420px"></div>
  <div class="take" id="t5"></div>
  <p class="note">只看「一首歌 × 一场」的记录（剔除整场合计与缺曲名），同一场重复测量取中位，每曲至少 4 场。波动用半音表示，
    1 个半音 = 100 音分。测量噪声只会让波动<b>变大</b>，所以「波动小」是保守结论：它不可能被噪声伪造。</p>

"""

TAKE = """  document.getElementById("t5").innerHTML = (() => {
    const L = voc.live_stability, det = (L.detail || []).filter(x => x.sessions >= 4).sort((a,b) => a.sd_semitone - b.sd_semitone);
    const stable = det.filter(x => x.sd_semitone < 1);
    const c5 = echarts.init(document.getElementById("c5"));
    c5.setOption({
      grid:{left:118,right:56,top:20,bottom:34},
      tooltip:{trigger:"item",formatter:p=>{const x=det[p.dataIndex];return `${x.song}<br>场次 ${x.sessions}｜中位最低音 ${x.median_hz}Hz<br>跨场波动 ${x.sd_semitone} 半音（极差 ${x.range_semitone}）`}},
      xAxis:{type:"value",name:"跨场波动（半音）",max:4,nameTextStyle:{color:"#9ca3af"},...axis},
      yAxis:{type:"category",data:det.map(x=>x.song),...axis},
      series:[{type:"bar",data:det.map(x=>({value:x.sd_semitone,itemStyle:{color:x.sd_semitone<1?"#6fbf8f":"#5bc2e7"}})),
        label:{show:true,position:"right",color:"#9ca3af",fontSize:11,formatter:p=>p.value.toFixed(2)},
        markLine:{silent:true,symbol:"none",label:{formatter:"1 半音",color:"#9ca3af",fontSize:11},
          data:[{xAxis:1,lineStyle:{color:"#f2d98d",type:"dashed"}}]}}]
    });
    document.getElementById("t5").innerHTML = `<b>整体还不足以下「稳」的结论，但有个别曲目站得住。</b>
      25 首可比的曲目里，同曲跨场波动中位 ${fmt(L.sd.median,2)} 半音（≈${Math.round(L.sd.median*100)} 音分），
      曲目间差异只占总方差的 ${Math.round(L.icc.icc*100)}%（ICC ${fmt(L.icc.icc,2)}，95% CI ${fmt(L.icc_ci[0],2)}–${fmt(L.icc_ci[1],2)}）——
      大部分波动来自音源与扩声，不是唱功。
      但 ${stable.length} 首在 4 场以上仍把波动压在 1 个半音以内：${stable.map(x=>`${x.song}（${x.sessions} 场 ${fmt(x.sd_semitone,2)}）`).join("、")}。
      其中波动最小的一首跨 ${stable[0]?stable[0].sessions:0} 场仅 ${stable[0]?fmt(stable[0].sd_semitone,2):"–"} 半音。
      要把它变成可发布的「唱功」结论，需要电台/官方音源或固定扩声条件的录音，把测量噪声压下去。`;
    return "";
  })();
"""

CARD = """    <div class="card"><div class="num">${(voc.live_stability.detail||[]).filter(x=>x.sessions>=4&&x.sd_semitone<1).length}<small> / ${(voc.live_stability.detail||[]).filter(x=>x.sessions>=4).length} 首</small></div>
      <p>4 场以上仍把最低音波动压在 1 个半音（100 音分）以内的曲目——这是现场数据唯一站得住的「稳」</p></div>`;"""


def main():
    html = SRC.read_text(encoding="utf-8")
    if "五、现场能撑到什么程度" in html:
        print("已存在，跳过")
        return
    # 1) 章节：插到「口径与局限」之前，并把它的编号改成六
    anchor = '  <h2>五、口径与局限</h2>'
    assert anchor in html, "找不到口径章节"
    html = html.replace(anchor, SECTION + '  <h2>六、口径与局限</h2>')

    # 2) 第四张结论卡
    card_anchor = '      <p>录音室作品里真正下探到 B1（±50 音分）的曲目数；常规低音在 C2–E♭2</p></div>`;'
    assert card_anchor in html, "找不到第三张卡"
    html = html.replace(card_anchor, card_anchor[:-2] + "\n" + CARD)

    # 3) 图表代码：插在 meta 赋值之前
    js_anchor = '  document.getElementById("meta").textContent ='
    assert js_anchor in html, "找不到 meta"
    html = html.replace(js_anchor, TAKE + js_anchor)

    TMP.parent.mkdir(exist_ok=True)
    TMP.write_text(html, encoding="utf-8")
    print(f"写出 {TMP}（{len(html)} 字符）")


if __name__ == "__main__":
    main()
