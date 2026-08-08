#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键安装：代理 IP 池（展示 / 批量追加 / 均匀分配）
- 不删除 Bot
- setWebhook 强制直连（避免坏代理导致全挂）
- 首次用现有 PROXY_LINES 原样初始化池
在服务器执行:
  cd /root/bot_panel
  python3 install_proxy_pool.py
  然后重启 bot_engine / panel_app
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from datetime import datetime

BASE = "/root/bot_panel"
if not os.path.isdir(BASE):
    BASE = os.path.dirname(os.path.abspath(__file__))

MOD_NAME = "proxy_pool_mod.py"

MOD_B64 = "IyAtKi0gY29kaW5nOiB1dGYtOCAtKi0KIiIiCuS7o+eQhiBJUCDmsaDmqKHlnZfvvIjni6znq4vmlofku7bvvIzlsL3ph4/lsJHmlLkgYm90X2VuZ2luZe+8iQotIOWxleekuiAvIOi/veWKoCBJUCAvIOWdh+WMgOWIhumFjQotIOS4jeWIoOmZpCBCb3TjgIHkuI3ph43mjIIgV2ViaG9vawotIHNldFdlYmhvb2sg55Sx5byV5pOO5L6n5L+d5oyB55u06L+eCiIiIgpmcm9tIF9fZnV0dXJlX18gaW1wb3J0IGFubm90YXRpb25zCgppbXBvcnQganNvbgppbXBvcnQgb3MKaW1wb3J0IHJlCmZyb20gZGF0ZXRpbWUgaW1wb3J0IGRhdGV0aW1lCmZyb20gdHlwaW5nIGltcG9ydCBBbnksIERpY3QsIExpc3QsIE9wdGlvbmFsLCBUdXBsZQoKUFJPWFlfUE9PTF9GSUxFID0gIi9yb290L2JvdF9wYW5lbC9kYXRhL3Byb3h5X3Bvb2wuanNvbiIKCgpkZWYgbWFza19wcm94eShwcm94eV91cmw6IHN0cikgLT4gc3RyOgogICAgaWYgbm90IHByb3h5X3VybDoKICAgICAgICByZXR1cm4gIiIKICAgIHJldHVybiBwcm94eV91cmwuc3BsaXQoIkAiKVsxXSBpZiAiQCIgaW4gcHJveHlfdXJsIGVsc2UgcHJveHlfdXJsCgoKZGVmIG5vcm1hbGl6ZV9wcm94eShsaW5lOiBzdHIsIGRlZmF1bHRfYXV0aDogc3RyID0gIiIpIC0+IE9wdGlvbmFsW3N0cl06CiAgICBzID0gKGxpbmUgb3IgIiIpLnN0cmlwKCkKICAgIGlmIG5vdCBzIG9yIHMuc3RhcnRzd2l0aCgiIyIpOgogICAgICAgIHJldHVybiBOb25lCiAgICBpZiAiOi8vIiBpbiBzOgogICAgICAgIHJldHVybiBzCiAgICBpZiAiQCIgaW4gczoKICAgICAgICByZXR1cm4gInNvY2tzNTovLyIgKyBzCiAgICBpZiBkZWZhdWx0X2F1dGg6CiAgICAgICAgcmV0dXJuIGYic29ja3M1Oi8ve2RlZmF1bHRfYXV0aH1Ae3N9IgogICAgcmV0dXJuICJzb2NrczU6Ly8iICsgcwoKCmRlZiBwYXJzZV9wcm94eV9saXN0KHRleHQ6IHN0ciwgZGVmYXVsdF9hdXRoOiBzdHIgPSAiIikgLT4gTGlzdFtzdHJdOgogICAgb3V0ID0gW10KICAgIGZvciByYXcgaW4gKHRleHQgb3IgIiIpLnNwbGl0bGluZXMoKToKICAgICAgICBwID0gbm9ybWFsaXplX3Byb3h5KHJhdywgZGVmYXVsdF9hdXRoKQogICAgICAgIGlmIHA6CiAgICAgICAgICAgIG91dC5hcHBlbmQocCkKICAgIHJldHVybiBvdXQKCgpkZWYgX25vcm1fcmFuZ2UocikgLT4gVHVwbGVbaW50LCBpbnRdOgogICAgcmV0dXJuIChpbnQoclswXSksIGludChyWzFdKSkKCgpkZWYgbGluZXNfdG9fc2VyaWFsaXphYmxlKHByb3h5X2xpbmVzOiBkaWN0KSAtPiBkaWN0OgogICAgZGF0YSA9IHsKICAgICAgICAidXBkYXRlZF9hdCI6IGRhdGV0aW1lLm5vdygpLmlzb2Zvcm1hdCgpLAogICAgICAgICJsaW5lcyI6IHt9LAogICAgfQogICAgZm9yIGssIHYgaW4gc29ydGVkKHByb3h5X2xpbmVzLml0ZW1zKCksIGtleT1sYW1iZGEgeDogaW50KHhbMF0pKToKICAgICAgICByID0gX25vcm1fcmFuZ2UodlsicmFuZ2UiXSkKICAgICAgICBkYXRhWyJsaW5lcyJdW3N0cihrKV0gPSB7CiAgICAgICAgICAgICJwcm94eSI6IHZbInByb3h5Il0sCiAgICAgICAgICAgICJyYW5nZSI6IFtyWzBdLCByWzFdXSwKICAgICAgICAgICAgImVuYWJsZWQiOiBib29sKHYuZ2V0KCJlbmFibGVkIiwgVHJ1ZSkpLAogICAgICAgICAgICAibm90ZSI6IHYuZ2V0KCJub3RlIiwgIiIpLAogICAgICAgIH0KICAgIHJldHVybiBkYXRhCgoKZGVmIHNhdmVfcHJveHlfcG9vbChwcm94eV9saW5lczogZGljdCwgcGF0aDogc3RyID0gUFJPWFlfUE9PTF9GSUxFKSAtPiBOb25lOgogICAgb3MubWFrZWRpcnMob3MucGF0aC5kaXJuYW1lKHBhdGgpLCBleGlzdF9vaz1UcnVlKQogICAgZGF0YSA9IGxpbmVzX3RvX3NlcmlhbGl6YWJsZShwcm94eV9saW5lcykKICAgIHRtcCA9IHBhdGggKyAiLnRtcCIKICAgIHdpdGggb3Blbih0bXAsICJ3IiwgZW5jb2Rpbmc9InV0Zi04IikgYXMgZjoKICAgICAgICBqc29uLmR1bXAoZGF0YSwgZiwgaW5kZW50PTIsIGVuc3VyZV9hc2NpaT1GYWxzZSkKICAgIG9zLnJlcGxhY2UodG1wLCBwYXRoKQoKCmRlZiBsb2FkX2ludG8ocHJveHlfbGluZXM6IGRpY3QsIHBhdGg6IHN0ciA9IFBST1hZX1BPT0xfRklMRSwgbG9nZ2VyPU5vbmUpIC0+IGRpY3Q6CiAgICAiIiIKICAgIOWKoOi9veaxoOWIsCBwcm94eV9saW5lc++8iOWOn+WcsOabtOaWsOW5tui/lOWbnu+8ieOAggogICAg5paH5Lu25LiN5a2Y5Zyo77ya5oqK5b2T5YmNIHByb3h5X2xpbmVzIOWOn+agt+inhOiMg+WMluWQjuiQveebmO+8iOeOsOe9keaYoOWwhOS4jeWPmO+8ieOAggogICAgIiIiCiAgICBpZiBub3Qgb3MucGF0aC5leGlzdHMocGF0aCk6CiAgICAgICAgZml4ZWQgPSB7fQogICAgICAgIGZvciBrLCB2IGluIGxpc3QocHJveHlfbGluZXMuaXRlbXMoKSk6CiAgICAgICAgICAgIHIgPSBfbm9ybV9yYW5nZSh2WyJyYW5nZSJdKQogICAgICAgICAgICBmaXhlZFtpbnQoayldID0gewogICAgICAgICAgICAgICAgInByb3h5IjogdlsicHJveHkiXSwKICAgICAgICAgICAgICAgICJyYW5nZSI6IHIsCiAgICAgICAgICAgICAgICAiZW5hYmxlZCI6IFRydWUsCiAgICAgICAgICAgICAgICAibm90ZSI6IHYuZ2V0KCJub3RlIiwgIiIpLAogICAgICAgICAgICB9CiAgICAgICAgcHJveHlfbGluZXMuY2xlYXIoKQogICAgICAgIHByb3h5X2xpbmVzLnVwZGF0ZShmaXhlZCkKICAgICAgICBzYXZlX3Byb3h5X3Bvb2wocHJveHlfbGluZXMsIHBhdGgpCiAgICAgICAgaWYgbG9nZ2VyOgogICAgICAgICAgICBsb2dnZXIuaW5mbygicHJveHlfcG9vbCDlt7LliJ3lp4vljJbvvIzlhbEgJXMg5p2h57q/6Lev77yI546w572R5pig5bCE5LiN5Y+Y77yJIiwgbGVuKHByb3h5X2xpbmVzKSkKICAgICAgICByZXR1cm4gcHJveHlfbGluZXMKCiAgICB0cnk6CiAgICAgICAgd2l0aCBvcGVuKHBhdGgsICJyIiwgZW5jb2Rpbmc9InV0Zi04IikgYXMgZjoKICAgICAgICAgICAgZGF0YSA9IGpzb24ubG9hZChmKQogICAgICAgIG5ld19tYXAgPSB7fQogICAgICAgIGZvciBrLCB2IGluIGRhdGEuZ2V0KCJsaW5lcyIsIHt9KS5pdGVtcygpOgogICAgICAgICAgICByID0gdi5nZXQoInJhbmdlIiwgWzEsIDFdKQogICAgICAgICAgICBuZXdfbWFwW2ludChrKV0gPSB7CiAgICAgICAgICAgICAgICAicHJveHkiOiB2WyJwcm94eSJdLAogICAgICAgICAgICAgICAgInJhbmdlIjogX25vcm1fcmFuZ2UociksCiAgICAgICAgICAgICAgICAiZW5hYmxlZCI6IGJvb2wodi5nZXQoImVuYWJsZWQiLCBUcnVlKSksCiAgICAgICAgICAgICAgICAibm90ZSI6IHYuZ2V0KCJub3RlIiwgIiIpLAogICAgICAgICAgICB9CiAgICAgICAgaWYgbmV3X21hcDoKICAgICAgICAgICAgcHJveHlfbGluZXMuY2xlYXIoKQogICAgICAgICAgICBwcm94eV9saW5lcy51cGRhdGUobmV3X21hcCkKICAgICAgICAgICAgaWYgbG9nZ2VyOgogICAgICAgICAgICAgICAgbG9nZ2VyLmluZm8oInByb3h5X3Bvb2wg5bey5Yqg6L2977yM5YWxICVzIOadoee6v+i3ryIsIGxlbihwcm94eV9saW5lcykpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgaWYgbG9nZ2VyOgogICAgICAgICAgICBsb2dnZXIuZXJyb3IoIuWKoOi9vSBwcm94eV9wb29sIOWksei0pe+8jOayv+eUqOWGheWtmDogJXMiLCBlKQogICAgcmV0dXJuIHByb3h5X2xpbmVzCgoKZGVmIGdldF9wcm94eV9mb3JfbnVtYmVyKHByb3h5X2xpbmVzOiBkaWN0LCBudW1iZXI6IGludCkgLT4gT3B0aW9uYWxbc3RyXToKICAgIGZvciBsaW5lX2lkLCBpbmZvIGluIHByb3h5X2xpbmVzLml0ZW1zKCk6CiAgICAgICAgaWYgbm90IGluZm8uZ2V0KCJlbmFibGVkIiwgVHJ1ZSk6CiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgc3RhcnQsIGVuZCA9IGluZm9bInJhbmdlIl0KICAgICAgICBpZiBzdGFydCA8PSBudW1iZXIgPD0gZW5kOgogICAgICAgICAgICByZXR1cm4gaW5mb1sicHJveHkiXQogICAgZm9yIGxpbmVfaWQsIGluZm8gaW4gc29ydGVkKHByb3h5X2xpbmVzLml0ZW1zKCksIGtleT1sYW1iZGEgeDogaW50KHhbMF0pKToKICAgICAgICBpZiBpbmZvLmdldCgiZW5hYmxlZCIsIFRydWUpOgogICAgICAgICAgICByZXR1cm4gaW5mb1sicHJveHkiXQogICAgcmV0dXJuIE5vbmUKCgpkZWYgZ2V0X2xpbmVfZm9yX251bWJlcihwcm94eV9saW5lczogZGljdCwgbnVtYmVyOiBpbnQpIC0+IGludDoKICAgIGZvciBsaW5lX2lkLCBpbmZvIGluIHByb3h5X2xpbmVzLml0ZW1zKCk6CiAgICAgICAgaWYgbm90IGluZm8uZ2V0KCJlbmFibGVkIiwgVHJ1ZSk6CiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgc3RhcnQsIGVuZCA9IGluZm9bInJhbmdlIl0KICAgICAgICBpZiBzdGFydCA8PSBudW1iZXIgPD0gZW5kOgogICAgICAgICAgICByZXR1cm4gaW50KGxpbmVfaWQpCiAgICBmb3IgbGluZV9pZCwgaW5mbyBpbiBzb3J0ZWQocHJveHlfbGluZXMuaXRlbXMoKSwga2V5PWxhbWJkYSB4OiBpbnQoeFswXSkpOgogICAgICAgIGlmIGluZm8uZ2V0KCJlbmFibGVkIiwgVHJ1ZSk6CiAgICAgICAgICAgIHJldHVybiBpbnQobGluZV9pZCkKICAgIHJldHVybiAxCgoKZGVmIGxpc3RfbGluZXMocHJveHlfbGluZXM6IGRpY3QsIGJvdHM6IGRpY3QpIC0+IExpc3RbZGljdF06CiAgICBpdGVtcyA9IFtdCiAgICBmb3IgbGluZV9pZCwgaW5mbyBpbiBzb3J0ZWQocHJveHlfbGluZXMuaXRlbXMoKSwga2V5PWxhbWJkYSB4OiBpbnQoeFswXSkpOgogICAgICAgIHN0YXJ0LCBlbmQgPSBpbmZvWyJyYW5nZSJdCiAgICAgICAgbGlkID0gaW50KGxpbmVfaWQpCiAgICAgICAgY250ID0gMAogICAgICAgIGZvciBiIGluIGJvdHMudmFsdWVzKCk6CiAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAgIGlmIGdldF9saW5lX2Zvcl9udW1iZXIocHJveHlfbGluZXMsIGludChiWyJudW1iZXIiXSkpID09IGxpZDoKICAgICAgICAgICAgICAgICAgICBjbnQgKz0gMQogICAgICAgICAgICBleGNlcHQgRXhjZXB0aW9uOgogICAgICAgICAgICAgICAgcGFzcwogICAgICAgIGl0ZW1zLmFwcGVuZCgKICAgICAgICAgICAgewogICAgICAgICAgICAgICAgImxpbmVfaWQiOiBsaWQsCiAgICAgICAgICAgICAgICAicHJveHkiOiBtYXNrX3Byb3h5KGluZm8uZ2V0KCJwcm94eSIsICIiKSksCiAgICAgICAgICAgICAgICAicmFuZ2Vfc3RhcnQiOiBzdGFydCwKICAgICAgICAgICAgICAgICJyYW5nZV9lbmQiOiBlbmQsCiAgICAgICAgICAgICAgICAibWF4X2JvdHMiOiBlbmQgLSBzdGFydCArIDEsCiAgICAgICAgICAgICAgICAiYm90X2NvdW50IjogY250LAogICAgICAgICAgICAgICAgImVuYWJsZWQiOiBpbmZvLmdldCgiZW5hYmxlZCIsIFRydWUpLAogICAgICAgICAgICAgICAgIm5vdGUiOiBpbmZvLmdldCgibm90ZSIsICIiKSwKICAgICAgICAgICAgfQogICAgICAgICkKICAgIHJldHVybiBpdGVtcwoKCmRlZiBiYXRjaF9hZGQocHJveHlfbGluZXM6IGRpY3QsIHRleHQ6IHN0ciwgZGVmYXVsdF9hdXRoOiBzdHIgPSAiIikgLT4gZGljdDoKICAgICIiIuWPqui/veWKoOaWsOe6v+i3r++8jOS4jeaUueW3suaciSBJUC/ljLrpl7QvQm9044CCIiIiCiAgICBwcm94aWVzID0gcGFyc2VfcHJveHlfbGlzdCh0ZXh0LCBkZWZhdWx0X2F1dGgpCiAgICBpZiBub3QgcHJveGllczoKICAgICAgICByZXR1cm4geyJvayI6IEZhbHNlLCAiZXJyb3IiOiAi5rKh5pyJ5pyJ5pWI5Luj55CGIiwgImFkZGVkIjogMCwgImxpbmVzIjogW119CgogICAgZXhpc3RpbmcgPSB7dlsicHJveHkiXSBmb3IgdiBpbiBwcm94eV9saW5lcy52YWx1ZXMoKX0KICAgIG5leHRfaWQgPSAobWF4KHByb3h5X2xpbmVzLmtleXMoKSkgKyAxKSBpZiBwcm94eV9saW5lcyBlbHNlIDEKICAgIG1heF9lbmQgPSBtYXgoKGluZm9bInJhbmdlIl1bMV0gZm9yIGluZm8gaW4gcHJveHlfbGluZXMudmFsdWVzKCkpLCBkZWZhdWx0PTApCiAgICBhZGRlZCA9IFtdCiAgICBmb3IgcCBpbiBwcm94aWVzOgogICAgICAgIGlmIHAgaW4gZXhpc3Rpbmc6CiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgc3RhcnQgPSBtYXhfZW5kICsgMQogICAgICAgIGVuZCA9IHN0YXJ0ICsgMTMKICAgICAgICBwcm94eV9saW5lc1tuZXh0X2lkXSA9IHsKICAgICAgICAgICAgInByb3h5IjogcCwKICAgICAgICAgICAgInJhbmdlIjogKHN0YXJ0LCBlbmQpLAogICAgICAgICAgICAiZW5hYmxlZCI6IFRydWUsCiAgICAgICAgICAgICJub3RlIjogIiIsCiAgICAgICAgfQogICAgICAgIGV4aXN0aW5nLmFkZChwKQogICAgICAgIGFkZGVkLmFwcGVuZCgKICAgICAgICAgICAgeyJsaW5lX2lkIjogbmV4dF9pZCwgInByb3h5IjogbWFza19wcm94eShwKSwgInJhbmdlIjogW3N0YXJ0LCBlbmRdfQogICAgICAgICkKICAgICAgICBtYXhfZW5kID0gZW5kCiAgICAgICAgbmV4dF9pZCArPSAxCgogICAgc2F2ZV9wcm94eV9wb29sKHByb3h5X2xpbmVzKQogICAgcmV0dXJuIHsib2siOiBUcnVlLCAiYWRkZWQiOiBsZW4oYWRkZWQpLCAibGluZXMiOiBhZGRlZH0KCgpkZWYgcmVkaXN0cmlidXRlKHByb3h5X2xpbmVzOiBkaWN0LCBib3RzOiBkaWN0LCBtYXhfYm90czogaW50ID0gMCkgLT4gZGljdDoKICAgICIiIgogICAg5LiA6ZSu5Z2H5YyA5YiG6YWN77ya6YeN5YiHIHJhbmdl77yM5pu05pawIGJvdC5saW5lL3Byb3h544CCCiAgICDkuI3liKDpmaQgQm9077yM5LiN6YeN5oyCIFdlYmhvb2vjgIIKICAgICIiIgogICAgZW5hYmxlZF9pZHMgPSBzb3J0ZWQoCiAgICAgICAgW2ludChrKSBmb3IgaywgdiBpbiBwcm94eV9saW5lcy5pdGVtcygpIGlmIHYuZ2V0KCJlbmFibGVkIiwgVHJ1ZSldCiAgICApCiAgICBpZiBub3QgZW5hYmxlZF9pZHM6CiAgICAgICAgcmV0dXJuIHsib2siOiBGYWxzZSwgImVycm9yIjogIuaXoOWQr+eUqOe6v+i3ryJ9CgogICAgaWYgbWF4X2JvdHMgPD0gMDoKICAgICAgICBudW1zID0gW2ludChiWyJudW1iZXIiXSkgZm9yIGIgaW4gYm90cy52YWx1ZXMoKV0gb3IgWzFdCiAgICAgICAgbWF4X2JvdHMgPSBtYXgobWF4KG51bXMpLCAzMDApCgogICAgbiA9IGxlbihlbmFibGVkX2lkcykKICAgIGNhcCA9IChtYXhfYm90cyArIG4gLSAxKSAvLyBuCiAgICBmb3IgaSwgbGlkIGluIGVudW1lcmF0ZShlbmFibGVkX2lkcyk6CiAgICAgICAgc3RhcnQgPSBpICogY2FwICsgMQogICAgICAgIGVuZCA9IG1pbigoaSArIDEpICogY2FwLCBtYXhfYm90cykKICAgICAgICBpZiBzdGFydCA+IGVuZDoKICAgICAgICAgICAgc3RhcnQgPSBlbmQKICAgICAgICBwcm94eV9saW5lc1tsaWRdWyJyYW5nZSJdID0gKHN0YXJ0LCBlbmQpCgogICAgdXBkYXRlZCA9IDAKICAgIGZvciBib3RfaWQsIGJvdCBpbiBsaXN0KGJvdHMuaXRlbXMoKSk6CiAgICAgICAgbnVtID0gaW50KGJvdFsibnVtYmVyIl0pCiAgICAgICAgbmV3X2xpbmUgPSBnZXRfbGluZV9mb3JfbnVtYmVyKHByb3h5X2xpbmVzLCBudW0pCiAgICAgICAgbmV3X3Byb3h5ID0gZ2V0X3Byb3h5X2Zvcl9udW1iZXIocHJveHlfbGluZXMsIG51bSkKICAgICAgICBpZiBib3QuZ2V0KCJsaW5lIikgIT0gbmV3X2xpbmUgb3IgYm90LmdldCgicHJveHkiKSAhPSBuZXdfcHJveHk6CiAgICAgICAgICAgIGJvdFsibGluZSJdID0gbmV3X2xpbmUKICAgICAgICAgICAgYm90WyJwcm94eSJdID0gbmV3X3Byb3h5CiAgICAgICAgICAgIHVwZGF0ZWQgKz0gMQoKICAgIHNhdmVfcHJveHlfcG9vbChwcm94eV9saW5lcykKICAgIHJldHVybiB7CiAgICAgICAgIm9rIjogVHJ1ZSwKICAgICAgICAibGluZXMiOiBuLAogICAgICAgICJtYXhfYm90cyI6IG1heF9ib3RzLAogICAgICAgICJjYXBfcGVyX2xpbmUiOiBjYXAsCiAgICAgICAgImJvdHNfdXBkYXRlZCI6IHVwZGF0ZWQsCiAgICB9Cg=="



