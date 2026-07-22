# -*- coding: utf-8 -*-
"""主编排 —— 一键跑通：采集 → 分析 → 生成指南。

用法:
  python run.py              # 全流程（能公开抓的都抓）
  python run.py --no-crawl   # 跳过采集，只用已有 raw 数据重新分析+出指南
  python run.py --with-xhs   # 额外尝试小红书（需 browser-use + 登录态）
"""
import sys

from analysis import hero_strength, equipment, team_comps, generate_guide


def step_crawl(with_xhs=False):
    # 1) 官方英雄/装备 —— 纯公开，必成
    from crawlers import official_pvp
    hs = official_pvp.crawl_heroes()
    its = official_pvp.crawl_items()
    print(f"[1/4 官方] 英雄 {len(hs)}，装备 {len(its)}")

    # 2) B站攻略热度 —— 公开，需 curl_cffi
    try:
        from crawlers import bilibili
        vids = bilibili.crawl()
        print(f"[2/4 B站] {sum(len(v) for v in vids.values())} 条视频")
    except ImportError:
        print("[2/4 B站] 跳过：未装 curl_cffi（pip install curl_cffi）")
    except Exception as e:                            # noqa: BLE001
        print(f"[2/4 B站] 失败（风控/网络）：{e}")

    # 3) 攻略站梯度榜 —— 需 crawl4ai
    try:
        import crawl4ai  # noqa: F401
        from crawlers import strategy_sites
        strategy_sites.crawl()
        print("[3/4 攻略站] 完成")
    except ImportError:
        print("[3/4 攻略站] 跳过：未装 crawl4ai（pip install crawl4ai && crawl4ai-setup）")

    # 4) 小红书 —— Playwright + 登录态，默认不跑
    if with_xhs:
        try:
            from crawlers import xiaohongshu
            notes = xiaohongshu.crawl()
            total = sum(len(v) for v in notes.values())
            if total == 0:
                print("[4/4 小红书] 0 篇：多半未登录。先跑 "
                      "python crawlers/xiaohongshu.py login 扫码登录")
            else:
                print(f"[4/4 小红书] {total} 篇笔记")
        except Exception as e:                        # noqa: BLE001
            print(f"[4/4 小红书] 跳过/失败：{e}")
    else:
        print("[4/4 小红书] 跳过（加 --with-xhs 启用，需先登录）")


def step_analyze():
    hero_strength.analyze()
    equipment.analyze()
    team_comps.build()
    path = generate_guide.generate()
    print(f"[分析] 完成，指南 -> {path}")
    return path


if __name__ == "__main__":
    if "--no-crawl" not in sys.argv:
        step_crawl(with_xhs="--with-xhs" in sys.argv)
    else:
        print("[采集] 跳过，使用已有 data/raw/")
    step_analyze()
    print("\n✅ 全部完成。查看 guide/王者荣耀指南.md")
