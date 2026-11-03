# voice / live 结构性改写 · 回退说明

**改写时间**：2026-11-03
**回退点**：tag `pre-ability-rewrite`（commit `936cb6a7`，改写前最后一次自动部署）

## 一、改了什么

| 文件 | 改动 |
|---|---|
| `voice.html` 生成器 | 把「最低稳定音」为主的三节降为**附一/附二/附三**；重排编号（原四五六七→二三四五） |
| `live.html` 生成器 | 第二节标题改为「稳定性与复现为主」；删掉“现场稳定音 C2 65.3Hz”的举例，换成“跨场极差 0.14 半音” |
| 两页页首 | 注入「能力主线」区块（7 音分 / 0.14 半音 / 14.3 秒 / 3 分贝），数字由 `data/ability_highlights.json` 派生 |
| `deploy_all.py` | 加一步 `inject_ability_blocks.py`（生成后注入，幂等） |

## 二、怎么回退（三选一）

### 方案 A：整体回到改写前（最干净）

```powershell
cd D:\wx409.github.io
git checkout pre-ability-rewrite -- voice.html live.html
git commit -m "回退：voice/live 恢复改写前版本"
git push origin main
```

> 注意：这只回退两个页面。生成器（`generate_voice_page.py`、`build_compact.py`）仍带改动，
> 下次部署会把页面重建回来。所以要连生成器一起回退，用方案 B。

### 方案 B：连生成器一起回退（彻底）

```powershell
cd D:\wx409.github.io
git checkout pre-ability-rewrite -- voice.html live.html
# 生成器不在仓库里，需手动还原
# E:\wx\论文素材_王晰作传\基线口径\generate_voice_page.py 里的编号
# 二→四、三→五、四→六之二、五→七、六→八、附一→二、附二→三、附三→六
# build_compact.py 的 <h2> 与那句"跨场极差"改回
git add -A; git commit -m "回退：页面与生成器一并恢复"; git push origin main
```

### 方案 C：只撤掉页首能力区块

```powershell
cd D:\wx409.github.io
python -c "import re,sys;p='voice.html';s=open(p,encoding='utf-8').read();s=re.sub(r'<!-- ABILITY_START -->.*?<!-- ABILITY_END -->','',s,flags=re.S);open(p,'w',encoding='utf-8').write(s)"
# live.html 同理
git add -A; git commit -m "撤掉能力区块"; git push origin main
```

## 三、回退后要做的

1. `python -X utf8 project_b\build_nav.py`
2. `python -X utf8 project_b\deploy_all.py`
3. `git push origin main`
4. 等 2–3 分钟跑 `python -X utf8 project_b\audit_live.py --wait 180`

## 四、风险提示

- 这次只改了**文案与编号**，没有动数据口径、没有改数字来源；
- 所有数字仍由 `data/ability_highlights.json` 派生，删掉区块不会影响其他页面；
- 审计（audit_caliber / audit_nav / audit_jsonld / audit_live）在部署里已跑过，全绿。
