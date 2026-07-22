# -*- coding: utf-8 -*-
"""生成指南 —— 把 processed 数据汇成一份 Markdown 王者荣耀指南。"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_PROCESSED, GUIDE_DIR


def _load(name):
    p = DATA_PROCESSED / f"{name}.json"
    return json.load(open(p, encoding="utf-8")) if p.exists() else {}


def generate():
    strength = _load("hero_strength")
    equip = _load("equipment")
    comps = _load("team_comps")

    L = []
    src = strength.get("tier_source", "人工基线种子")
    tier_by_lane = strength.get("tier_by_lane", {})
    mf = tier_by_lane.get("_manifest", {})
    season = mf.get("season", "")
    L.append("# 王者荣耀 游戏指南（英雄 · 装备 · 阵容）\n")
    L.append(f"> 自动生成于 {time.strftime('%Y-%m-%d %H:%M')} ｜ "
             f"数据源：官方 pvp.qq.com（英雄/装备）+ 攻略站梯度({src}) + B站攻略热度\n")
    L.append(f"> 梯度来源：**{src}**｜ {mf.get('recency_note','梯度随版本变化，仅供参考。')}\n")
    if mf.get("sources"):
        L.append("> 各分路梯度来源日期："
                 + "；".join(f"{k} {v.get('date','?')}"
                            for k, v in mf["sources"].items()) + "\n")

    # 分路完整梯度榜
    if tier_by_lane:
        L.append(f"\n## ⭐ 分路梯度榜（{season}）\n")
        for lane in ["对抗路", "打野", "中路", "发育路", "游走"]:
            tiers = tier_by_lane.get(lane)
            if not tiers:
                continue
            L.append(f"\n**{lane}**")
            for tier in ["T0", "T0.5", "T1", "T2", "T3", "T4"]:
                if tier in tiers:
                    L.append(f"- `{tier}`：{'、'.join(tiers[tier])}")

    # 1. 英雄强度
    L.append("\n## 一、英雄强度榜\n")
    if strength.get("hot_heroes"):
        L.append(f"**版本热议英雄**（B站攻略视频提及）："
                 f"{'、'.join(strength['hot_heroes'][:12])}\n")
    L.append("\n### 综合强度 TOP20\n")
    L.append("| 排名 | 英雄 | 分路 | T级 | 综合分 | 社区热度 |")
    L.append("|---|---|---|---|---|---|")
    for i, r in enumerate(strength.get("ranking", [])[:20], 1):
        L.append(f"| {i} | {r['name']} | {r['role'] or '-'} | "
                 f"{r['tier_seed'] or '-'} | {r['score']} | {r['heat_norm']} |")

    # 分定位榜
    L.append("\n### 分定位强度榜（各取前6）\n")
    for role in ["对抗路", "打野", "中路", "发育路", "游走"]:
        rows = strength.get("by_role", {}).get(role, [])[:6]
        if rows:
            names = "、".join(f"{r['name']}({r['score']})" for r in rows)
            L.append(f"- **{role}**：{names}")

    # 2. 装备（各类型内梯度）
    L.append("\n\n## 二、装备梯度（按类型）\n")
    ch = equip.get("change", {})
    if ch:
        L.append(f"官方装备库共 **{equip.get('item_count', 0)}** 件。"
                 f"**{ch.get('season','')} 装备改动**（{ch.get('date','')}）："
                 f"加强 {'、'.join(ch.get('buff', []))}；"
                 f"削弱 {'、'.join(ch.get('nerf', []))}。")
        L.append(f"版本趋势：{ch.get('trend','')}\n")
        L.append("> 梯度 = 类型内成型价值 + S44改动加权(↑加强/↓削弱) + 热度；小件为合成件。\n")

    def _mark(x):
        return x["name"] + ("↑" if x["change"] == "buff" else "↓" if x["change"] == "nerf" else "")

    tier_order = ["T0", "T1", "T2", "核心"]
    for typ in ["攻击", "法术", "防御", "打野", "游走", "装备", "移动"]:
        d = equip.get("by_type", {}).get(typ)
        if not d or not d.get("tiers"):
            continue
        L.append(f"\n### {typ}（成品 {d.get('final_count', 0)} 件）\n")
        for tier in tier_order:
            lst = d["tiers"].get(tier)
            if lst:
                L.append(f"- `{tier}`：{'、'.join(_mark(x) for x in lst)}")
        if d.get("smalls"):
            L.append(f"- 小件：{'、'.join(d['smalls'][:10])}")

    # 3. 阵容（英雄已按当前梯度动态校正）
    names_cn = {2: "双人", 3: "三人", 5: "五人"}
    L.append("\n\n## 三、阵容搭配（当前梯度动态生成）\n")
    for size in ("5", "3", "2"):
        cs = comps.get(size) or comps.get(int(size)) or []
        if not cs:
            continue
        L.append(f"\n### {names_cn[int(size)]}阵容（按综合强度排序）\n")
        for c in cs:
            picks = "　".join(f"**{m['hero']}**·{m['lane']}" for m in c["members"])
            L.append(f"#### 🏆 {c['name']}（强度 {c['team_score']}）")
            L.append(f"- 阵容：{picks}")
            L.append(f"- 打法：{c['idea']}")
            alts = []
            for m in c["members"]:
                if m.get("version_alts"):
                    alts.append(f"{m['lane']}可换 {'/'.join(m['version_alts'])}")
            if alts:
                L.append(f"- 版本替补：{'；'.join(alts)}")
            L.append("")

    text = "\n".join(L)
    out = GUIDE_DIR / "王者荣耀指南.md"
    out.write_text(text, encoding="utf-8")
    return out


if __name__ == "__main__":
    p = generate()
    print("已生成:", p)
    print(p.read_text(encoding="utf-8")[:600])
