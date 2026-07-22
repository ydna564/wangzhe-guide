# -*- coding: utf-8 -*-
"""英雄强度分析 —— 融合三路信号打分：

  1) 官方 herolist（英雄名 + 定位）—— 地基
  2) B站热度（攻略视频标题提及次数 × 播放量权重）—— 版本讨论度
  3) baseline.TIER_SEED（人工/攻略站梯度）—— 强度基准

综合分 = 0.6 × 基线梯度分 + 0.4 × 归一化B站热度分
输出每个英雄的  {定位, 综合分, T级, 热度}，并给出各定位榜单。
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_RAW, DATA_PROCESSED
from analysis.baseline import TIER_SEED, TIER_SCORE


def _load(name):
    p = DATA_RAW / f"{name}.json"
    return json.load(open(p, encoding="utf-8")) if p.exists() else None


def community_heat(hero_names):
    """社区热度 = B站视频标题提及(播放加权) + 小红书笔记标题提及(点赞加权)。
    两个源都可缺省；小红书需登录后才有数据（见 crawlers/xiaohongshu.py）。"""
    heat = Counter()

    # B站：标题提及 × log播放加权
    for lst in (_load("bilibili_videos") or {}).values():
        for v in lst:
            title = v.get("title", "")
            w = 1 + math.log10((v.get("play") or 0) + 10) / 4
            for n in hero_names:
                if n in title:
                    heat[n] += w

    # 小红书：标题提及 × log点赞加权（已抽好的 heroes 字段优先）
    for lst in (_load("xiaohongshu_notes") or {}).values():
        for note in (lst or []):
            title = note.get("title", "")
            w = 1 + math.log10((note.get("likes") or 0) + 10) / 4
            hit = note.get("heroes") or [n for n in hero_names if n in title]
            for n in hit:
                heat[n] += w

    return heat


def tier_source():
    """梯度数据优先级：
       1) data/tier_current.json —— 人工核对、带来源日期的当前赛季 T 榜（最新）
       2) data/raw/strategy_tier.json —— crawl4ai 抓取解析（结构化页可自动更新）
       3) baseline.TIER_SEED —— 兜底人工种子
    """
    from config import ROOT
    cur = ROOT / "data" / "tier_current.json"
    if cur.exists():
        data = json.load(open(cur, encoding="utf-8"))
        mf = data.get("_manifest", {})
        label = f"{mf.get('season','?')}·核对榜({mf.get('generated','?')})"
        return data, label
    scraped = _load("strategy_tier")
    if scraped:
        return scraped, "攻略站(7724·抓取)"
    return TIER_SEED, "人工基线种子"


def tier_lookup():
    """英雄 -> (分路, T级, 梯度分)。一个英雄可能出现在多分路，取最高分。"""
    tiers_by_lane, _src = tier_source()
    table = {}
    for lane, tiers in tiers_by_lane.items():
        if lane.startswith("_"):          # 跳过 _manifest 等元数据
            continue
        for tier, names in tiers.items():
            for n in names:
                score = TIER_SCORE.get(tier, 50)
                if n not in table or score > table[n][2]:
                    table[n] = (lane, tier, score)
    return table


def analyze():
    heroes = _load("heroes") or []
    names = [h["name"] for h in heroes]
    heat = community_heat(names)
    max_heat = max(heat.values()) if heat else 1
    tiers = tier_lookup()

    rows = []
    for h in heroes:
        n = h["name"]
        role, tier, base = tiers.get(n, (h.get("primary_role"), None, 40))
        heat_raw = heat.get(n, 0)
        heat_norm = 100 * heat_raw / max_heat if max_heat else 0
        composite = round(0.6 * base + 0.4 * heat_norm, 1)
        rows.append({
            "name": n,
            "role": role,
            "official_role": h.get("primary_role"),
            "tier_seed": tier,
            "base_score": base,
            "heat_mentions": round(heat_raw, 2),
            "heat_norm": round(heat_norm, 1),
            "score": composite,
        })
    rows.sort(key=lambda r: r["score"], reverse=True)

    # 分定位榜
    by_role = defaultdict(list)
    for r in rows:
        by_role[r["role"]].append(r)
    for role in by_role:
        by_role[role].sort(key=lambda r: r["score"], reverse=True)

    _tiers, src = tier_source()
    out = {"ranking": rows, "by_role": by_role,
           "tier_by_lane": _tiers, "tier_source": src,
           "hot_heroes": [n for n, _ in heat.most_common(15)]}
    json.dump(out, open(DATA_PROCESSED / "hero_strength.json", "w",
              encoding="utf-8"), ensure_ascii=False, indent=2)
    return out


if __name__ == "__main__":
    res = analyze()
    print("=== 综合强度 TOP15 ===")
    for r in res["ranking"][:15]:
        print(f"  {r['name']:<6} {r['role'] or '-':<5} "
              f"T:{r['tier_seed'] or '-':<3} 分:{r['score']:<6} 热度:{r['heat_norm']}")
    print("\n版本热议英雄:", " ".join(res["hot_heroes"][:12]))
