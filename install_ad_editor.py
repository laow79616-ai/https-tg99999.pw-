#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装广告编辑器（按线路 + 面板配置）
- 不删 Bot、不改代理池
- 兼容旧 ad_config.json
在服务器:
  cd /root/bot_panel
  python3 install_ad_editor.py
  重启 bot_engine + panel_app
"""
from __future__ import annotations

import base64
import os
import re
import shutil
import sys
from datetime import datetime

BASE = "/root/bot_panel"
if not os.path.isdir(BASE):
    BASE = os.path.dirname(os.path.abspath(__file__))

MOD_NAME = "ad_mod.py"

# 模块源码由同目录文件读取；若缺失则报错
def ensure_module():
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), MOD_NAME)
    if not os.path.isfile(src):
        src = os.path.join(BASE, MOD_NAME)
    dst = os.path.join(BASE, MOD_NAME)
    if os.path.isfile(src):
        shutil.copy2(src, dst)
        print("已安装", dst)
    elif os.path.isfile(dst):
        print("模块已存在", dst)
    else:
        print("错误: 需要 ad_mod.py")
        sys.exit(1)


def backup(files):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = os.path.join(BASE, f"backup_ad_{ts}")
    os.makedirs(bak, exist_ok=True)
    for f in files:
        p = os.path.join(BASE, f)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(bak, f.replace("/", "_")))
    print("备份:", bak)


def patch_bot_engine():
    path = os.path.join(BASE, "bot_engine.py")
    s = open(path, encoding="utf-8").read()
    changed = False

    if "import ad_mod" not in s:
        s = s.replace("from aiohttp import web\n", "from aiohttp import web\nimport ad_mod\n", 1)
        changed = True

    # load_ad_config 改为用 ad_mod 并保留 self.ad_store
    if "self.ad_store" not in s:
        s = s.replace(
            "self.ad_config = {}",
            "self.ad_config = {}\n        self.ad_store = {}",
            1,
        )
        changed = True

    if "ad_mod.load_store" not in s:
        new_load = '''
    def load_ad_config(self):
        """加载广告：支持全局 default + 按线路 by_line（兼容旧配置）"""
        try:
            self.ad_store = ad_mod.load_store(AD_CONFIG_FILE)
            self.ad_config = ad_mod.normalize_ad(self.ad_store.get("default") or {})
            logger.info(
                "加载广告配置: default=%s text_len=%s lines=%s",
                self.ad_config.get("name", ""),
                len(self.ad_config.get("text") or ""),
                len(self.ad_store.get("by_line") or {}),
            )
        except Exception as e:
            logger.error(f"加载广告配置失败: {e}")
'''
        s = re.sub(
            r"    def load_ad_config\(self\):[\s\S]*?(?=\n    def )",
            new_load + "\n",
            s,
            count=1,
        )
        changed = True

    # reload
    if "ad_mod.load_store" in s and "async def reload_ad_config" in s:
        s2 = re.sub(
            r"    async def reload_ad_config\(self\):[\s\S]*?(?=\n    async def |\n    def )",
            '''    async def reload_ad_config(self):
        """重新加载广告配置"""
        try:
            self.ad_store = ad_mod.load_store(AD_CONFIG_FILE)
            self.ad_config = ad_mod.normalize_ad(self.ad_store.get("default") or {})
            logger.info("广告配置已重新加载")
        except Exception as e:
            logger.error(f"重新加载广告配置失败: {e}")

''',
            s,
            count=1,
        )
        if s2 != s:
            s = s2
            changed = True

    # send_ad_to_chat: 增加 line_id 参数并从 store 取广告
    if "get_ad_for_line" not in s:
        # 修改函数签名与取 caption 逻辑入口
        if "async def send_ad_to_chat(self, token, proxy_url, chat_id):" in s:
            s = s.replace(
                "async def send_ad_to_chat(self, token, proxy_url, chat_id):",
                "async def send_ad_to_chat(self, token, proxy_url, chat_id, line_id=None):",
                1,
            )
            changed = True
        # 在取 caption 前注入 ad 解析
        needle = "client = await self.get_client(proxy_url)\n            caption = self.ad_config.get('text', '')\n            buttons = self.ad_config.get('buttons', [])"
        repl = """client = await self.get_client(proxy_url)
            store = getattr(self, 'ad_store', None) or ad_mod.load_store(AD_CONFIG_FILE)
            ad = ad_mod.get_ad_for_line(store, line_id)
            caption = ad_mod.caption_of(ad) or (self.ad_config.get('text') or '')
            buttons = ad.get('buttons') or self.ad_config.get('buttons', [])
            photo_path = ad_mod.resolve_media_path(ad.get('photo') or '')
            video_path = ad_mod.resolve_media_path(ad.get('video') or '')"""
        if needle in s:
            s = s.replace(needle, repl, 1)
            changed = True
        # 发送媒体：优先 video → photo 文件 → AD_IMAGE_FILE → 纯文字
        old_media = "if os.path.exists(AD_IMAGE_FILE):"
        # only first occurrence inside send_ad_to_chat - careful
        if "video_path" in s and "sendVideo" not in s:
            # replace the AD_IMAGE_FILE block start
            idx = s.find("photo_path = ad_mod.resolve_media_path")
            if idx > 0:
                # find if os.path.exists(AD_IMAGE_FILE) after that
                j = s.find("if os.path.exists(AD_IMAGE_FILE):", idx)
                if j > 0:
                    s = (
                        s[:j]
                        + """if video_path and os.path.exists(video_path):
                url = f"https://api.telegram.org/bot{token}/sendVideo"
                with open(video_path, 'rb') as vf:
                    files = {'video': (os.path.basename(video_path), vf)}
                    data = {'chat_id': str(chat_id), 'caption': caption}
                    if inline_keyboard:
                        data['reply_markup'] = json.dumps({"inline_keyboard": inline_keyboard})
                    resp = await client.post(url, data=data, files=files)
                    result = resp.json()
            elif photo_path and os.path.exists(photo_path):
                url = f"https://api.telegram.org/bot{token}/sendPhoto"
                with open(photo_path, 'rb') as img:
                    files = {'photo': (os.path.basename(photo_path), img)}
                    data = {'chat_id': str(chat_id), 'caption': caption}
                    if inline_keyboard:
                        data['reply_markup'] = json.dumps({"inline_keyboard": inline_keyboard})
                    resp = await client.post(url, data=data, files=files)
                    result = resp.json()
            elif os.path.exists(AD_IMAGE_FILE):"""
                        + s[j + len("if os.path.exists(AD_IMAGE_FILE):") :]
                    )
                    changed = True

    # 调用 send_ad_to_chat 时传入 line
    if "send_ad_to_chat(token, proxy_url, chat_id, line_id=" not in s:
        # handle_webhook 内有 number
        s2 = s.replace(
            "await self.send_ad_to_chat(token, proxy_url, chat_id)",
            "await self.send_ad_to_chat(token, proxy_url, chat_id, line_id=get_line_for_number(number))",
        )
        # send_welcome 里 number 变量名可能是 bot_number
        s2 = s2.replace(
            "await self.send_ad_to_chat(token, proxy_url, chat_id, line_id=get_line_for_number(number))",
            "await self.send_ad_to_chat(token, proxy_url, chat_id, line_id=get_line_for_number(number))",
        )
        # fix welcome: uses bot_number
        s2 = re.sub(
            r"(async def send_welcome\(self, token, proxy_url, chat_id, bot_number\):[\s\S]{0,800}?)await self\.send_ad_to_chat\(token, proxy_url, chat_id, line_id=get_line_for_number\(number\)\)",
            r"\1await self.send_ad_to_chat(token, proxy_url, chat_id, line_id=get_line_for_number(bot_number))",
            s2,
            count=1,
        )
        if s2 != s:
            s = s2
            changed = True

    # API handlers
    handlers = '''
    async def handle_ad_get(self, request):
        store = ad_mod.load_store(AD_CONFIG_FILE)
        self.ad_store = store
        return web.json_response(ad_mod.list_summary(store))

    async def handle_ad_save(self, request):
        data = await request.json()
        ad = data.get("ad") or data
        as_default = bool(data.get("as_default", True))
        line_ids = data.get("line_ids") or data.get("lines") or []
        line_ids = [int(x) for x in line_ids]
        store = ad_mod.load_store(AD_CONFIG_FILE)
        result = ad_mod.save_ad(store, ad, as_default=as_default, line_ids=line_ids or None)
        self.ad_store = ad_mod.load_store(AD_CONFIG_FILE)
        self.ad_config = ad_mod.normalize_ad(self.ad_store.get("default") or {})
        return web.json_response(result)

    async def handle_ad_clear_lines(self, request):
        data = await request.json()
        line_ids = [int(x) for x in (data.get("line_ids") or [])]
        store = ad_mod.load_store(AD_CONFIG_FILE)
        result = ad_mod.clear_line_ads(store, line_ids)
        self.ad_store = ad_mod.load_store(AD_CONFIG_FILE)
        return web.json_response(result)

    async def handle_ad_upload(self, request):
        """上传广告图片/视频到 data/ad_media/"""
        reader = await request.multipart()
        field = await reader.next()
        if field is None:
            return web.json_response({"ok": False, "error": "no file"}, status=400)
        filename = field.filename or "upload.bin"
        ext = os.path.splitext(filename)[1].lower() or ".bin"
        os.makedirs(ad_mod.AD_MEDIA_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = f"ad_{ts}{ext}"
        dest = os.path.join(ad_mod.AD_MEDIA_DIR, safe)
        size = 0
        with open(dest, "wb") as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                size += len(chunk)
                f.write(chunk)
        kind = "video" if ext in (".mp4", ".mov", ".webm") else "photo"
        return web.json_response({"ok": True, "path": dest, "kind": kind, "size": size, "name": safe})

'''
    if "handle_ad_save" not in s:
        s = s.replace(
            "async def handle_status(self, request):",
            handlers + "\n    async def handle_status(self, request):",
            1,
        )
        changed = True

    if "/ad/save" not in s:
        s = s.replace(
            "app.router.add_get('/status', engine.handle_status)",
            "app.router.add_get('/status', engine.handle_status)\n"
            "    app.router.add_get('/ad', engine.handle_ad_get)\n"
            "    app.router.add_post('/ad/save', engine.handle_ad_save)\n"
            "    app.router.add_post('/ad/clear_lines', engine.handle_ad_clear_lines)\n"
            "    app.router.add_post('/ad/upload', engine.handle_ad_upload)",
            1,
        )
        changed = True

    if changed:
        open(path, "w", encoding="utf-8").write(s)
        print("OK bot_engine.py")
    else:
        print("bot_engine 无需改或已打过补丁")

    import py_compile

    py_compile.compile(path, doraise=True)
    print("bot_engine 语法 OK")


def patch_panel():
    path = os.path.join(BASE, "panel_app.py")
    s = open(path, encoding="utf-8").read()
    block = '''

@app.route("/api/ad")
@login_required
def api_ad_get():
    try:
        resp = requests.get(f"{ENGINE_URL}/ad", timeout=ENGINE_TIMEOUT)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ad/save", methods=["POST"])
@login_required
def api_ad_save():
    try:
        data = request.get_json(force=True, silent=True) or {}
        resp = requests.post(f"{ENGINE_URL}/ad/save", json=data, timeout=30)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ad/clear_lines", methods=["POST"])
@login_required
def api_ad_clear_lines():
    try:
        data = request.get_json(force=True, silent=True) or {}
        resp = requests.post(f"{ENGINE_URL}/ad/clear_lines", json=data, timeout=15)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ad/upload", methods=["POST"])
@login_required
def api_ad_upload():
    try:
        if "file" not in request.files and "photo" not in request.files:
            return jsonify({"error": "no file"}), 400
        f = request.files.get("file") or request.files.get("photo")
        files = {"file": (f.filename, f.stream, f.mimetype or "application/octet-stream")}
        resp = requests.post(f"{ENGINE_URL}/ad/upload", files=files, timeout=120)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

'''
    if "/api/ad/save" not in s:
        s = s.replace("if __name__ == '__main__':", block + "\nif __name__ == '__main__':", 1)
        open(path, "w", encoding="utf-8").write(s)
        print("OK panel_app.py")
    else:
        print("panel_app 已有广告路由")
    import py_compile

    py_compile.compile(path, doraise=True)
    print("panel 语法 OK")


AD_UI = '''
    <div class="lines-section" id="ad-editor-section" style="margin-top:16px">
        <h3 style="color:#00d4ff">广告编辑器（全局默认 / 按线路）</h3>
        <p style="color:#8899aa;font-size:12px;margin-bottom:10px">改完保存即对所选线路生效；用户再互动会收到新广告。不删Bot、不重挂Webhook。</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div>
                <label style="color:#aaa;font-size:12px">标题</label>
                <input id="ad-title" style="width:100%;padding:8px;background:#1a2332;border:1px solid #2c3e50;color:#fff;border-radius:4px;margin-bottom:8px">
                <label style="color:#aaa;font-size:12px">文案</label>
                <textarea id="ad-text" rows="8" style="width:100%;padding:8px;background:#1a2332;border:1px solid #2c3e50;color:#fff;border-radius:4px"></textarea>
                <label style="color:#aaa;font-size:12px;display:block;margin-top:8px">按钮（每行：按钮文字 | https://链接）</label>
                <textarea id="ad-buttons" rows="4" style="width:100%;padding:8px;background:#1a2332;border:1px solid #2c3e50;color:#fff;border-radius:4px" placeholder="访问官网 | https://www.kuaiyue.vip"></textarea>
            </div>
            <div>
                <label style="color:#aaa;font-size:12px">图片路径（上传后自动填）</label>
                <input id="ad-photo" style="width:100%;padding:8px;background:#1a2332;border:1px solid #2c3e50;color:#fff;border-radius:4px;margin-bottom:8px">
                <input type="file" id="ad-photo-file" accept="image/*" style="color:#ccc;margin-bottom:8px">
                <label style="color:#aaa;font-size:12px">视频路径（可选）</label>
                <input id="ad-video" style="width:100%;padding:8px;background:#1a2332;border:1px solid #2c3e50;color:#fff;border-radius:4px;margin-bottom:8px">
                <input type="file" id="ad-video-file" accept="video/*" style="color:#ccc;margin-bottom:8px">
                <label style="color:#aaa;font-size:12px">应用到线路（多选，空=只改全局默认）</label>
                <div id="ad-line-checks" style="max-height:120px;overflow:auto;background:#1a2332;padding:8px;border-radius:4px;margin-bottom:8px;color:#ddd;font-size:12px"></div>
                <label style="color:#aaa;font-size:12px"><input type="checkbox" id="ad-as-default" checked> 同时设为全局默认</label>
                <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
                    <button class="btn btn-add" onclick="saveAdConfig()">保存广告</button>
                    <button class="btn btn-refresh" onclick="loadAdConfig()">刷新</button>
                    <button class="btn btn-check" onclick="clearSelectedLineAds()">清除所选线路专属（回退默认）</button>
                </div>
                <div id="ad-save-msg" style="color:#8f8;font-size:12px;margin-top:8px"></div>
            </div>
        </div>
    </div>
'''

AD_JS = '''
        async function loadAdConfig() {
            try {
                var data = await fetchAPI((typeof API_BASE!=='undefined'?API_BASE:'') + '/api/ad');
                if (data.error) { alert(data.error); return; }
                var d = data.default || {};
                document.getElementById('ad-title').value = d.title || '';
                document.getElementById('ad-text').value = d.text || '';
                document.getElementById('ad-photo').value = d.photo || '';
                document.getElementById('ad-video').value = d.video || '';
                var btns = d.buttons || [];
                var lines = [];
                btns.forEach(function(row) {
                    (row || []).forEach(function(b) {
                        lines.push((b.text || '') + ' | ' + (b.url || ''));
                    });
                });
                document.getElementById('ad-buttons').value = lines.join('\\n');
                var box = document.getElementById('ad-line-checks');
                if (box) {
                    var html = '';
                    for (var i = 1; i <= 30; i++) {
                        var tag = (data.by_line && data.by_line[String(i)]) ? ' [有专属]' : '';
                        html += '<label style="margin-right:10px;display:inline-block"><input type="checkbox" class="ad-line-cb" value="'+i+'"> '+i+'号线'+tag+'</label>';
                    }
                    box.innerHTML = html;
                }
            } catch (e) { console.log(e); }
        }
        function parseAdButtons() {
            var text = document.getElementById('ad-buttons').value || '';
            var rows = [];
            text.split('\\n').forEach(function(line) {
                line = line.trim();
                if (!line) return;
                var parts = line.split('|');
                if (parts.length < 2) return;
                var t = parts[0].trim();
                var u = parts.slice(1).join('|').trim();
                if (t && u) rows.push([{text: t, url: u}]);
            });
            return rows;
        }
        async function uploadAdFile(inputId, targetId) {
            var inp = document.getElementById(inputId);
            if (!inp || !inp.files || !inp.files[0]) return;
            var fd = new FormData();
            fd.append('file', inp.files[0]);
            var resp = await fetch((typeof API_BASE!=='undefined'?API_BASE:'') + '/api/ad/upload', { method: 'POST', body: fd, credentials: 'same-origin' });
            var data = await resp.json();
            if (data.path) document.getElementById(targetId).value = data.path;
            else alert('上传失败: ' + (data.error || JSON.stringify(data)));
        }
        async function saveAdConfig() {
            var line_ids = [];
            document.querySelectorAll('.ad-line-cb:checked').forEach(function(cb){ line_ids.push(parseInt(cb.value,10)); });
            var payload = {
                as_default: document.getElementById('ad-as-default').checked,
                line_ids: line_ids,
                ad: {
                    name: 'panel_ad',
                    title: document.getElementById('ad-title').value.trim(),
                    text: document.getElementById('ad-text').value,
                    photo: document.getElementById('ad-photo').value.trim(),
                    video: document.getElementById('ad-video').value.trim(),
                    buttons: parseAdButtons()
                }
            };
            try {
                var result = await fetchAPI((typeof API_BASE!=='undefined'?API_BASE:'') + '/api/ad/save', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                document.getElementById('ad-save-msg').textContent = result.ok ? ('已保存 ' + (result.lines && result.lines.length ? ('线路 '+result.lines.join(',')) : '全局默认')) : JSON.stringify(result);
                loadAdConfig();
            } catch (e) { alert(e.message); }
        }
        async function clearSelectedLineAds() {
            var line_ids = [];
            document.querySelectorAll('.ad-line-cb:checked').forEach(function(cb){ line_ids.push(parseInt(cb.value,10)); });
            if (!line_ids.length) { alert('请先勾选线路'); return; }
            if (!confirm('清除线路专属广告，恢复用全局默认？')) return;
            await fetchAPI((typeof API_BASE!=='undefined'?API_BASE:'') + '/api/ad/clear_lines', {
                method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({line_ids: line_ids})
            });
            loadAdConfig();
        }
        document.addEventListener('DOMContentLoaded', function() {
            var pf = document.getElementById('ad-photo-file');
            var vf = document.getElementById('ad-video-file');
            if (pf) pf.addEventListener('change', function(){ uploadAdFile('ad-photo-file', 'ad-photo'); });
            if (vf) vf.addEventListener('change', function(){ uploadAdFile('ad-video-file', 'ad-video'); });
            if (document.getElementById('ad-editor-section')) loadAdConfig();
        });
'''


def patch_html(rel):
    path = os.path.join(BASE, rel)
    if not os.path.isfile(path):
        return
    h = open(path, encoding="utf-8").read()
    if "ad-editor-section" not in h:
        if "代理IP池" in h or "lines-section" in h:
            # 插在 check-section 前
            if '<div class="check-section">' in h:
                h = h.replace(
                    '<div class="check-section">',
                    AD_UI + '\n    <div class="check-section">',
                    1,
                )
            else:
                h = h.replace("</body>", AD_UI + "\n</body>", 1)
        else:
            h = h.replace("</body>", AD_UI + "\n</body>", 1)
    if "function loadAdConfig" not in h:
        h = h.replace("</script>", AD_JS + "\n    </script>", 1)
    open(path, "w", encoding="utf-8").write(h)
    print("OK", rel)


def main():
    os.chdir(BASE)
    backup(["bot_engine.py", "panel_app.py", "index.html", "frontend/index.html", "data/ad_config.json"])
    ensure_module()
    patch_bot_engine()
    patch_panel()
    patch_html("frontend/index.html")
    patch_html("index.html")
    print("完成。重启:")
    print("  pkill -f bot_engine.py; nohup python3 bot_engine.py >> logs/engine.log 2>&1 &")
    print("  pkill -f panel_app.py;  nohup python3 panel_app.py  >> logs/panel.log 2>&1 &")


if __name__ == "__main__":
    main()
