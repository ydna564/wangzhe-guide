# -*- coding: utf-8 -*-
"""攻略站爬虫 —— 用 crawl4ai 抓分路英雄梯度榜并解析成结构化 T 榜。

crawl4ai 免费、渲染 JS、出干净 markdown。7724 的梯度页结构稳定：
    **对抗路**
    T0：元歌、杨戬、夏洛特。
    T1：马超、蒙恬、...
直接正则解析出  {分路: {T级: [英雄]}}，用来覆盖 baseline 的人工种子。

依赖:  pip install crawl4ai  &&  crawl4ai-setup
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from crawlers.base import save_raw

# 梯度榜源。注意两种排版：
#   A. 合并页(如 S43 的 226360)：`Tx：英雄、英雄。` 规整列表 —— 本解析器能自动解析
#   B. 分路单篇(当前 S44)：`**T0**` + 散文描述 —— 结构不统一，确定性解析不可靠
# 因此【当前赛季的权威梯度以人工核对的 data/tier_current.json 为准】（近3个月内来源+日期），
# 本爬虫作为「结构化合并页」的自动解析通道保留；换赛季若出现合并页可直接换 URL 自动更新。
TARGETS = [
    # 当前 S44 分路源（散文排版，解析有限；权威数据见 data/tier_current.json）：
    "http://m.7724.com/wzry/news/230038.html",   # S44 对抗路 2026-06-26
    "http://m.7724.com/wzry/news/230370.html",   # S44 中路   2026-06-29
    "http://m.7724.com/wzry/news/230056.html",   # S44 辅助   2026-06-26
    "http://www.7724.com/wzry/news/229578.html",  # S44 射手   2026-06-23
]


def _official_names():
    import json
    from config import DATA_RAW
    p = DATA_RAW / "heroes.json"
    if not p.exists():
        return set()
    return {h["name"] for h in json.load(open(p, encoding="utf-8"))}


_OFFICIAL = _official_names()

LANES = ["对抗路", "打野", "中路", "发育路", "游走", "辅助", "发育", "中单", "上单"]
LANE_NORM = {"发育": "发育路", "中单": "中路", "上单": "对抗路", "辅助": "游走"}
TIER_RE = re.compile(r"(T0\.5|T[0-4])\s*[:：]\s*([^\n。]+)")
LANE_RE = re.compile(r"\*{0,2}(" + "|".join(LANES) + r")\*{0,2}\s*$")
SPLIT = re.compile(r"[、,，/]\s*")


def _clean_hero(name):
    name = re.sub(r"\(.*?\)|（.*?）", "", name)      # 去掉 (刺客) 等括注
    name = re.sub(r"[_\s\d\.]+", "", name)
    return name.strip()


def parse_tier(markdown):
    """从 markdown 解析 {分路: {T级: [英雄]}}。"""
    lines = [l.strip() for l in markdown.splitlines() if l.strip()]
    result = {}
    cur_lane = None
    for l in lines:
        m = LANE_RE.match(l)
        if m:
            cur_lane = LANE_NORM.get(m.group(1), m.group(1))
            result.setdefault(cur_lane, {})
            continue
        tm = TIER_RE.search(l)
        if tm and cur_lane:
            tier = tm.group(1)
            heroes = [_clean_hero(h) for h in SPLIT.split(tm.group(2)) if h.strip()]
            # 单字英雄名(镜/澜/曜/影)需在官方名单里才保留，避免解析噪声；
            # 多字名放宽（可能有官方名单还没收录的新英雄）。
            heroes = [h for h in heroes
                      if (2 <= len(h) <= 6) or (h in _OFFICIAL)]
            if heroes:
                result[cur_lane].setdefault(tier, [])
                for h in heroes:
                    if h not in result[cur_lane][tier]:
                        result[cur_lane][tier].append(h)
    return {k: v for k, v in result.items() if v}


async def crawl_async(targets=TARGETS):
    from crawl4ai import (AsyncWebCrawler, BrowserConfig,
                          CrawlerRunConfig, CacheMode)
    merged = {}
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        for url in targets:
            try:
                res = await crawler.arun(
                    url=url,
                    config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS,
                                            page_timeout=30000))
                if not res.success:
                    print(f"[攻略站] {url} 抓取失败")
                    continue
                parsed = parse_tier(res.markdown.raw_markdown)
                n = sum(len(hs) for t in parsed.values() for hs in t.values())
                print(f"[攻略站] {url.split('/')[-1]} -> {len(parsed)}路 {n}英雄")
                # 合并（先到为准，后到补充）
                for lane, tiers in parsed.items():
                    merged.setdefault(lane, {})
                    for tier, hs in tiers.items():
                        merged[lane].setdefault(tier, [])
                        for h in hs:
                            if all(h not in v for v in merged[lane].values()):
                                merged[lane][tier].append(h)
            except Exception as e:                    # noqa: BLE001
                print(f"[攻略站] {url} 异常: {e}")
    if merged:
        save_raw("strategy_tier", merged)
    return merged


def crawl(targets=TARGETS):
    return asyncio.run(crawl_async(targets))


if __name__ == "__main__":
    try:
        import crawl4ai  # noqa: F401
    except ImportError:
        print("未安装 crawl4ai。请先:  pip install crawl4ai && crawl4ai-setup")
        sys.exit(1)
    r = crawl()
    for lane, tiers in r.items():
        print(f"\n{lane}:")
        for tier in ["T0", "T0.5", "T1", "T2", "T3", "T4"]:
            if tier in tiers:
                print(f"  {tier}: {'、'.join(tiers[tier])}")