def backup(paths):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = os.path.join(BASE, f"backup_proxy_{ts}")
    os.makedirs(bak, exist_ok=True)
    for p in paths:
        fp = os.path.join(BASE, p) if not os.path.isabs(p) else p
        if os.path.isfile(fp):
            shutil.copy2(fp, os.path.join(bak, os.path.basename(fp).replace("/", "_")))
    print("备份目录:", bak)
    return bak


def ensure_module():
    import base64
    dst = os.path.join(BASE, MOD_NAME)
    open(dst, "wb").write(base64.b64decode(MOD_B64))
    print("已写入", dst, "bytes", os.path.getsize(dst))


def patch_bot_engine():
    path = os.path.join(BASE, "bot_engine.py")
    s = open(path, encoding="utf-8").read()
    changed = False

    if "import proxy_pool_mod" not in s:
        s = s.replace(
            "from aiohttp import web\n",
            "from aiohttp import web\nimport proxy_pool_mod\n",
            1,
        )
        changed = True

    # 替换 get_proxy / get_line 为读池
    new_getters = '''
def get_proxy_for_number(number):
    """根据Bot编号获取代理URL（读 IP 池）"""
    p = proxy_pool_mod.get_proxy_for_number(PROXY_LINES, number)
    if p:
        return p
    if PROXY_LINES:
        return next(iter(PROXY_LINES.values()))["proxy"]
    return None

def get_line_for_number(number):
    """根据Bot编号获取线路号（读 IP 池）"""
    return proxy_pool_mod.get_line_for_number(PROXY_LINES, number)

'''
    if "proxy_pool_mod.get_proxy_for_number" not in s:
        s = re.sub(
            r"def get_proxy_for_number\(number\):[\s\S]*?def get_line_for_number\(number\):[\s\S]*?return 1\n",
            new_getters,
            s,
            count=1,
        )
        changed = True

    # __init__ 加载池
    if "proxy_pool_mod.load_into" not in s:
        s = s.replace(
            "self.load_config()",
            "proxy_pool_mod.load_into(PROXY_LINES, logger=logger)\n        self.load_config()",
            1,
        )
        changed = True

    # setWebhook 直连
    if "REGISTER_WEBHOOK_DIRECT" not in s:
        s = s.replace(
            "        proxy_url = get_proxy_for_number(number)\n        secret = get_webhook_secret(token)",
            "        proxy_url = None  # REGISTER_WEBHOOK_DIRECT setWebhook 直连，不走代理\n        secret = get_webhook_secret(token)",
            1,
        )
        changed = True

    # get_client 支持 None -> 直连
    if "if not proxy_url:" not in s:
        s = s.replace(
            '    async def get_client(self, proxy_url, bot_id=None):\n        """获取或创建httpx客户端（按代理线路共享，代理失败回退直连）"""\n        if proxy_url not in self.clients:',
            '    async def get_client(self, proxy_url, bot_id=None):\n        """获取或创建httpx客户端（按代理线路共享，代理失败回退直连）"""\n        if not proxy_url:\n            proxy_url = "_direct_"\n        if proxy_url not in self.clients:',
            1,
        )
        changed = True

    # API handlers
    handlers = '''
    async def handle_proxy_pool(self, request):
        items = proxy_pool_mod.list_lines(PROXY_LINES, self.bots)
        return web.json_response({"ok": True, "total": len(items), "lines": items})

    async def handle_proxy_batch_add(self, request):
        data = await request.json()
        text = data.get("proxies_text") or ""
        if not text and isinstance(data.get("proxies"), list):
            text = chr(10).join(data["proxies"])
        result = proxy_pool_mod.batch_add(PROXY_LINES, text, data.get("default_auth", ""))
        status = 200 if result.get("ok") else 400
        return web.json_response(result, status=status)

    async def handle_proxy_redistribute(self, request):
        try:
            data = await request.json()
        except Exception:
            data = {}
        max_bots = int(data.get("max_bots") or 0)
        result = proxy_pool_mod.redistribute(PROXY_LINES, self.bots, max_bots=max_bots)
        if result.get("ok"):
            self.save_config()
            # 清理不再使用的代理 httpx 客户端（不影响 webhook 入站）
            try:
                live = {info["proxy"] for info in PROXY_LINES.values() if info.get("enabled", True)}
                dead = [u for u in list(self.clients.keys()) if u not in live and u != "_direct_"]
                for u in dead:
                    c = self.clients.pop(u, None)
                    if c:
                        import asyncio as _asyncio
                        _asyncio.create_task(c.aclose())
            except Exception as e:
                logger.warning("清理 proxy 客户端: %s", e)
        status = 200 if result.get("ok") else 400
        return web.json_response(result, status=status)

'''
    if "handle_proxy_batch_add" not in s:
        s = s.replace(
            "    async def handle_status(self, request):",
            handlers + "\n    async def handle_status(self, request):",
            1,
        )
        changed = True

    if "/proxy_pool/redistribute" not in s:
        s = s.replace(
            "app.router.add_get('/status', engine.handle_status)",
            "app.router.add_get('/status', engine.handle_status)\n"
            "    app.router.add_get('/proxy_pool', engine.handle_proxy_pool)\n"
            "    app.router.add_post('/proxy_pool/batch_add', engine.handle_proxy_batch_add)\n"
            "    app.router.add_post('/proxy_pool/redistribute', engine.handle_proxy_redistribute)",
            1,
        )
        changed = True

    if changed:
        open(path, "w", encoding="utf-8").write(s)
        print("OK 已修改 bot_engine.py")
    else:
        print("bot_engine.py 已是目标状态")

    import py_compile

    py_compile.compile(path, doraise=True)
    print("bot_engine 语法 OK")


