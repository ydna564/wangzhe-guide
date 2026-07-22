# -*- coding: utf-8 -*-
"""爬虫公共工具：HTTP 抓取（带指纹回退）、原始数据落盘。"""
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_RAW, DEFAULT_UA


def fetch(url, *, impersonate="chrome124", timeout=15, headers=None):
    """抓一个 URL 返回 bytes。

    优先用 curl_cffi 模拟真实 Chrome 指纹（对付 B站/攻略站的基础反爬）；
    没装 curl_cffi 时回退到标准库 urllib（够用于官网这种纯公开 JSON）。
    """
    hdrs = {"User-Agent": DEFAULT_UA, "Referer": "https://pvp.qq.com/"}
    if headers:
        hdrs.update(headers)
    try:
        from curl_cffi import requests as creq  # 真实 TLS/JA3 指纹
        r = creq.get(url, headers=hdrs, impersonate=impersonate, timeout=timeout)
        r.raise_for_status()
        return r.content
    except ImportError:
        req = Request(url, headers=hdrs)
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()


def fetch_json(url, **kw):
    raw = fetch(url, **kw)
    # 官网部分 JSON 是 gbk，容错解码
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return json.loads(raw.decode("utf-8", errors="ignore"))


def save_raw(name, data):
    """把原始数据存到 data/raw/，带时间戳留档。"""
    path = DATA_RAW / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    stamp = DATA_RAW / f"{name}.{time.strftime('%Y%m%d')}.json"
    with open(stamp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path
