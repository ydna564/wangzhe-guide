# -*- coding: utf-8 -*-
"""小红书爬虫 —— Playwright 持久登录态 + 搜索笔记提取。

为什么用 Playwright 而不是 browser-use：
  抓小红书是「搜索关键词 → 提取笔记卡片」的重复结构化任务，Playwright
  确定性强、免 LLM API 费、更稳；browser-use 的 LLM 代理层在这种任务上
  又慢又贵又易飘（它本身也是跑在 Playwright 上）。

选择器已用真实 DOM 验证（explore 页无登录即可提取）：
  笔记卡片 section.note-item ｜ 标题 .title ｜ 作者 .author .name ｜ 点赞 .like-wrapper .count

登录：小红书搜索结果需登录。login() 会开一个有头浏览器让你扫码登录一次，
登录态持久化到 ~/.wzry_xhs_profile，之后 crawl() 复用，无需再登。
⚠️ 抓小红书违反其 ToS 且有反爬，请用小号、控频率，仅供个人研究。

依赖:  crawl4ai 已带 playwright+chromium；或  pip install playwright && playwright install chromium
用法:
  python crawlers/xiaohongshu.py login     # 一次性：扫码登录（有头浏览器）
  python crawlers/xiaohongshu.py           # 抓取（复用登录态）
"""
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_RAW
from crawlers.base import save_raw

PROFILE_DIR = str(Path.home() / ".wzry_xhs_profile")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
KEYWORDS = ["王者荣耀最强阵容", "王者荣耀上分英雄", "王者荣耀双人上分", "王者荣耀T0"]

# 页面内提取笔记卡片的 JS（选择器已对真实 DOM 验证）
EXTRACT_JS = r"""
() => {
  const pick = (el, sels) => {
    for (const s of sels) { const n = el.querySelector(s); if (n && n.innerText) return n.innerText.trim(); }
    return '';
  };
  return [...document.querySelectorAll('section.note-item')].map(it => ({
    title:  pick(it, ['.title', 'a.title span', '.footer .title']),
    author: pick(it, ['.author .name', '.author-wrapper .name', '.name']),
    like:   pick(it, ['.like-wrapper .count', '.count', '.like .count']),
    href:   (it.querySelector("a.cover, a[href*='/explore/']") || {}).getAttribute
             ? it.querySelector("a.cover, a[href*='/explore/']").getAttribute('href') : '',
  })).filter(x => x.title);
}
"""


def _parse_like(s):
    """'2.9万' / '10万+' / '5.1万' -> 整数近似。"""
    s = (s or "").replace("+", "").strip()
    m = re.match(r"([\d.]+)\s*万", s)
    if m:
        return int(float(m.group(1)) * 10000)
    return int(re.sub(r"\D", "", s) or 0)


def _match_heroes(text):
    p = DATA_RAW / "heroes.json"
    if not p.exists():
        return []
    import json
    names = [h["name"] for h in json.load(open(p, encoding="utf-8"))]
    return sorted({n for n in names if n in (text or "")})


def login():
    """开有头浏览器，手动扫码登录小红书；登录态存进持久 profile。"""
    from playwright.sync_api import sync_playwright
    print("即将打开小红书，请在浏览器里【扫码/短信登录】。登录成功后回到终端按回车。")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE_DIR, headless=False, user_agent=UA,
            viewport={"width": 1280, "height": 900})
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
        input(">>> 登录完成后按回车继续...")
        ctx.close()
    print(f"登录态已保存到 {PROFILE_DIR}")


def _is_logged_in(ctx):
    cookies = {c["name"] for c in ctx.cookies()}
    return "web_session" in cookies or "a1" in cookies


def crawl(keywords=KEYWORDS, headless=True, max_scroll=3, per_kw=20):
    from playwright.sync_api import sync_playwright
    results = {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE_DIR, headless=headless, user_agent=UA,
            viewport={"width": 1280, "height": 900})
        if not _is_logged_in(ctx):
            print("⚠️ 未检测到登录态。请先运行:  python crawlers/xiaohongshu.py login")
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        for kw in keywords:
            url = ("https://www.xiaohongshu.com/search_result?keyword="
                   + urllib.parse.quote(kw) + "&type=51")
            try:
                pg.goto(url, timeout=30000, wait_until="domcontentloaded")
                pg.wait_for_timeout(3500)
                for _ in range(max_scroll):
                    pg.mouse.wheel(0, 3000)
                    pg.wait_for_timeout(1500)
                cards = pg.evaluate(EXTRACT_JS)[:per_kw]
                for c in cards:
                    c["likes"] = _parse_like(c.get("like"))
                    c["heroes"] = _match_heroes(c.get("title"))
                results[kw] = cards
                print(f"[小红书] '{kw}' -> {len(cards)} 篇笔记")
            except Exception as e:                    # noqa: BLE001
                print(f"[小红书] '{kw}' 失败: {e}")
                results[kw] = []
            time.sleep(2)
        ctx.close()
    save_raw("xiaohongshu_notes", results)
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        login()
    else:
        crawl()
