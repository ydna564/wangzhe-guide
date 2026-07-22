# -*- coding: utf-8 -*-
"""装备分析 —— 官方装备按【类型】分组，做类型内梯度。

不再给分定位核心出装；而是每个装备类型(攻击/法术/防御/移动/打野/游走)
内部对成品装排梯度。梯度分 = 类型内价格归一(成型价值) + S44改动加权
(加强↑/削弱↓) + B站热度，尽量贴近当前版本核心度。小件(合成件)单列。
"""
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_RAW, DATA_PROCESSED
from analysis.baseline import ITEM_CHANGE

ITEM_TYPE = {1: "攻击", 2: "法术", 3: "防御", 4: "移动", 5: "打野", 6: "游走", 7: "装备"}
FINAL_MIN_PRICE = 1500        # 成品装价格门槛（低于且无被动视为合成小件）


def _item_heat(names):
    """B站视频标题里提到的装备名次数（装备热度，通常稀疏）。"""
    vids = _load("bilibili_videos") or {}
    heat = Counter()
    titles = [v.get("title", "") for lst in vids.values() for v in lst]
    for t in titles:
        for n in names:
            if len(n) >= 2 and n in t:
                heat[n] += 1
    return heat


def _load(name):
    p = DATA_RAW / f"{name}.json"
    return json.load(open(p, encoding="utf-8")) if p.exists() else None


def _change_flag(name):
    for b in ITEM_CHANGE["buff"]:
        if b in name:
            return "buff"
    for n in ITEM_CHANGE["nerf"]:
        if n in name:
            return "nerf"
    return None


def analyze():
    items = _load("items") or []
    names = [it["name"] for it in items]
    heat = _item_heat(names)
    max_heat = max(heat.values()) if heat else 1

    by_type = defaultdict(list)
    for it in items:
        by_type[ITEM_TYPE.get(it.get("type"), "其他")].append(it)

    result = {}
    for typ, its in by_type.items():
        finals = [it for it in its
                  if (it.get("total_price") or 0) >= FINAL_MIN_PRICE and it.get("passive")]
        smalls = [it["name"] for it in its if it not in finals]

        # 鞋子/小类型：成品太少就不强分档，整体列一档
        prices = [it["total_price"] for it in finals] or [1]
        pmin, pmax = min(prices), max(prices)
        scored = []
        for it in finals:
            span = (pmax - pmin) or 1
            price_norm = 100 * (it["total_price"] - pmin) / span     # 类型内成型价值
            flag = _change_flag(it["name"])
            adj = 15 if flag == "buff" else (-22 if flag == "nerf" else 0)
            h = 12 * heat.get(it["name"], 0) / max_heat
            sc = round(price_norm + adj + h, 1)
            scored.append({"name": it["name"], "price": it["total_price"],
                           "change": flag, "score": sc})
        scored.sort(key=lambda x: x["score"], reverse=True)

        # 按分数分档（成品多才分 T0/T1/T2，少则单档）
        tiers = {}
        n = len(scored)
        if n >= 6:
            cut0, cut1 = max(1, n // 4), max(2, n // 2)
            tiers["T0"] = scored[:cut0]
            tiers["T1"] = scored[cut0:cut1]
            tiers["T2"] = scored[cut1:]
        elif n:
            tiers["核心"] = scored
        result[typ] = {"tiers": tiers, "smalls": smalls, "final_count": n}

    out = {"by_type": result, "item_count": len(items),
           "change": ITEM_CHANGE}
    json.dump(out, open(DATA_PROCESSED / "equipment.json", "w",
              encoding="utf-8"), ensure_ascii=False, indent=2)
    return out


if __name__ == "__main__":
    res = analyze()
    print(f"装备总数 {res['item_count']}｜S44改动: 加强 "
          f"{res['change']['buff']}｜削弱 {res['change']['nerf']}\n")
    for typ in ["攻击", "法术", "防御", "打野"]:
        d = res["by_type"].get(typ, {})
        print(f"== {typ}（成品{d.get('final_count',0)}件）==")
        for tier, lst in d.get("tiers", {}).items():
            tag = lambda x: ("↑" if x["change"] == "buff" else "↓" if x["change"] == "nerf" else "")
            print(f"  {tier}: " + "、".join(f"{x['name']}{tag(x)}" for x in lst))
