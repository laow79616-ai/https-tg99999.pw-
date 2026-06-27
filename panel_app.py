#!/usr/bin/env python3
"""
分布式机器人管理面板 - Flask前端
连接Bot引擎(8899端口)获取数据
支持300个Bot，10条代理线路
增加登录验证功能
"""
from flask import Flask, jsonify, request, send_from_directory, session, redirect, url_for, render_template_string
import requests
import json
import os
import time
import hashlib
from functools import wraps, lru_cache

app = Flask(__name__, static_folder='/root/bot_panel/frontend')
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB
app.secret_key = 'bot_panel_secret_key_2026_tg99999'

ENGINE_URL = "http://127.0.0.1:8899"
ENGINE_TIMEOUT = 5  # 引擎在本地，5秒足够

# 登录凭据
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Ab123456987"

# 缓存状态数据（避免频繁请求引擎）
_status_cache = {"data": None, "time": 0}
CACHE_TTL = 3  # 缓存3秒

# ============ 登录验证 ============

LOGIN_PAGE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>分布式机器人管理系统 - 登录</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: rgba(30, 30, 50, 0.95);
            border: 1px solid rgba(0, 188, 212, 0.3);
            border-radius: 12px;
            padding: 40px;
            width: 380px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }
        .login-title {
            text-align: center;
            color: #00bcd4;
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 30px;
        }
        .login-subtitle {
            text-align: center;
            color: #888;
            font-size: 13px;
            margin-top: -20px;
            margin-bottom: 25px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            color: #aaa;
            font-size: 13px;
            margin-bottom: 6px;
        }
        .form-group input {
            width: 100%;
            padding: 12px 15px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 6px;
            color: #fff;
            font-size: 15px;
            outline: none;
            transition: border-color 0.3s;
        }
        .form-group input:focus {
            border-color: #00bcd4;
        }
        .login-btn {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #00bcd4, #0097a7);
            border: none;
            border-radius: 6px;
            color: #fff;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: opacity 0.3s;
            margin-top: 10px;
        }
        .login-btn:hover {
            opacity: 0.9;
        }
        .error-msg {
            color: #ff5252;
            text-align: center;
            font-size: 13px;
            margin-top: 15px;
            display: {{ "block" if error else "none" }};
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1 class="login-title">分布式机器人管理系统</h1>
        <p class="login-subtitle">请输入管理员账号登录</p>
        <form method="POST" action="/login">
            <div class="form-group">
                <label>用户名</label>
                <input type="text" name="username" placeholder="请输入用户名" required autofocus>
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" name="password" placeholder="请输入密码" required>
            </div>
            <button type="submit" class="login-btn">登 录</button>
            <p class="error-msg">{{ error or "" }}</p>
        </form>
    </div>
</body>
</html>
'''


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            session['login_time'] = time.time()
            return redirect('/')
        else:
            return render_template_string(LOGIN_PAGE, error="用户名或密码错误")
    return render_template_string(LOGIN_PAGE, error=None)


@app.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    return redirect('/login')


# ============ 引擎状态 ============

def get_engine_status():
    """从引擎获取状态（带缓存）"""
    now = time.time()
    if _status_cache["data"] and (now - _status_cache["time"]) < CACHE_TTL:
        return _status_cache["data"]
    
    try:
        resp = requests.get(f"{ENGINE_URL}/status", timeout=ENGINE_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            _status_cache["data"] = data
            _status_cache["time"] = now
            return data
    except Exception as e:
        app.logger.error(f"引擎连接失败: {e}")
    
    # 引擎离线时返回空数据
    if _status_cache["data"]:
        return _status_cache["data"]
    
    return {
        "status": "offline",
        "total_bots": 0,
        "max_bots": 300,
        "lines": {},
        "stats": {"total_sent": 0, "total_success": 0, "total_failed": 0,
                  "today_sent": 0, "today_success": 0, "today_failed": 0}
    }


# ============ 页面路由 ============

@app.route('/')
@login_required
def index():
    return send_from_directory('/root/bot_panel/frontend', 'index.html')


# ============ API路由 ============

@app.route('/api/status')
@login_required
def api_status():
    """获取完整状态"""
    return jsonify(get_engine_status())


@app.route('/api/stats')
@login_required
def api_stats():
    """获取统计数据"""
    status = get_engine_status()
    return jsonify(status.get('stats', {}))


@app.route('/api/add_bot', methods=['POST'])
@login_required
def api_add_bot():
    """添加单个Bot"""
    data = request.json
    try:
        resp = requests.post(f"{ENGINE_URL}/add_bot", json=data, timeout=15)
        _status_cache["data"] = None  # 清除缓存
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": f"引擎连接失败: {str(e)}"}), 500


@app.route('/api/batch_add', methods=['POST'])
@login_required
def api_batch_add():
    """批量添加Bot"""
    data = request.json
    try:
        resp = requests.post(f"{ENGINE_URL}/batch_add", json=data, timeout=60)
        _status_cache["data"] = None
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": f"引擎连接失败: {str(e)}"}), 500


@app.route('/api/remove_bot', methods=['POST'])
@login_required
def api_remove_bot():
    """删除Bot"""
    data = request.json
    try:
        resp = requests.post(f"{ENGINE_URL}/remove_bot", json=data, timeout=10)
        _status_cache["data"] = None
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/start_all', methods=['POST'])
@login_required
def api_start_all():
    """启动所有Bot"""
    try:
        resp = requests.post(f"{ENGINE_URL}/start_all", timeout=10)
        _status_cache["data"] = None
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stop_all', methods=['POST'])
@login_required
def api_stop_all():
    """停止所有Bot"""
    try:
        resp = requests.post(f"{ENGINE_URL}/stop_all", timeout=10)
        _status_cache["data"] = None
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/check_all', methods=['POST'])
@login_required
def api_check_all():
    """一键自检"""
    try:
        resp = requests.post(f"{ENGINE_URL}/check_all", timeout=300)
        _status_cache["data"] = None
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/send', methods=['POST'])
@login_required
def api_send():
    """发送消息"""
    data = request.json
    try:
        resp = requests.post(f"{ENGINE_URL}/send", json=data, timeout=30)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/upload_photo', methods=['POST'])
@login_required
def api_upload_photo():
    """上传Bot头像图片"""
    if 'photo' not in request.files:
        return jsonify({"ok": False, "error": "没有选择图片"}), 400
    
    photo = request.files['photo']
    batch_size = int(request.form.get('batch_size', 50))
    
    # 保存图片
    import time as _time
    filename = f"bot_photo_{int(_time.time())}.jpg"
    save_path = f"/root/bot_panel/data/{filename}"
    photo.save(save_path)
    
    # 转发给引擎处理
    try:
        import io
        photo.seek(0)
        files = {'photo': (filename, open(save_path, 'rb'), 'image/jpeg')}
        data = {'batch_size': str(batch_size)}
        resp = requests.post(f"{ENGINE_URL}/upload_photo", files=files, data=data, timeout=300)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"ok": True, "message": f"图片已保存到 {save_path}", "path": save_path})


@app.route('/api/set_profile', methods=['POST'])
@login_required
def api_set_profile():
    """一键修改Bot头像和简介"""
    data = request.json or {}
    try:
        resp = requests.post(f"{ENGINE_URL}/set_profile", json=data, timeout=300)
        _status_cache["data"] = None
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": f"引擎连接失败: {str(e)}"}), 500


@app.route('/api/reset_stats', methods=['POST'])
@login_required
def api_reset_stats():
    """重置统计"""
    try:
        resp = requests.post(f"{ENGINE_URL}/reset_stats", timeout=5)
        _status_cache["data"] = None
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/profile_progress')
@login_required
def api_profile_progress():
    """查询set_profile进度"""
    try:
        resp = requests.get(f"{ENGINE_URL}/profile_progress", timeout=5)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/save_profile_config', methods=['POST'])
@login_required
def api_save_profile_config():
    """保存简介配置到文件"""
    import json, os
    try:
        data = request.get_json()
        config_path = '/root/bot_panel/data/profile_config.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/load_profile_config')
@login_required
def api_load_profile_config():
    """加载简介配置"""
    import json, os
    config_path = '/root/bot_panel/data/profile_config.json'
    photos_dir = '/root/bot_panel/data/photos'
    config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    # 获取已上传的图片列表
    photos = []
    if os.path.exists(photos_dir):
        photos = sorted([p for p in os.listdir(photos_dir) if p.endswith(('.jpg', '.png', '.jpeg'))])
    config['photos'] = photos
    config['photos_count'] = len(photos)
    return jsonify(config)


@app.route('/api/upload_photos', methods=['POST'])
@login_required
def api_upload_photos():
    """上传多张头像图片，直接保存到本地"""
    import os
    photos_dir = '/root/bot_panel/data/photos'
    os.makedirs(photos_dir, exist_ok=True)
    try:
        files = request.files.getlist('photos')
        if not files:
            return jsonify({"error": "没有选择文件"}), 400
        saved = 0
        for f in files:
            if f.filename:
                safe_name = f'photo_{saved+1:03d}.jpg'
                filepath = os.path.join(photos_dir, safe_name)
                f.save(filepath)
                saved += 1
        all_photos = sorted([p for p in os.listdir(photos_dir) if p.endswith(('.jpg', '.png', '.jpeg'))])
        return jsonify({
            "ok": True,
            "saved": saved,
            "total_photos": len(all_photos),
            "photos": all_photos
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/list_photos')
@login_required
def api_list_photos():
    """列出已上传的头像图片"""
    try:
        resp = requests.get(f"{ENGINE_URL}/list_photos", timeout=5)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/api/check_result')
@login_required
def api_check_result():
    """获取最近一次自动检测结果"""
    try:
        resp = requests.get(f"{ENGINE_URL}/check_result", timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/manual_check', methods=['POST'])
@login_required
def api_manual_check():
    """手动触发一次Bot检测"""
    try:
        resp = requests.post(f"{ENGINE_URL}/manual_check", timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
