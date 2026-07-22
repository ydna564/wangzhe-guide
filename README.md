<div align="center">

# 🎮 王者荣耀 · 数据驱动游戏指南

**爬取国内多平台数据，自动分析英雄 / 装备强度，生成 2 · 3 · 5 人阵容搭配指南**

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Season](https://img.shields.io/badge/版本-S44-e63946)
![Data](https://img.shields.io/badge/数据-近3个月内-2a9d8f)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/官方·B站·攻略站-已跑通-success)

一条命令跑通「**采集 → 分析 → 出指南**」，梯度随版本自动更新。

</div>

---

## ✨ 特性

- 🕸️ **四源采集**：官方接口 + B站 + 攻略站 + 小红书，每个源用最合适的爬虫（见下表）
- 🛡️ **实战级反爬**：B站 WBI 签名 + buvid 绕风控、小红书持久登录态、真实浏览器指纹
- 📊 **数据驱动分析**：英雄综合强度、装备类型内梯度、阵容按当前梯度动态生成
- ⏱️ **时效性保证**：所有来源锁定**近 3 个月内**，B站自动过滤老视频，梯度带来源日期
- 🔁 **换赛季零改代码**：只改一个 `tier_current.json`，英雄榜 / 阵容全部自动跟着变
- 📄 **一键出稿**：产物是一份结构化 Markdown 指南 [`guide/王者荣耀指南.md`](guide/王者荣耀指南.md)

---

## 🚀 快速开始

```bash
git clone https://github.com/ydna564/wangzhe-guide.git
cd wangzhe-guide

python3 -m venv .venv && source .venv/bin/activate
pip install curl_cffi crawl4ai        # 官方源零依赖；这俩给 B站/攻略站
crawl4ai-setup                        # 装 chromium 内核（首次一次）

python run.py                         # 采集 → 分析 → 生成指南
```

| 命令 | 作用 |
|---|---|
| `python run.py` | 全流程（能公开抓的都抓） |
| `python run.py --no-crawl` | 跳过采集，只用已有数据重新分析出稿 |
| `python run.py --with-xhs` | 额外抓小红书（需先登录，见下） |

---

## 🕸️ 数据源与爬虫选型

| 源 | 爬虫 | 状态 | 说明 |
|---|---|:---:|---|
| **官方** pvp.qq.com | 标准库 requests | ✅ | 131 英雄 + 121 装备，纯公开 JSON，无反爬 |
| **B站** 攻略视频 | `curl_cffi` | ✅ | 指纹 + WBI签名 + buvid绕风控，近90天视频热度 |
| **攻略站** 7724 | `crawl4ai` | ✅ | 抓分路梯度榜，转 markdown 解析 T 榜 |
| **小红书** 攻略笔记 | `Playwright` | ✅ 需登录 | 持久登录态；选择器已对真实 DOM 验证 |

> **为什么这么选**：官方源最干净做地基；B站有公开 API（已解决 403+风控）；攻略站用
> crawl4ai 转 markdown；小红书反爬最强用真实浏览器。scrapy/crawlee 这类工业框架对本项目
> 量级过重，未采用。

---

## 🛡️ 反爬是怎么绕过的

<details>
<summary><b>B站</b>：403 + v_voucher 风控 + WBI 签名（点开看）</summary>

1. `curl_cffi` 用 `impersonate="chrome124"` 伪造真实 TLS/JA3 指纹 → 过 403；
2. 访问首页 + `/frontend/finger/spi` 补 `buvid3/buvid4` cookie → 过 `v_voucher` 风控软拦截；
3. 完整实现 **WBI 签名**（nav 取密钥 + 固定置换表 + md5）→ 搜索接口鉴权；
4. 每关键词换新 session + 无空格关键词 + 退避重试 → 稳定不被限流。

登录后更全：`export BILI_SESSDATA=你的cookie` 再跑。
</details>

<details>
<summary><b>小红书</b>：搜索需登录，扫码一次复用（点开看）</summary>

搜索结果需登录，扫码只能你自己做：
```bash
python crawlers/xiaohongshu.py login    # 有头浏览器扫码，登录态存进 ~/.wzry_xhs_profile
python run.py --with-xhs                 # 复用登录态抓取，热度自动并入分析
```
选择器（`section.note-item` / `.title` / `.author .name` / `.like-wrapper .count`）已对真实
DOM 验证；提取 + 点赞解析 + 英雄匹配管道已跑通，唯一缺口是登录态。
</details>

---

## 🧮 分析口径

**英雄强度**　`综合分 = 0.6 × 梯度分 + 0.4 × 社区热度`
- 梯度分优先级：`tier_current.json`（当前 S44 核对榜）> crawl4ai 抓取 > 兜底种子
- T 级分：`T0=100 / T0.5=90 / T1=78 / T2=60 / T3=45 / T4=30`
- 社区热度 = B站 + 小红书 标题提及 × log(播放/点赞) 加权

**装备梯度**　按**类型**（攻击/法术/防御/移动/打野/游走）做类型内梯度，不给分定位出装
- 梯度分 = 类型内成型价值 + **S44 装备改动加权**（加强 +15 / 削弱 −22）+ 热度
- 成品分 `T0/T1/T2`，小件单列；版本加强 ↑ / 削弱 ↓ 直接标注

**阵容**　模板给打法思路 + 各分路建议英雄，按当前梯度**动态校正**
- 建议英雄跌出该分路前 4 名 → 自动替换为当前最强（指南标 `←原英雄`）
- 阵容强度 = 成员综合分均值，附版本替补

---

## ⏱️ 数据时效性

所有来源锁定**近 3 个月内**（当前 **S44 赛季**）：

| 数据 | 时效保证 |
|---|---|
| 官方英雄/装备 | 实时接口，每次跑都是最新 |
| B站热度 | `MAX_AGE_DAYS=90` 只保留近 90 天视频（实测 100% 达标） |
| 分路梯度 | `data/tier_current.json`，各分路带 `_manifest` 来源 URL + 日期 |
| 装备改动 | `baseline.ITEM_CHANGE`，S44 调整公告 2026-06-18 |

**换赛季刷新**（约每 1~2 个月）：搜「王者荣耀 sXX 各分路 T0 梯度」→ 更新
`data/tier_current.json` → `python run.py --no-crawl`。英雄榜、阵容全部自动跟着变。

---

## 🗂️ 目录结构

```
wangzhe-guide/
├── run.py                  # 一键编排（--no-crawl / --with-xhs）
├── config.py               # 路径 / 角色映射 / 数据源清单
├── crawlers/
│   ├── official_pvp.py     # ✅ 官方英雄 + 装备
│   ├── bilibili.py         # ✅ B站攻略热度（指纹+WBI+风控绕过）
│   ├── strategy_sites.py   # ✅ crawl4ai 攻略站梯度
│   └── xiaohongshu.py      # ✅ Playwright 小红书（需登录）
├── analysis/
│   ├── baseline.py         # 兜底种子 / S44装备改动 / 阵容模板
│   ├── hero_strength.py    # 官方 + 社区热度 + 梯度 → 综合强度
│   ├── equipment.py        # 装备按类型做类型内梯度
│   ├── team_comps.py       # 2/3/5 人阵容（按当前梯度动态校正）
│   └── generate_guide.py   # 汇总出 Markdown 指南
├── data/
│   ├── tier_current.json   # ⭐ 当前赛季梯度（换赛季只改这个）
│   ├── raw/                # 原始抓取
│   └── processed/          # 清洗后
└── guide/王者荣耀指南.md    # 📄 最终产物
```

---

## ⚠️ 免责声明

- 本项目仅供**个人学习研究**。抓取小红书 / B站 违反其 ToS 且有反爬，请用小号、控频率，风险自负。
- 梯度数据来自公开攻略文章，随版本变化，仅供参考，不代表官方或作者立场。
- 请勿用于商业用途或大规模抓取。

## 📄 License

MIT
