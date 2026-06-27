# 分布式机器人管理系统

分布式 Telegram Bot 管理面板，支持批量管理、代理分配、自动简介设置等功能。

## 功能特性

- 支持 300 个 Bot 管理
- 18 条代理线路自动分配
- 20 个 Telegram API 轮换
- 一键自检、批量添加、自动设置简介
- 广告发送统计
- 登录验证保护

## 部署说明

### 环境要求

- Python 3.9+
- Flask
- httpx / aiohttp

### 安装

```bash
pip install -r requirements.txt
```

### 运行

```bash
# 启动 Bot 引擎（端口 8899）
python3 bot_engine.py

# 启动面板（端口 5000）
python3 panel_app.py
```

### 登录凭据

- 用户名：`admin`
- 密码：`Ab123456987`

## 文件结构

```
bot_panel/
├── bot_engine.py       # Bot 引擎核心（polling、消息处理、API调用）
├── panel_app.py        # Flask 面板前端（含登录验证）
├── frontend/
│   └── index.html      # 前端页面
├── data/
│   ├── bots_config.json      # Bot 配置
│   ├── profile_config.json   # 简介配置
│   ├── api_config.json       # API 配置
│   ├── ad_config.json        # 广告配置
│   └── photos/               # Bot 头像图片
└── requirements.txt
```

## 域名

- 面板地址：https://tg99999.pw/