def patch_panel_app():
    path = os.path.join(BASE, "panel_app.py")
    s = open(path, encoding="utf-8").read()
    block = '''

@app.route("/api/proxy_pool")
@login_required
def api_proxy_pool():
    try:
        resp = requests.get(f"{ENGINE_URL}/proxy_pool", timeout=ENGINE_TIMEOUT)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/proxy_pool/batch_add", methods=["POST"])
@login_required
def api_proxy_batch_add():
    try:
        data = request.get_json(force=True, silent=True) or {}
        resp = requests.post(f"{ENGINE_URL}/proxy_pool/batch_add", json=data, timeout=30)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/proxy_pool/redistribute", methods=["POST"])
@login_required
def api_proxy_redistribute():
    try:
        data = request.get_json(force=True, silent=True) or {}
        resp = requests.post(f"{ENGINE_URL}/proxy_pool/redistribute", json=data, timeout=60)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

'''
    if "/api/proxy_pool/redistribute" not in s:
        s = s.replace(
            "if __name__ == '__main__':",
            block + "\nif __name__ == '__main__':",
            1,
        )
        open(path, "w", encoding="utf-8").write(s)
        print("OK 已修改 panel_app.py")
    else:
        print("panel_app.py 已是目标状态")

    import py_compile

    py_compile.compile(path, doraise=True)
    print("panel_app 语法 OK")


