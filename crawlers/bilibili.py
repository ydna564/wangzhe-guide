# -*- coding: utf-8 -*-
"""B站爬虫 —— 搜索王者荣耀攻略视频 + 评论区口碑。

用 curl_cffi 模拟真实 Chrome 指纹（对付基础反爬）。
B站搜索接口需要 WBI 签名，这里完整实现了签名算法（公开技术，无需登录）。
登录后（传 SESSDATA cookie）可拿到更全的评论。

依赖:  pip install curl_cffi
"""
import hashlib
import sys
import time
import urllib.parse
from functools import reduce
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from crawlers.base import save_raw

_SESSION = None
MAX_AGE_DAYS = 90          # 只保留近 90 天的视频，保证热度信号时效性


def _session():
    """带真实 Chrome 指纹的持久 session，先访问首页拿 buvid3 cookie
    （B站搜索接口现在要求这个匿名 cookie，否则 403）。"""
    global _SESSION
    if _SESSION is not None:
        return _SESSION
    from curl_cffi import requests as creq          # 必需，纯 urllib 会被 403
    s = creq.Session(impersonate="chrome124")
    s.get("https://www.bilibili.com", timeout=15)   # 种下 buvid3 / b_nut
    # 补 buvid3/buvid4，绕过搜索接口的 v_voucher 风控软拦截（无需登录）
    try:
        spi = s.get("https://api.bilibili.com/x/frontend/finger/spi",
                    timeout=15).json().get("data", {})
        if spi.get("b_3"):
            s.cookies.set("buvid3", spi["b_3"], domain=".bilibili.com")
        if spi.get("b_4"):
            s.cookies.set("buvid4", spi["b_4"], domain=".bilibili.com")
    except Exception:                               # noqa: BLE001
        pass
    # 可选：有登录 cookie 时传入，能拿更全数据（见 README）
    import os
    if os.environ.get("BILI_SESSDATA"):
        s.cookies.set("SESSDATA", os.environ["BILI_SESSDATA"],
                      domain=".bilibili.com")
    _SESSION = s
    return s


def _get_json(url):
    return _session().get(url, timeout=15).json()

# WBI 混淆置换表（B站前端固定常量）
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]


def _get_mixin_key(orig):
    return reduce(lambda s, i: s + orig[i], MIXIN_KEY_ENC_TAB, "")[:32]


def _get_wbi_keys():
    """从 nav 接口取 img_key / sub_key（无需登录即可拿到）。"""
    data = _get_json("https://api.bilibili.com/x/web-interface/nav")
    wbi = data["data"]["wbi_img"]
    img = wbi["img_url"].rsplit("/", 1)[-1].split(".")[0]
    sub = wbi["sub_url"].rsplit("/", 1)[-1].split(".")[0]
    return img, sub


def _sign(params):
    img, sub = _get_wbi_keys()
    mixin = _get_mixin_key(img + sub)
    params = dict(params, wts=int(time.time()))
    query = urllib.parse.urlencode(sorted(params.items()))
    params["w_rid"] = hashlib.md5((query + mixin).encode()).hexdigest()
    return params


def _reset_session():
    global _SESSION
    _SESSION = None


def search_videos(keyword, page=1, retries=3):
    """搜索攻略视频，返回 [{标题, UP主, 播放, 点赞, bvid}]。

    B站搜索有自适应风控：连查会返回 v_voucher（软拦截，data 里只有 voucher）。
    命中时重置 session 重拿 buvid + 退避重试。设 BILI_SESSDATA 登录 cookie 更稳。
    """
    result = []
    for attempt in range(retries):
        params = _sign({
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "order": "totalrank",
        })
        url = "https://api.bilibili.com/x/web-interface/wbi/search/type?" + \
              urllib.parse.urlencode(params)
        data = _get_json(url).get("data", {})
        result = data.get("result")
        if result:                                   # 拿到结果
            break
        # v_voucher 风控：换 session + 退避
        _reset_session()
        time.sleep(2 * (attempt + 1))
    cutoff = time.time() - MAX_AGE_DAYS * 86400        # 只保留近 N 天的视频
    out = []
    for v in (result or []):
        pub = v.get("pubdate") or 0
        if pub and pub < cutoff:                       # 过滤过时内容，保证时效性
            continue
        out.append({
            "title": _strip(v.get("title")),
            "author": v.get("author"),
            "play": v.get("play"),
            "like": v.get("like"),
            "bvid": v.get("bvid"),
            "pubdate": v.get("pubdate"),
        })
    return out


def _strip(s):
    import re
    return re.sub(r"<[^>]+>", "", s or "")


# 无空格关键词更容易过风控（带空格更易触发 v_voucher）
DEFAULT_KEYWORDS = ("王者荣耀最强阵容", "王者荣耀英雄梯度", "王者荣耀上分英雄",
                    "王者荣耀T0英雄", "王者荣耀版本答案")


def crawl(keywords=DEFAULT_KEYWORDS):
    results = {}
    for kw in keywords:
        try:
            results[kw] = search_videos(kw)
            print(f"[B站] '{kw}' -> {len(results[kw])} 条")
        except Exception as e:                       # noqa: BLE001
            print(f"[B站] '{kw}' 失败: {e}")
            results[kw] = []
        _reset_session()          # 每个关键词换新 session，降低风控
        time.sleep(3)
    save_raw("bilibili_videos", results)
    return results


if __name__ == "__main__":
    crawl()
