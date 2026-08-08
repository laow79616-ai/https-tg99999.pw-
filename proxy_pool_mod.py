# -*- coding: utf-8 -*-
"""
代理 IP 池模块（独立文件，尽量少改 bot_engine）
- 展示 / 追加 IP / 均匀分配
- 不删除 Bot、不重挂 Webhook
- setWebhook 由引擎侧保持直连
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

PROXY_POOL_FILE = "/root/bot_panel/data/proxy_pool.json"


def mask_proxy(proxy_url: str) -> str:
    if not proxy_url:
        return ""
    return proxy_url.split("@")[1] if "@" in proxy_url else proxy_url


def normalize_proxy(line: str, default_auth: str = "") -> Optional[str]:
    s = (line or "").strip()
    if not s or s.startswith("#"):
        return None
    if "://" in s:
        return s
    if "@" in s:
        return "socks5://" + s
    if default_auth:
        return f"socks5://{default_auth}@{s}"
    return "socks5://" + s


def parse_proxy_list(text: str, default_auth: str = "") -> List[str]:
    out = []
    for raw in (text or "").splitlines():
        p = normalize_proxy(raw, default_auth)
        if p:
            out.append(p)
    return out


def _norm_range(r) -> Tuple[int, int]:
    return (int(r[0]), int(r[1]))


def lines_to_serializable(proxy_lines: dict) -> dict:
    data = {
        "updated_at": datetime.now().isoformat(),
        "lines": {},
    }
    for k, v in sorted(proxy_lines.items(), key=lambda x: int(x[0])):
        r = _norm_range(v["range"])
        data["lines"][str(k)] = {
            "proxy": v["proxy"],
            "range": [r[0], r[1]],
            "enabled": bool(v.get("enabled", True)),
            "note": v.get("note", ""),
        }
    return data


def save_proxy_pool(proxy_lines: dict, path: str = PROXY_POOL_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = lines_to_serializable(proxy_lines)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def load_into(proxy_lines: dict, path: str = PROXY_POOL_FILE, logger=None) -> dict:
    """
    加载池到 proxy_lines（原地更新并返回）。
    文件不存在：把当前 proxy_lines 原样规范化后落盘（现网映射不变）。
    """
    if not os.path.exists(path):
        fixed = {}
        for k, v in list(proxy_lines.items()):
            r = _norm_range(v["range"])
            fixed[int(k)] = {
                "proxy": v["proxy"],
                "range": r,
                "enabled": True,
                "note": v.get("note", ""),
            }
        proxy_lines.clear()
        proxy_lines.update(fixed)
        save_proxy_pool(proxy_lines, path)
        if logger:
            logger.info("proxy_pool 已初始化，共 %s 条线路（现网映射不变）", len(proxy_lines))
        return proxy_lines

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        new_map = {}
        for k, v in data.get("lines", {}).items():
            r = v.get("range", [1, 1])
            new_map[int(k)] = {
                "proxy": v["proxy"],
                "range": _norm_range(r),
                "enabled": bool(v.get("enabled", True)),
                "note": v.get("note", ""),
            }
        if new_map:
            proxy_lines.clear()
            proxy_lines.update(new_map)
            if logger:
                logger.info("proxy_pool 已加载，共 %s 条线路", len(proxy_lines))
    except Exception as e:
        if logger:
            logger.error("加载 proxy_pool 失败，沿用内存: %s", e)
    return proxy_lines


def get_proxy_for_number(proxy_lines: dict, number: int) -> Optional[str]:
    for line_id, info in proxy_lines.items():
        if not info.get("enabled", True):
            continue
        start, end = info["range"]
        if start <= number <= end:
            return info["proxy"]
    for line_id, info in sorted(proxy_lines.items(), key=lambda x: int(x[0])):
        if info.get("enabled", True):
            return info["proxy"]
    return None


def get_line_for_number(proxy_lines: dict, number: int) -> int:
    for line_id, info in proxy_lines.items():
        if not info.get("enabled", True):
            continue
        start, end = info["range"]
        if start <= number <= end:
            return int(line_id)
    for line_id, info in sorted(proxy_lines.items(), key=lambda x: int(x[0])):
        if info.get("enabled", True):
            return int(line_id)
    return 1


def list_lines(proxy_lines: dict, bots: dict) -> List[dict]:
    items = []
    for line_id, info in sorted(proxy_lines.items(), key=lambda x: int(x[0])):
        start, end = info["range"]
        lid = int(line_id)
        cnt = 0
        for b in bots.values():
            try:
                if get_line_for_number(proxy_lines, int(b["number"])) == lid:
                    cnt += 1
            except Exception:
                pass
        items.append(
            {
                "line_id": lid,
                "proxy": mask_proxy(info.get("proxy", "")),
                "range_start": start,
                "range_end": end,
                "max_bots": end - start + 1,
                "bot_count": cnt,
                "enabled": info.get("enabled", True),
                "note": info.get("note", ""),
            }
        )
    return items


def batch_add(proxy_lines: dict, text: str, default_auth: str = "") -> dict:
    """只追加新线路，不改已有 IP/区间/Bot。"""
    proxies = parse_proxy_list(text, default_auth)
    if not proxies:
        return {"ok": False, "error": "没有有效代理", "added": 0, "lines": []}

    existing = {v["proxy"] for v in proxy_lines.values()}
    next_id = (max(proxy_lines.keys()) + 1) if proxy_lines else 1
    max_end = max((info["range"][1] for info in proxy_lines.values()), default=0)
    added = []
    for p in proxies:
        if p in existing:
            continue
        start = max_end + 1
        end = start + 13
        proxy_lines[next_id] = {
            "proxy": p,
            "range": (start, end),
            "enabled": True,
            "note": "",
        }
        existing.add(p)
        added.append(
            {"line_id": next_id, "proxy": mask_proxy(p), "range": [start, end]}
        )
        max_end = end
        next_id += 1

    save_proxy_pool(proxy_lines)
    return {"ok": True, "added": len(added), "lines": added}


def redistribute(proxy_lines: dict, bots: dict, max_bots: int = 0) -> dict:
    """
    一键均匀分配：重切 range，更新 bot.line/proxy。
    不删除 Bot，不重挂 Webhook。
    """
    enabled_ids = sorted(
        [int(k) for k, v in proxy_lines.items() if v.get("enabled", True)]
    )
    if not enabled_ids:
        return {"ok": False, "error": "无启用线路"}

    if max_bots <= 0:
        nums = [int(b["number"]) for b in bots.values()] or [1]
        max_bots = max(max(nums), 300)

    n = len(enabled_ids)
    cap = (max_bots + n - 1) // n
    for i, lid in enumerate(enabled_ids):
        start = i * cap + 1
        end = min((i + 1) * cap, max_bots)
        if start > end:
            start = end
        proxy_lines[lid]["range"] = (start, end)

    updated = 0
    for bot_id, bot in list(bots.items()):
        num = int(bot["number"])
        new_line = get_line_for_number(proxy_lines, num)
        new_proxy = get_proxy_for_number(proxy_lines, num)
        if bot.get("line") != new_line or bot.get("proxy") != new_proxy:
            bot["line"] = new_line
            bot["proxy"] = new_proxy
            updated += 1

    save_proxy_pool(proxy_lines)
    return {
        "ok": True,
        "lines": n,
        "max_bots": max_bots,
        "cap_per_line": cap,
        "bots_updated": updated,
    }