HTML_BLOCK = '''
    <div class="lines-section">
        <h3 style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
            <span>代理IP池 / 线路</span>
            <span>
                <button class="btn btn-batch" onclick="showProxyAddModal()">批量添加IP</button>
                <button class="btn btn-check" onclick="redistributeProxies()">一键均匀分配</button>
                <button class="btn btn-refresh" onclick="refreshStatus()">刷新</button>
            </span>
        </h3>
        <div class="lines-grid" id="lines-display"></div>
    </div>
    <div id="proxy-add-modal" class="modal" style="display:none;align-items:center;justify-content:center">
        <div class="modal-content" style="max-width:520px">
            <h3 style="color:#00d4ff;margin-bottom:12px">批量添加代理IP</h3>
            <p style="color:#8899aa;font-size:12px;margin-bottom:8px">每行一条。只追加新线路，不改已有Bot的IP。</p>
            <textarea id="proxy-batch-text" rows="8" style="width:100%;padding:10px;background:#1a2332;border:1px solid #2c3e50;color:#fff;border-radius:4px" placeholder="socks5://user:pass@1.2.3.4:9270"></textarea>
            <div style="margin:10px 0">
                <label style="color:#aaa;font-size:12px">默认账号 user:pass（可选）</label>
                <input id="proxy-default-auth" type="text" style="width:100%;padding:8px;background:#1a2332;border:1px solid #2c3e50;color:#fff;border-radius:4px">
            </div>
            <div class="modal-actions">
                <button class="btn btn-refresh" onclick="document.getElementById('proxy-add-modal').style.display='none'">取消</button>
                <button class="btn btn-add" onclick="submitProxyBatch()">确认添加</button>
            </div>
        </div>
    </div>
'''

