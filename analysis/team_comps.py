# -*- coding: utf-8 -*-
"""阵容搭配 —— 2/3/5 人阵容，英雄按【当前梯度】动态校正。

每个模板给出打法思路 + 各分路建议英雄；build() 用当前强度榜校正：
若建议英雄已跌出该分路 T0/T1（不在当前前 TOP_K），自动替换为该分路
当前最强英雄，避免出现过时阵容。并给出每个位置的版本替补。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_PROCESSED
from analysis.baseline import COMP_TEMPLATES

TOP_K = 4          # 建议英雄若不在该分路前 TOP_K，视为已过时，自动替换


def _load_strength():
    p = DATA_PROCESSED / "hero_strength.json"
    if not p.exists():
        return {}, {}
    data = json.load(open(p, encoding="utf-8"))
    score = {r["name"]: r["score"] for r in data["ranking"]}
    top_by_lane = {}
    for lane, rows in data.get("by_role", {}).items():
        top_by_lane[lane] = [r["name"] for r in rows]
    return score, top_by_lane


def build():
    score, top_by_lane = _load_strength()
    result = {}
    for size, templates in COMP_TEMPLATES.items():
        comps = []
        for tpl in templates:
            members, used = [], set()
            for lane, hero in tpl["slots"]:
                ranking = top_by_lane.get(lane, [])
                current = hero
                replaced = False
                # 建议英雄已过时（不在当前 TOP_K）→ 换当前最强且未占用的
                if ranking and hero not in ranking[:TOP_K]:
                    for cand in ranking:
                        if cand not in used:
                            current, replaced = cand, True
                            break
                used.add(current)
                alts = [h for h in ranking[:TOP_K] if h != current][:2]
                members.append({
                    "lane": lane,
                    "hero": current,
                    "score": score.get(current, 0),
                    "replaced_from": hero if replaced else None,
                    "version_alts": alts,
                })
            avg = round(sum(m["score"] for m in members) / len(members), 1) \
                if members else 0
            comps.append({
                "name": tpl["name"], "size": size, "idea": tpl["idea"],
                "members": members, "team_score": avg,
            })
        comps.sort(key=lambda c: c["team_score"], reverse=True)
        result[size] = comps

    json.dump(result, open(DATA_PROCESSED / "team_comps.json", "w",
              encoding="utf-8"), ensure_ascii=False, indent=2)
    return result


if __name__ == "__main__":
    res = build()
    for size in (2, 3, 5):
        print(f"\n=== {size}人阵容 ===")
        for c in res[size]:
            picks = " + ".join(
                f"{m['hero']}({m['lane']})" + (f"←{m['replaced_from']}" if m['replaced_from'] else "")
                for m in c["members"])
            print(f"  【{c['name']}】强度{c['team_score']}")
            print(f"    {picks}")
            print(f"    思路: {c['idea']}")
