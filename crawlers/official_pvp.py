# -*- coding: utf-8 -*-
"""官方数据爬虫 —— 王者荣耀官网 pvp.qq.com 的公开 JSON 接口。

无需登录、无反爬，是所有分析的地基层：
  - 英雄列表 + 定位(roles)
  - 装备属性 + 价格
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import ROLE_MAP
from crawlers.base import fetch_json, save_raw

HERO_URL = "https://pvp.qq.com/web201605/js/herolist.json"
ITEM_URL = "https://pvp.qq.com/web201605/js/item.json"

_TAG = re.compile(r"<[^>]+>")


def _clean(html):
    return _TAG.sub(" ", html or "").replace("&nbsp;", " ").strip()


def crawl_heroes():
    raw = fetch_json(HERO_URL)
    heroes = []
    for h in raw:
        roles = [ROLE_MAP.get(r, r) for r in str(h.get("roles", "")).split("|") if r]
        heroes.append({
            "ename": h["ename"],
            "name": h["cname"],
            "id_name": h.get("id_name"),
            "title": h.get("title"),
            "roles": roles,                      # 如 ["坦克","辅助"]
            "primary_role": roles[0] if roles else None,
            "skin_count": len(str(h.get("skin_name", "")).split("|")),
        })
    save_raw("heroes", heroes)
    return heroes


def crawl_items():
    raw = fetch_json(ITEM_URL)
    items = []
    for it in raw:
        items.append({
            "item_id": it["item_id"],
            "name": it["item_name"],
            "type": it.get("item_type"),         # 1攻击 2法术 3防御 ...
            "price": it.get("price"),
            "total_price": it.get("total_price"),
            "desc": _clean(it.get("des1")),
            "passive": _clean(it.get("des2")),
        })
    save_raw("items", items)
    return items


if __name__ == "__main__":
    hs = crawl_heroes()
    its = crawl_items()
    print(f"[官方] 英雄 {len(hs)} 个，装备 {len(its)} 件，已存 data/raw/")
    from collections import Counter
    c = Counter(h["primary_role"] for h in hs)
    print("主定位分布:", dict(c))