JS_BLOCK = '''
        function showProxyAddModal() {
            var el = document.getElementById('proxy-add-modal');
            if (el) el.style.display = 'flex';
        }
        async function submitProxyBatch() {
            var textEl = document.getElementById('proxy-batch-text');
            var authEl = document.getElementById('proxy-default-auth');
            if (!textEl) { alert('页面缺少输入框'); return; }
            var text = textEl.value.trim();
            var default_auth = authEl ? authEl.value.trim() : '';
            if (!text) { alert('请粘贴代理列表'); return; }
            try {
                var result = await fetchAPI((typeof API_BASE !== 'undefined' ? API_BASE : '') + '/api/proxy_pool/batch_add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ proxies_text: text, default_auth: default_auth })
                });
                if (result.error || result.ok === false) {
                    alert('添加失败: ' + (result.error || JSON.stringify(result)));
                    return;
                }
                alert('已追加 ' + result.added + ' 条新线路（未改现有Bot IP）');
                textEl.value = '';
                var modal = document.getElementById('proxy-add-modal');
                if (modal) modal.style.display = 'none';
                refreshStatus();
            } catch (e) {
                alert('添加失败: ' + e.message);
            }
        }
        async function redistributeProxies() {
            if (!confirm('将按启用线路均匀重切编号，并更新每个Bot的line/proxy。\\n不会删除Bot，不会重挂Webhook。\\n确认？')) return;
            try {
                var result = await fetchAPI((typeof API_BASE !== 'undefined' ? API_BASE : '') + '/api/proxy_pool/redistribute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({})
                });
                if (result.error || result.ok === false) {
                    alert('分配失败: ' + (result.error || JSON.stringify(result)));
                    return;
                }
                alert('完成：' + result.lines + ' 条线路，每线约 ' + result.cap_per_line + '，更新 ' + result.bots_updated + ' 个Bot');
                refreshStatus();
            } catch (e) {
                alert('分配失败: ' + e.message);
            }
        }
'''


