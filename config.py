# -*- coding: utf-8 -*-
"""王者指南 全局配置：路径、角色映射、数据源清单。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
GUIDE_DIR = ROOT / "guide"

for _d in (DATA_RAW, DATA_PROCESSED, GUIDE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# 官方 herolist 的 roles 字段编码 -> 分路/定位
ROLE_MAP = {
    "1": "坦克",
    "2": "战士",
    "3": "刺客",
    "4": "法师",
    "5": "射手",
    "6": "辅助",
}

# 分路（用于阵容搭配的站位约束）
LANE_MAP = {
    "对抗路": ["战士", "坦克"],
    "中路": ["法师"],
    "发育路": ["射手"],
    "打野": ["刺客", "战士"],
    "游走": ["辅助", "坦克"],
}

# 数据源清单：每个源标注 采集方式 / 是否需要登录 / 使用的爬虫
SOURCES = {
    "official_pvp": {
        "name": "王者荣耀官网(pvp.qq.com)",
        "crawler": "requests",          # 纯公开 JSON，无需第三方
        "needs_login": False,
        "public": True,
        "provides": ["英雄列表", "装备属性", "英雄定位"],
    },
    "strategy_sites": {
        "name": "攻略站梯度榜(18183/玩加电竞等)",
        "crawler": "crawl4ai",
        "needs_login": False,
        "public": True,
        "provides": ["英雄梯度T榜", "出装推荐", "版本强势"],
    },
    "bilibili": {
        "name": "B站(攻略视频/评论区)",
        "crawler": "curl_cffi",         # 模拟 Chrome 指纹调公开 API
        "needs_login": False,           # 搜索/评论公开可读，登录后更全
        "public": True,
        "provides": ["UP主版本评测", "阵容口碑", "热度"],
    },
    "xiaohongshu": {
        "name": "小红书(攻略笔记/阵容图)",
        "crawler": "browser-use",       # 需登录 + 反爬，真人式操作
        "needs_login": True,
        "public": False,
        "provides": ["实战阵容", "上分攻略", "笔记热度"],
    },
}

# 常用 User-Agent（curl_impersonate / curl_cffi 会覆盖成真实指纹）
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
