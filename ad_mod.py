# -*- coding: utf-8 -*-
"""
广告配置模块：全局默认 + 按线路覆盖
兼容旧版扁平 ad_config.json
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional

AD_CONFIG_FILE = "/root/bot_panel/data/ad_config.json"
AD_MEDIA_DIR = "/root/bot_panel/data/ad_media"


def _empty_ad(name: str = "default") -> dict:
    return {
        "name": name,
        "title": "",
        "text": "",
        "photo": "",
        "video": "",
        "buttons": [],
    }


def normalize_ad(raw: dict) -> dict:
    if not isinstance(raw, dict):
        return _empty_ad()
    buttons = raw.get("buttons") or []
    # 统一 buttons 为 list[list[dict]]
    norm_btns = []
    for row in buttons:
        if isinstance(row, list):
            norm_btns.append(
                [
                    {"text": b.get("text", ""), "url": b.get("url", "")}
                    for b in row
                    if isinstance(b, dict) and b.get("text") and b.get("url")
                ]
            )
        elif isinstance(row, dict) and row.get("text") and row.get("url"):
            norm_btns.append([{"text": row["text"], "url": row["url"]}])
    text = raw.get("text") or raw.get("caption") or ""
    title = raw.get("title") or ""
    if title and title not in text:
        # 发送时用完整 caption
        pass
    photo = raw.get("photo") or raw.get("image") or ""
    return {
        "name": raw.get("name") or "ad",
        "title": title,
        "text": text,
        "photo": photo,
        "video": raw.get("video") or "",
        "buttons": norm_btns,
    }


def caption_of(ad: dict) -> str:
    title = (ad.get("title") or "").strip()
    text = (ad.get("text") or "").strip()
    if title and text:
        return title + "\n\n" + text
    return title or text


def migrate_raw(raw: Any) -> dict:
    """旧格式 → version2"""
    if not isinstance(raw, dict):
        return {"version": 2, "default": _empty_ad(), "by_line": {}}
    if raw.get("version") == 2 and "default" in raw:
        out = {
            "version": 2,
            "default": normalize_ad(raw.get("default") or {}),
            "by_line": {},
        }
        for k, v in (raw.get("by_line") or {}).items():
            out["by_line"][str(k)] = normalize_ad(v)
        return out
    # ads 列表格式
    if "ads" in raw and isinstance(raw["ads"], list) and raw["ads"]:
        active = None
        for ad in raw["ads"]:
            if ad.get("active", True):
                active = ad
                break
        active = active or raw["ads"][0]
        return {"version": 2, "default": normalize_ad(active), "by_line": {}}
    # 扁平
    return {"version": 2, "default": normalize_ad(raw), "by_line": {}}


def load_store(path: str = AD_CONFIG_FILE) -> dict:
    if not os.path.exists(path):
        return {"version": 2, "default": _empty_ad("default_ad"), "by_line": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return migrate_raw(raw)
    except Exception:
        return {"version": 2, "default": _empty_ad(), "by_line": {}}


def save_store(store: dict, path: str = AD_CONFIG_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    store = migrate_raw(store)
    store["updated_at"] = datetime.now().isoformat()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def get_ad_for_line(store: dict, line_id: Optional[int]) -> dict:
    store = migrate_raw(store)
    if line_id is not None:
        key = str(int(line_id))
        if key in store.get("by_line", {}):
            return normalize_ad(store["by_line"][key])
    return normalize_ad(store.get("default") or {})


def resolve_media_path(path: str) -> str:
    if not path:
        return ""
    if os.path.isabs(path) and os.path.exists(path):
        return path
    # 相对 data 目录
    candidates = [
        path,
        os.path.join("/root/bot_panel/data", path),
        os.path.join(AD_MEDIA_DIR, os.path.basename(path)),
        os.path.join("/root/bot_panel/data/photos", os.path.basename(path)),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return ""


def list_summary(store: dict) -> dict:
    store = migrate_raw(store)
    d = store["default"]
    by = {}
    for k, v in store.get("by_line", {}).items():
        by[k] = {
            "name": v.get("name"),
            "title": v.get("title"),
            "text_len": len(v.get("text") or ""),
            "has_photo": bool(v.get("photo")),
            "has_video": bool(v.get("video")),
            "buttons": len(v.get("buttons") or []),
        }
    return {
        "ok": True,
        "version": 2,
        "default": {
            "name": d.get("name"),
            "title": d.get("title"),
            "text": d.get("text"),
            "photo": d.get("photo"),
            "video": d.get("video"),
            "buttons": d.get("buttons"),
            "text_len": len(d.get("text") or ""),
        },
        "by_line": by,
        "line_ids": sorted(by.keys(), key=lambda x: int(x)),
    }


def save_ad(
    store: dict,
    ad: dict,
    *,
    as_default: bool = True,
    line_ids: Optional[List[int]] = None,
) -> dict:
    """
    保存广告。
    as_default=True 时写入 default。
    line_ids 非空时写入对应线路（覆盖）。
    """
    store = migrate_raw(store)
    ad = normalize_ad(ad)
    if as_default or not line_ids:
        store["default"] = ad
    if line_ids:
        if "by_line" not in store:
            store["by_line"] = {}
        for lid in line_ids:
            store["by_line"][str(int(lid))] = ad
    save_store(store)
    return {"ok": True, "as_default": bool(as_default or not line_ids), "lines": [int(x) for x in (line_ids or [])]}


def clear_line_ads(store: dict, line_ids: List[int]) -> dict:
    store = migrate_raw(store)
    for lid in line_ids:
        store.get("by_line", {}).pop(str(int(lid)), None)
    save_store(store)
    return {"ok": True, "cleared": [int(x) for x in line_ids]}