def patch_html(rel):
    path = os.path.join(BASE, rel)
    if not os.path.isfile(path):
        print("跳过", rel)
        return
    h = open(path, encoding="utf-8").read()

    # 清理曾手改截断的坏函数
    h = re.sub(
        r"async function submitProxyBatch\s*\([\s\S]*?\n\s*\}\s*(?=\n\s*</script>|\n\s*function |\n\s*async function )",
        "",
        h,
        count=3,
    )
    h = re.sub(r"function showProxyAddModal\s*\([\s\S]*?\n\s*\}\s*", "", h, count=3)
    h = re.sub(r"async function redistributeProxies\s*\([\s\S]*?\n\s*\}\s*", "", h, count=3)

    if "proxy-add-modal" not in h:
        if re.search(
            r'<div class="lines-section">[\s\S]*?</div>\s*(?=<div class="check-section">)',
            h,
        ):
            h = re.sub(
                r'<div class="lines-section">[\s\S]*?</div>\s*(?=<div class="check-section">)',
                HTML_BLOCK + "\n    ",
                h,
                count=1,
            )
        elif '<div class="check-section">' in h:
            h = h.replace(
                '<div class="check-section">',
                HTML_BLOCK + '\n    <div class="check-section">',
                1,
            )
        else:
            print("警告: 未找到 lines-section/check-section", rel)

    # 动态线路
    h2, n = re.subn(
        r"for\s*\(\s*let\s+i\s*=\s*1;\s*i\s*<=\s*10;\s*i\+\+\s*\)\s*\{[\s\S]*?linesDiv\.innerHTML\s*=\s*linesHTML;",
        """const ids = Object.keys(lines).map(Number).sort(function(a,b){return a-b;});
            for (var _i=0; _i<ids.length; _i++) {
                var i = ids[_i];
                var line = lines[String(i)];
                if (!line) continue;
                linesHTML += '<div class="line-tag line-' + i + '">'
                    + '<span class="line-name">' + i + '号线</span>'
                    + '<span class="line-info">编号 ' + line.range_start + '-' + line.range_end + '</span>'
                    + '<span class="line-info">' + line.proxy + '</span>'
                    + '<span class="line-info">[' + line.bot_count + '/' + line.max_bots + ']</span></div>';
            }
            linesDiv.innerHTML = linesHTML || '<div style="color:#8899aa">暂无线路</div>';""",
        h,
        count=1,
    )
    if n:
        h = h2

    if "function showProxyAddModal" not in h:
        if "</script>" in h:
            h = h.replace("</script>", JS_BLOCK + "\n    </script>", 1)
        else:
            print("警告: 无 </script>", rel)

    open(path, "w", encoding="utf-8").write(h)
    print("OK", rel)


def main():
    os.chdir(BASE)
    print("工作目录:", BASE)
    backup(
        [
            "bot_engine.py",
            "panel_app.py",
            "index.html",
            "frontend/index.html",
            MOD_NAME,
        ]
    )
    ensure_module()
    patch_bot_engine()
    patch_panel_app()
    patch_html("index.html")
    patch_html("frontend/index.html")
    print("")
    print("安装完成。请执行:")
    print("  pkill -f bot_engine.py; nohup python3 bot_engine.py >> logs/engine.log 2>&1 &")
    print("  pkill -f panel_app.py;  nohup python3 panel_app.py  >> logs/panel.log 2>&1 &")
    print("  sleep 5; grep Webhook注册完成 logs/engine.log | tail -3")
    print("  curl -s http://127.0.0.1:8899/proxy_pool | head -c 300; echo")


if __name__ == "__main__":
    main()
