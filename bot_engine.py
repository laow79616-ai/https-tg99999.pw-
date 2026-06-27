#!/usr/bin/env python3
"""
Bot引擎 v4 - 使用httpx实现高效SOCKS5 polling
解决CPU高占用问题：使用连接池复用，分批启动
"""
import asyncio
import httpx
import json
import time
import os
import logging
from datetime import datetime, date
from aiohttp import web

# 配置
CONFIG_FILE = '/root/bot_panel/data/bots_config.json'
STATS_FILE = '/root/bot_panel/data/stats.json'
AD_CONFIG_FILE = '/root/bot_panel/data/ad_config.json'
AD_IMAGE_FILE = '/root/bot_panel/data/ad_image.jpg'
BACKUP_DIR = '/root/bot_panel/data/backups'
LOG_FILE = '/root/bot_panel/logs/engine.log'
PORT = 8899

# 代理线路配置
PROXY_LINES = {
    1: {"proxy": "socks5://sSxA669yDqru:F2keVQvoiIh6@198.65.51.89:7055", "range": (1, 8)},
    2: {"proxy": "socks5://pTVGUfSlyk03:bD3riHOujtIQ@198.65.51.197:7055", "range": (9, 16)},
    3: {"proxy": "socks5://3gLbefgNLqcq:iHK8DaMD2euS@198.65.51.130:7055", "range": (17, 24)},
    4: {"proxy": "socks5://XZQKcp9iOLZU:f5VOUl2BRxZP@198.65.51.42:7055", "range": (25, 32)},
    5: {"proxy": "socks5://v4eH6NpbFJAy:GhOBzRkyH0Nd@198.65.51.96:7055", "range": (33, 40)},
    6: {"proxy": "socks5://qrsp9E9hacN5:sViGpZTysqDG@198.65.51.180:7055", "range": (41, 48)},
    7: {"proxy": "socks5://R8EFXJPeO4sA:tH8RTX0P6jYd@198.65.51.249:7055", "range": (49, 56)},
    8: {"proxy": "socks5://0R9YhHcxXS0l:F9DFTCAEGBif@198.65.51.173:7055", "range": (57, 64)},
    9: {"proxy": "socks5://qFdHKT1NaC0w:tavEbNB2sPQD@198.65.51.216:7055", "range": (65, 72)},
    10: {"proxy": "socks5://9eX0k27E75ha:n4CiaWqzs4hE@207.45.13.233:45835", "range": (73, 80)},
    11: {"proxy": "socks5://6ac9tKhgBrvD:UU6VUy9ca13U@198.65.96.124:7439", "range": (81, 88)},
    12: {"proxy": "socks5://Po5TxkDfStSu:pFPULHEu1Kpi@198.65.28.51:7037", "range": (89, 96)},
    13: {"proxy": "socks5://HKJ3er9sblgH:AQBXJoHCKGvO@198.65.112.50:6935", "range": (97, 104)},
    14: {"proxy": "socks5://aJt0S20Qr5QC:Pza9DEyv1MDN@198.65.47.100:7471", "range": (105, 112)},
    15: {"proxy": "socks5://QHMCr34mQevI:Pmn9lPrzYmEN@198.65.51.124:7055", "range": (113, 120)},
    16: {"proxy": "socks5://6iutAedgZfpC:mJJCvY8WV5z7@198.65.126.41:45623", "range": (121, 128)},
    17: {"proxy": "socks5://cLaYWRgmtrT2:4tNcYgLIEgnQ@157.238.73.209:36337", "range": (129, 136)},
    18: {"proxy": "socks5://pcLLjaXzjnPm:xA9gWEmu5tXW@204.1.89.177:44755", "range": (137, 144)},
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)



# Telegram API Pool - 20个API均匀分配给Bot，降低限流风险
API_POOL = [
    {
        "api_id": 31034207,
        "api_hash": "c6d49c6a93371381efb3fa3033d7c73a"
    },
    {
        "api_id": 37900420,
        "api_hash": "417d6f1b7e58418e81dff5b2c4f33943"
    },
    {
        "api_id": 38928927,
        "api_hash": "e5e54a03a61c3c9083899d9dffecabaf"
    },
    {
        "api_id": 36961078,
        "api_hash": "d4d9bafec6afed118856cd20f0c88c9a"
    },
    {
        "api_id": 36404424,
        "api_hash": "4fe722fcee7095dd78dab10ce3a7d1f0"
    },
    {
        "api_id": 39269216,
        "api_hash": "1114d86031ed03ce4aeec6e4a03be84d"
    },
    {
        "api_id": 39249840,
        "api_hash": "6f84364761b7a35af521a5bd5efec612"
    },
    {
        "api_id": 14530972,
        "api_hash": "4cb9f0631f064eab9bfb5e3b19E24E2"
    },
    {
        "api_id": 31864297,
        "api_hash": "4f285240ee6703396489c530876804a2"
    },
    {
        "api_id": 33219075,
        "api_hash": "9a0290f6951c020dcb15ff03096ceda3"
    },
    {
        "api_id": 24701885,
        "api_hash": "6FE8f295d213368f7b489982c68d6b6d"
    },
    {
        "api_id": 34783567,
        "api_hash": "0651774c408e8aec6b0972a9d6cc58a1"
    },
    {
        "api_id": 31055556,
        "api_hash": "7df74caff42422020f952cc5b532d1b5"
    },
    {
        "api_id": 32053459,
        "api_hash": "da7eab7df5996fe90188c628d6c128c2"
    },
    {
        "api_id": 33853337,
        "api_hash": "49bc1f37ae5a5ea5732215af2b336a5c"
    },
    {
        "api_id": 32885401,
        "api_hash": "08e5c4b9befafd18488e88a5d26c1645"
    },
    {
        "api_id": 31351042,
        "api_hash": "fd6d872bbccde181291ba561d07bc62a"
    },
    {
        "api_id": 31016054,
        "api_hash": "bda2382b78864bc45219b1aec4ea9e5b"
    },
    {
        "api_id": 33835697,
        "api_hash": "c1b216558292e093a5cfd6060e72ce6e"
    },
    {
        "api_id": 30548968,
        "api_hash": "bbe4acf228f7d9d363acb897c4737dd9"
    }
]

def get_api_for_number(number):
    """根据Bot编号获取分配的API (api_id, api_hash)"""
    idx = (number - 1) % len(API_POOL)
    return API_POOL[idx]

def get_proxy_for_number(number):
    """根据Bot编号获取代理URL"""
    for line_id, info in PROXY_LINES.items():
        start, end = info['range']
        if start <= number <= end:
            return info['proxy']
    return PROXY_LINES[1]['proxy']


def get_line_for_number(number):
    """根据Bot编号获取线路号"""
    for line_id, info in PROXY_LINES.items():
        start, end = info['range']
        if start <= number <= end:
            return line_id
    return 1


class BotEngine:
    def __init__(self):
        self.bots = {}
        self.api_last_call = {}  # api_index -> last_call_timestamp (per-API rate limiter)
        self.stats = {
            "total_sent": 0, "total_success": 0, "total_failed": 0,
            "today_sent": 0, "today_success": 0, "today_failed": 0,
            "last_date": str(date.today())
        }
        self.ad_config = {}
        self.running = False
        self.polling_tasks = {}
        self.clients = {}  # proxy_url -> httpx.AsyncClient
        self.load_config()
        self.load_stats()
        self.load_ad_config()

    def load_config(self):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.bots = data.get('bots', {})
                    logger.info(f"加载了 {len(self.bots)} 个Bot配置")
            except Exception as e:
                logger.error(f"加载配置失败: {e}")

    def _save_config(self):
        self.save_config()

    def save_config(self):
        data = {'bots': self.bots, 'saved_at': datetime.now().isoformat()}
        tmp_file = CONFIG_FILE + '.tmp'
        with open(tmp_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, CONFIG_FILE)
        # 备份
        backup_file = os.path.join(BACKUP_DIR, f"bots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(backup_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith('bots_')])
        for old in backups[:-20]:
            os.remove(os.path.join(BACKUP_DIR, old))

    def load_stats(self):
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, 'r') as f:
                    self.stats = json.load(f)
            except:
                pass

    def save_stats(self):
        with open(STATS_FILE, 'w') as f:
            json.dump(self.stats, f)

    def load_ad_config(self):
        if os.path.exists(AD_CONFIG_FILE):
            try:
                with open(AD_CONFIG_FILE, 'r') as f:
                    raw = json.load(f)
                # 支持新格式（ads数组）和旧格式（扁平结构）
                if 'ads' in raw and isinstance(raw['ads'], list) and raw['ads']:
                    # 新格式：取第一个active的广告
                    active_ad = None
                    for ad in raw['ads']:
                        if ad.get('active', True):
                            active_ad = ad
                            break
                    if not active_ad:
                        active_ad = raw['ads'][0]
                    self.ad_config = {
                        'name': active_ad.get('name', ''),
                        'text': active_ad.get('caption', active_ad.get('text', '')),
                        'buttons': active_ad.get('buttons', []),
                        'image': active_ad.get('image', '')
                    }
                else:
                    # 旧格式：直接使用
                    self.ad_config = raw
                logger.info(f"加载广告配置: {self.ad_config.get('name', '')}, 文案长度: {len(self.ad_config.get('text', ''))}, 按钮数: {len(self.ad_config.get('buttons', []))}")
            except Exception as e:
                logger.error(f"加载广告配置失败: {e}")

    def reset_today_stats(self):
        today = str(date.today())
        if self.stats.get('last_date') != today:
            self.stats['today_sent'] = 0
            self.stats['today_success'] = 0
            self.stats['today_failed'] = 0
            self.stats['last_date'] = today
            self.save_stats()

    async def get_client(self, proxy_url):
        """获取或创建httpx客户端（带连接池复用）"""
        if proxy_url not in self.clients:
            self.clients[proxy_url] = httpx.AsyncClient(
                proxy=proxy_url,
                timeout=httpx.Timeout(45.0, connect=10.0),
                limits=httpx.Limits(max_connections=30, max_keepalive_connections=15),
                http2=False
            )
        return self.clients[proxy_url]

    async def poll_bot(self, bot_id):
        """为单个Bot进行长轮询"""
        bot = self.bots.get(bot_id)
        if not bot:
            return
        token = bot['token']
        # 自动获取Bot用户名（如果还没有）
        if not bot.get('username'):
            try:
                proxy_url = get_proxy_for_number(bot.get('number', 1))
                client = await self.get_client(proxy_url)
                me_resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                me_data = me_resp.json()
                if me_data.get('ok'):
                    bot['username'] = me_data['result'].get('username', '')
                    bot['first_name'] = me_data['result'].get('first_name', '')
                    self.save_config()
            except Exception:
                pass
        number = bot['number']
        proxy_url = get_proxy_for_number(number)
        offset = 0

        logger.info(f"Bot #{number} 开始polling (proxy: {proxy_url[:30]}...)")
        # 启动前先删除webhook确保不冲突
        try:
            client = await self.get_client(proxy_url)
            del_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
            await client.post(del_url, json={"drop_pending_updates": False})
            await asyncio.sleep(1)
        except Exception as e:
            logger.warning(f"Bot #{number} deleteWebhook失败: {e}")

        conflict_count = 0
        while self.running and bot.get('status') == 'running':
            try:
                client = await self.get_client(proxy_url)
                url = f"https://api.telegram.org/bot{token}/getUpdates"
                params = {"offset": offset, "timeout": 25}
                resp = await client.get(url, params=params)

                # 处理409 Conflict（另一个getUpdates连接正在使用）
                if resp.status_code == 409:
                    conflict_count += 1
                    if conflict_count <= 3:
                        logger.warning(f"Bot #{number} 409 Conflict (第{conflict_count}次), 重新deleteWebhook")
                        try:
                            del_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
                            await client.post(del_url, json={"drop_pending_updates": False})
                        except:
                            pass
                        await asyncio.sleep(5)
                        continue
                    else:
                        # 持续冲突，降低频率
                        if conflict_count % 20 == 0:
                            logger.warning(f"Bot #{number} 持续409 ({conflict_count}次)")
                        await asyncio.sleep(30)
                        continue
                elif resp.status_code == 401:
                    logger.error(f"Bot #{number} Token无效(401), 停止polling")
                    bot['status'] = 'error'
                    self.save_config()
                    break

                conflict_count = 0
                result = resp.json()

                if result.get('ok') and result.get('result'):
                    for update in result['result']:
                        offset = update['update_id'] + 1
                        asyncio.create_task(self.handle_update(bot_id, update))

            except asyncio.CancelledError:
                break
            except httpx.TimeoutException:
                continue
            except Exception as e:
                err_msg = str(e)[:100]
                if 'Invalid username/password' in err_msg or 'proxy' in err_msg.lower():
                    if not hasattr(self, '_proxy_error_logged'):
                        self._proxy_error_logged = set()
                    if number not in self._proxy_error_logged:
                        logger.warning(f"Bot #{number} 代理认证失败")
                        self._proxy_error_logged.add(number)
                    await asyncio.sleep(30)
                elif err_msg:
                    logger.warning(f"Bot #{number} polling错误: {err_msg}")
                    await asyncio.sleep(3)
                else:
                    await asyncio.sleep(3)
        logger.info(f"Bot #{number} polling已停止")

    async def handle_update(self, bot_id, update):
        """处理收到的消息"""
        bot = self.bots.get(bot_id)
        if not bot:
            return
        token = bot['token']
        number = bot['number']
        proxy_url = get_proxy_for_number(number)

        try:
            message = update.get('message', {})
            text = message.get('text', '')
            chat_id = message.get('chat', {}).get('id')

            if not chat_id:
                # 可能是callback_query
                callback = update.get('callback_query', {})
                if callback:
                    chat_id = callback.get('message', {}).get('chat', {}).get('id')
                    await self.send_ad_to_chat(token, proxy_url, chat_id)
                return

            if text == '/start':
                logger.info(f"Bot #{number} 收到 /start 来自 {chat_id}")
                await self.send_welcome(token, proxy_url, chat_id, number)
            elif text == '/ad' or text == '预览消息':
                await self.send_ad_to_chat(token, proxy_url, chat_id)
            elif text == '/help':
                await self.send_help(token, proxy_url, chat_id)
            else:
                # 任何其他消息也发送广告
                await self.send_ad_to_chat(token, proxy_url, chat_id)

        except Exception as e:
            logger.error(f"Bot #{number} 处理消息错误: {e}")

    async def send_welcome(self, token, proxy_url, chat_id, bot_number):
        """发送欢迎消息+广告"""
        try:
            client = await self.get_client(proxy_url)
            welcome_text = (
                f"🇲🇾 欢迎来到 马来西亚-快约到家！\n\n"
                f"• 管理推广素材 [图片+文案+按钮]\n"
                f"• 预览推广消息效果\n"
                f"• 自动轮换发送，避免限流\n"
                f"• 频率控制，保护账号安全\n\n"
                f"请使用下方菜单操作 👇\n"
                f"或输入 /help 查看详细帮助"
            )
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": welcome_text}
            await client.post(url, json=payload)

            await asyncio.sleep(0.5)
            await self.send_ad_to_chat(token, proxy_url, chat_id)
        except Exception as e:
            logger.error(f"发送欢迎消息失败: {e}")

    async def send_ad_to_chat(self, token, proxy_url, chat_id):
        """发送广告到指定聊天"""
        if not self.ad_config:
            # 没有广告配置，发送提示
            client = await self.get_client(proxy_url)
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": "🇲🇾 暂无广告素材。"}
            await client.post(url, json=payload)
            return {"ok": False}

        try:
            client = await self.get_client(proxy_url)
            caption = self.ad_config.get('text', '')
            buttons = self.ad_config.get('buttons', [])

            inline_keyboard = []
            for btn in buttons:
                if isinstance(btn, list):
                    # 新格式：已经是行格式 [[{text, url}]]
                    inline_keyboard.append(btn)
                elif isinstance(btn, dict):
                    # 旧格式：每个按钮单独一行
                    inline_keyboard.append([{"text": btn['text'], "url": btn['url']}])

            # 发送图片+文案+按钮
            if os.path.exists(AD_IMAGE_FILE):
                url = f"https://api.telegram.org/bot{token}/sendPhoto"
                with open(AD_IMAGE_FILE, 'rb') as img:
                    files = {'photo': ('ad.jpg', img, 'image/jpeg')}
                    data = {
                        'chat_id': str(chat_id),
                        'caption': caption,
                    }
                    if inline_keyboard:
                        data['reply_markup'] = json.dumps({"inline_keyboard": inline_keyboard})

                    resp = await client.post(url, data=data, files=files)
                    result = resp.json()
            else:
                # 没有图片，只发文字
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": caption,
                    "reply_markup": {"inline_keyboard": inline_keyboard}
                }
                resp = await client.post(url, json=payload)
                result = resp.json()

            if result.get('ok'):
                self.stats['total_success'] = self.stats.get('total_success', 0) + 1
                self.stats['today_success'] = self.stats.get('today_success', 0) + 1
            else:
                self.stats['total_failed'] = self.stats.get('total_failed', 0) + 1
                self.stats['today_failed'] = self.stats.get('today_failed', 0) + 1

            self.stats['total_sent'] = self.stats.get('total_sent', 0) + 1
            self.stats['today_sent'] = self.stats.get('today_sent', 0) + 1
            self.save_stats()
            return result

        except Exception as e:
            logger.error(f"发送广告失败: {e}")
            self.stats['total_failed'] = self.stats.get('total_failed', 0) + 1
            self.stats['today_failed'] = self.stats.get('today_failed', 0) + 1
            self.stats['total_sent'] = self.stats.get('total_sent', 0) + 1
            self.stats['today_sent'] = self.stats.get('today_sent', 0) + 1
            self.save_stats()
            return {"ok": False}

    async def send_help(self, token, proxy_url, chat_id):
        """发送帮助信息"""
        try:
            client = await self.get_client(proxy_url)
            help_text = (
                "📋 命令列表:\n\n"
                "/start - 启动Bot\n"
                "/ad - 预览广告\n"
                "/help - 查看帮助\n\n"
                "发送任何消息都会收到广告预览"
            )
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": help_text}
            await client.post(url, json=payload)
        except Exception as e:
            logger.error(f"发送帮助失败: {e}")

    async def start_all_polling(self):
        """分批启动所有Bot的polling"""
        self.running = True
        bot_ids = [bid for bid, bot in self.bots.items() if bot.get('status') == 'running']
        logger.info(f"准备启动 {len(bot_ids)} 个Bot的polling")

        # 分批启动，每批10个，间隔1秒
        batch_size = 10
        for i in range(0, len(bot_ids), batch_size):
            batch = bot_ids[i:i+batch_size]
            for bot_id in batch:
                if bot_id not in self.polling_tasks or self.polling_tasks[bot_id].done():
                    task = asyncio.create_task(self.poll_bot(bot_id))
                    self.polling_tasks[bot_id] = task
            await asyncio.sleep(1)  # 每批间隔1秒

        logger.info(f"所有Bot polling已启动")

    async def stop_all_polling(self):
        """停止所有polling"""
        self.running = False
        for bot_id, task in self.polling_tasks.items():
            if not task.done():
                task.cancel()
        self.polling_tasks.clear()

    # ===== API 端点 =====
    async def handle_status(self, request):
        """返回所有Bot状态（含线路分组）"""
        self.reset_today_stats()
        # 构建按线路分组的数据
        lines = {}
        for line_id, info in PROXY_LINES.items():
            start, end = info['range']
            lines[str(line_id)] = {
                "proxy": info['proxy'].split('@')[1] if '@' in info['proxy'] else info['proxy'],
                "range_start": start,
                "range_end": end,
                "max_bots": end - start + 1,
                "bot_count": 0,
                "bots": []
            }
        # 填充Bot数据到对应线路
        for bot_id, bot in list(self.bots.items()):
            polling_active = bot_id in self.polling_tasks and not self.polling_tasks[bot_id].done()
            number = bot['number']
            line_id = str(get_line_for_number(number))
            api_info = get_api_for_number(number)
            bot_info = {
                "id": bot_id,
                "name": str(number),
                "number": number,
                "token_short": bot['token'][:20] + "...",
                "username": bot.get("username", ""), "token_id": bot["token"].split(":")[0][-4:],
                "line": int(line_id),
                "api_id": api_info["api_id"],
                "status": "running" if polling_active else bot.get('status', 'stopped'),
                "sent_total": bot.get('sent', 0),
                "sent_success": bot.get('success', 0),
                "sent_failed": bot.get('failed', 0),
                "ad_configured": bool(self.ad_config)
            }
            if line_id in lines:
                lines[line_id]["bots"].append(bot_info)
                lines[line_id]["bot_count"] += 1
        # 对每条线路的bots按编号排序
        for line_id in lines:
            lines[line_id]["bots"].sort(key=lambda x: x["number"])
        # 判断Agent状态
        active_polling = sum(1 for t in self.polling_tasks.values() if not t.done())
        agent_status = "online" if self.running and active_polling > 0 else "offline"
        return web.json_response({
            "status": agent_status,
            "total_bots": len(self.bots),
            "max_bots": 300,
            "polling_count": active_polling,
            "total_apis": len(API_POOL),
            "total_proxies": len(PROXY_LINES),
            "lines": lines,
            "stats": self.stats,
            "ad_config": {
                "name": self.ad_config.get('name', ''),
                "has_image": os.path.exists(AD_IMAGE_FILE),
                "text": self.ad_config.get('text', ''),
                "buttons": self.ad_config.get('buttons', [])
            }
        })
    async def handle_add_bot(self, request):
        """添加Bot"""
        data = await request.json()
        token = data.get('token', '').strip()
        # 支持 "编号 Token" 格式
        if ' ' in token:
            token = token.split(' ', 1)[-1].strip()
        if not token or ':' not in token:
            return web.json_response({"ok": False, "error": "无效Token"}, status=400)

        # 检查重复
        for bot_id, bot in list(self.bots.items()):
            if bot['token'] == token:
                return web.json_response({"ok": False, "error": "Token已存在"}, status=400)

        # 分配编号
        used_numbers = {bot['number'] for bot in self.bots.values()}
        number = 1
        while number in used_numbers:
            number += 1

        bot_id = f"bot_{number}"
        proxy_url = get_proxy_for_number(number)

        # 验证Token
        username = ""
        try:
            client = await self.get_client(proxy_url)
            url = f"https://api.telegram.org/bot{token}/getMe"
            resp = await client.get(url)
            result = resp.json()
            if result.get('ok'):
                username = result['result'].get('username', '')
            else:
                return web.json_response({"ok": False, "error": "Token无效或已被封"}, status=400)
        except Exception as e:
            logger.warning(f"验证Token超时，仍然添加: {e}")

        self.bots[bot_id] = {
            "number": number,
            "token": token,
            "username": username,
            "proxy": f"{get_proxy_for_number(number)}",
            "line": get_line_for_number(number),
            "status": "running",
            "sent": 0, "success": 0, "failed": 0,
            "added_at": datetime.now().isoformat()
        }
        self.save_config()

        # 启动polling
        task = asyncio.create_task(self.poll_bot(bot_id))
        self.polling_tasks[bot_id] = task
        # 自动设置Bot简介和头像
        asyncio.create_task(self.setup_bot_profile(bot_id))

        return web.json_response({"ok": True, "number": number, "username": username})

    async def handle_batch_add(self, request):
        """批量添加Bot"""
        data = await request.json()
        tokens = data.get('tokens', [])
        results = []
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            # 支持 "编号 Token" 格式，自动去除编号前缀
            # 例如 "120 8402681751:AAFB1-xxx" -> "8402681751:AAFB1-xxx"
            if ' ' in token:
                parts = token.split(' ', 1)
                token = parts[-1].strip()
            if not token or ':' not in token:
                results.append({"token": token[:20], "ok": False, "error": "格式错误"})
                continue

            # 检查重复
            duplicate = False
            for bot_id, bot in list(self.bots.items()):
                if bot['token'] == token:
                    duplicate = True
                    break
            if duplicate:
                results.append({"token": token[:20], "ok": False, "error": "重复"})
                continue

            used_numbers = {bot['number'] for bot in self.bots.values()}
            number = 1
            while number in used_numbers:
                number += 1

            bot_id = f"bot_{number}"
            self.bots[bot_id] = {
                "number": number,
                "token": token,
                "username": "",
                "proxy": get_proxy_for_number(number),
                "line": get_line_for_number(number),
                "status": "running",
                "sent": 0, "success": 0, "failed": 0,
                "added_at": datetime.now().isoformat()
            }

            # 启动polling
            task = asyncio.create_task(self.poll_bot(bot_id))
            self.polling_tasks[bot_id] = task
            # 自动设置Bot简介和头像
            asyncio.create_task(self.setup_bot_profile(bot_id))
            results.append({"token": token[:20], "ok": True, "number": number})

        self.save_config()
        return web.json_response({"ok": True, "results": results})

    async def handle_remove_bot(self, request):
        """删除Bot"""
        data = await request.json()
        bot_id = data.get('bot_id', '')
        if bot_id in self.polling_tasks:
            self.polling_tasks[bot_id].cancel()
            del self.polling_tasks[bot_id]
        if bot_id in self.bots:
            del self.bots[bot_id]
            self.save_config()
            return web.json_response({"ok": True})
        return web.json_response({"ok": False, "error": "Bot不存在"}, status=404)

    async def handle_start_all(self, request):
        """启动所有Bot"""
        for bot_id, bot in list(self.bots.items()):
            bot['status'] = 'running'
            if bot_id not in self.polling_tasks or self.polling_tasks[bot_id].done():
                task = asyncio.create_task(self.poll_bot(bot_id))
                self.polling_tasks[bot_id] = task
        self.save_config()
        return web.json_response({"ok": True})

    async def handle_stop_all(self, request):
        """停止所有Bot"""
        for bot_id, bot in list(self.bots.items()):
            bot['status'] = 'stopped'
        for bot_id, task in self.polling_tasks.items():
            if not task.done():
                task.cancel()
        self.polling_tasks.clear()
        self.save_config()
        return web.json_response({"ok": True})

    async def handle_update_ad(self, request):
        """更新广告配置"""
        data = await request.json()
        self.ad_config = {
            "name": data.get('name', ''),
            "text": data.get('text', ''),
            "buttons": data.get('buttons', [])
        }
        with open(AD_CONFIG_FILE, 'w') as f:
            json.dump(self.ad_config, f, ensure_ascii=False, indent=2)
        return web.json_response({"ok": True})

    async def handle_stats(self, request):
        """返回统计数据"""
        self.reset_today_stats()
        return web.json_response(self.stats)



    async def handle_upload_photo(self, request):
        """处理Bot头像图片上传"""
        reader = await request.multipart()
        photo_data = None
        batch_size = 50
        
        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == 'photo':
                photo_data = await part.read()
            elif part.name == 'batch_size':
                batch_size = int(await part.text())
        
        if not photo_data:
            return web.json_response({"ok": False, "error": "没有图片数据"})
        
        # 保存图片
        import time as _time
        photo_path = f"/root/bot_panel/data/bot_photo_{int(_time.time())}.jpg"
        with open(photo_path, 'wb') as f:
            f.write(photo_data)
        
        self.current_photo_path = photo_path
        self.photo_batch_size = batch_size
        
        return web.json_response({
            "ok": True,
            "message": f"图片已保存，将分配给 {batch_size} 个Bot",
            "path": photo_path
        })

    async def handle_set_profile(self, request):
        """一键修改所有Bot的头像和简介（后台异步执行）"""
        data = await request.json()
        name = data.get('name', '马来西亚 🇲🇾 快约到家欢迎您')
        description = data.get('description', '快约到家 - 专业按摩·正规服务·安全放心\n官网: www.kuaiyue.vip\n频道: https://t.me/kuaiyue9\n咨询: @kuaiyue777')
        short_description = data.get('short_description', '🇲🇾 快约到家 - 专业按摩·正规服务·安全放心')
        
        # 保存配置供新Bot使用
        self.profile_config = {
            'name': name,
            'description': description,
            'short_description': short_description
        }
        # 保存配置到文件供启动时使用
        import json as _json
        with open('/root/bot_panel/data/profile_config.json', 'w') as _f:
            _json.dump(self.profile_config, _f, ensure_ascii=False)
        
        # 后台执行
        new_bots_count = len([b for b in self.bots.values() if not b.get('profile_done')])
        if new_bots_count == 0:
            return web.json_response({"ok": True, "message": "没有需要修改的新Bot，所有Bot已设置过简介", "total": 0})
        self.profile_progress = {"total": new_bots_count, "done": 0, "success": 0, "running": True, "skipped": 0, "failed_bots": []}
        asyncio.ensure_future(self._do_set_profile(name, description, short_description))
        
        return web.json_response({
            "ok": True,
            "message": "已开始后台处理",
            "total": len(self.bots)
        })
    
    async def _do_set_profile(self, name, description, short_description):
        """后台执行修改所有Bot简介 - 按线路分散并行，线路内串行低频"""
        # 只处理未设置过简介的新Bot（profile_done != True）
        bot_list = [(bid, b) for bid, b in self.bots.items() if not b.get('profile_done')]
        if not bot_list:
            self.profile_progress = {"total": 0, "done": 0, "success": 0, "running": False, "skipped": 0, "failed_bots": [], "message": "没有需要修改的新Bot"}
            logger.info("set_profile: 没有新Bot需要修改简介")
            return
        self.profile_progress["skipped"] = 0
        self.profile_progress["failed_bots"] = []

        async def call_api_safe(client, url, json_data, number):
            """安全的API调用，带per-API频率控制，遇到长时间429跳过"""
            # Per-API频率控制：同一API的请求间隔至少2秒
            api_info = get_api_for_number(number)
            api_idx = (number - 1) % len(API_POOL)
            import time
            now = time.time()
            last_call = self.api_last_call.get(api_idx, 0)
            if now - last_call < 2.0:
                await asyncio.sleep(2.0 - (now - last_call))
            self.api_last_call[api_idx] = time.time()

            for attempt in range(2):
                try:
                    resp = await client.post(url, json=json_data, timeout=30)
                    if resp.status_code == 429:
                        retry_after = resp.json().get('parameters', {}).get('retry_after', 5)
                        if retry_after > 30:
                            logger.warning(f"Bot#{number} 被限流 {retry_after}秒，跳过")
                            return None
                        logger.info(f"Bot#{number} 限流 {retry_after}秒，等待重试")
                        await asyncio.sleep(retry_after + 1)
                        continue
                    elif resp.status_code == 401:
                        logger.warning(f"Bot#{number} Token无效(401)")
                        return None
                    return resp
                except Exception as e:
                    logger.error(f"Bot#{number} API调用异常: {e}")
                    if attempt == 0:
                        await asyncio.sleep(2)
                        continue
                    return None
            return None

        async def process_one_bot(bot_id, bot):
            """处理单个Bot的所有简介设置"""
            token = bot['token']
            number = bot['number']
            proxy_url = get_proxy_for_number(number)
            try:
                client = await self.get_client(proxy_url)

                # 1. 设置名称
                url = f"https://api.telegram.org/bot{token}/setMyName"
                resp = await call_api_safe(client, url, {"name": name}, number)
                if resp is None:
                    return "skipped"
                await asyncio.sleep(3)

                # 2. 设置简介
                url = f"https://api.telegram.org/bot{token}/setMyDescription"
                resp = await call_api_safe(client, url, {"description": description}, number)
                if resp is None:
                    return "skipped"
                result = resp.json()
                success = result.get('ok', False)
                await asyncio.sleep(3)

                # 3. 设置短简介
                url = f"https://api.telegram.org/bot{token}/setMyShortDescription"
                resp = await call_api_safe(client, url, {"short_description": short_description}, number)
                if resp is None:
                    return "skipped"
                await asyncio.sleep(3)

                # 4. 设置命令菜单
                url = f"https://api.telegram.org/bot{token}/setMyCommands"
                commands = [
                    {"command": "start", "description": "开始使用"},
                    {"command": "ad", "description": "预览消息"},
                    {"command": "help", "description": "帮助信息"}
                ]
                resp = await call_api_safe(client, url, {"commands": commands}, number)
                if resp is None:
                    return "skipped"
                await asyncio.sleep(3)

                # 5. 设置头像
                photo_path = self._get_photo_for_bot(number)
                if photo_path and os.path.exists(photo_path):
                    url = f"https://api.telegram.org/bot{token}/setMyPhoto"
                    try:
                        with open(photo_path, 'rb') as photo_file:
                            import aiohttp
                            form = aiohttp.FormData()
                            form.add_field('photo', photo_file, filename='photo.jpg', content_type='image/jpeg')
                            async with aiohttp.ClientSession() as session:
                                async with session.post(url, data=form, proxy=proxy_url) as resp2:
                                    pass
                    except Exception as e:
                        logger.error(f"Bot#{number} setMyPhoto error: {e}")

                if success:
                    logger.info(f"Bot#{number} 简介修改成功")
                # 标记该Bot已完成简介设置
                bot['profile_done'] = True
                self._save_config()
                return success
            except Exception as e:
                logger.error(f"Bot#{number} set_profile error: {e}")
                return False

        async def process_line(line_bots):
            """处理一条线路上的所有Bot（串行，每个间隔5秒）"""
            for bot_id, bot in line_bots:
                result = await process_one_bot(bot_id, bot)
                self.profile_progress["done"] += 1
                if result == "skipped":
                    self.profile_progress["skipped"] += 1
                    self.profile_progress["failed_bots"].append(bot.get('number', 0))
                elif result is True:
                    self.profile_progress["success"] += 1
                # 同一线路内Bot之间间隔5秒
                await asyncio.sleep(5)

        # 按线路分组
        line_groups = {}
        for bot_id, bot in bot_list:
            number = bot['number']
            line = get_line_for_number(number)
            if line not in line_groups:
                line_groups[line] = []
            line_groups[line].append((bot_id, bot))

        logger.info(f"set_profile开始: {len(bot_list)}个Bot, {len(line_groups)}条线路并行")

        # 所有线路并行处理（每条线路内串行）
        tasks = [process_line(bots) for bots in line_groups.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

        self.profile_progress["running"] = False
        logger.info(f"set_profile完成: {self.profile_progress}")


    async def auto_set_all_profiles(self):
        """启动时自动为所有未设置简介的Bot修改简介（后台低频执行）"""
        await asyncio.sleep(10)  # 等待所有polling启动完成
        # 加载配置
        if not hasattr(self, 'profile_config') or not self.profile_config:
            try:
                with open('/root/bot_panel/data/profile_config.json', 'r') as f:
                    self.profile_config = json.load(f)
            except:
                logger.info("auto_set_all_profiles: 无profile_config.json，跳过")
                return
        # 找出未设置简介的Bot
        pending = [(bid, b) for bid, b in self.bots.items() if not b.get('profile_done')]
        if not pending:
            logger.info("auto_set_all_profiles: 所有Bot已设置过简介")
            return
        logger.info(f"auto_set_all_profiles: 开始为 {len(pending)} 个Bot自动设置简介")
        config = self.profile_config
        name = config.get('name', '')
        description = config.get('description', '')
        short_description = config.get('short_description', '')
        success_count = 0
        skip_count = 0
        for bot_id, bot in pending:
            token = bot['token']
            number = bot['number']
            proxy_url = get_proxy_for_number(number)
            try:
                client = await self.get_client(proxy_url)
                # 设置名称
                if name:
                    url = f"https://api.telegram.org/bot{token}/setMyName"
                    resp = await client.post(url, json={"name": name}, timeout=10)
                    result = resp.json()
                    if not result.get('ok'):
                        error_code = result.get('error_code', 0)
                        if error_code == 429:
                            retry_after = result.get('parameters', {}).get('retry_after', 60)
                            if retry_after > 30:
                                logger.warning(f"Bot#{number} 限流 retry_after={retry_after}s，跳过")
                                skip_count += 1
                                continue
                            await asyncio.sleep(retry_after)
                    await asyncio.sleep(3)
                # 设置简介
                if description:
                    url = f"https://api.telegram.org/bot{token}/setMyDescription"
                    await client.post(url, json={"description": description}, timeout=10)
                    await asyncio.sleep(3)
                # 设置短简介
                if short_description:
                    url = f"https://api.telegram.org/bot{token}/setMyShortDescription"
                    await client.post(url, json={"short_description": short_description}, timeout=10)
                    await asyncio.sleep(3)
                # 设置命令
                url = f"https://api.telegram.org/bot{token}/setMyCommands"
                commands = [{"command": "start", "description": "开始使用"}, {"command": "ad", "description": "预览消息"}, {"command": "help", "description": "帮助信息"}]
                await client.post(url, json={"commands": commands}, timeout=10)
                await asyncio.sleep(2)
                # 设置头像
                photo_path = self._get_photo_for_bot(number)
                if photo_path and os.path.exists(photo_path):
                    try:
                        import aiohttp
                        url = f"https://api.telegram.org/bot{token}/setMyPhoto"
                        with open(photo_path, 'rb') as photo_file:
                            form = aiohttp.FormData()
                            form.add_field('photo', photo_file, filename='photo.jpg', content_type='image/jpeg')
                            async with aiohttp.ClientSession() as session:
                                async with session.post(url, data=form, proxy=proxy_url) as resp2:
                                    pass
                    except Exception as e:
                        logger.error(f"Bot#{number} auto setMyPhoto error: {e}")
                # 标记完成
                bot['profile_done'] = True
                self.save_config()
                success_count += 1
                logger.info(f"Bot#{number} 自动设置简介成功 ({success_count}/{len(pending)})")
                await asyncio.sleep(5)  # Bot之间间隔5秒
            except Exception as e:
                logger.error(f"Bot#{number} 自动设置简介失败: {e}")
                skip_count += 1
                await asyncio.sleep(5)
        logger.info(f"auto_set_all_profiles 完成: 成功={success_count}, 跳过={skip_count}")

    async def _auto_set_profile_for_new_bot(self, bot_id, bot):
        """新Bot添加后自动设置简介"""
        if not hasattr(self, 'profile_config') or not self.profile_config:
            # 尝试从文件加载
            try:
                with open('/root/bot_panel/data/profile_config.json', 'r') as f:
                    self.profile_config = json.load(f)
            except:
                return
        config = self.profile_config
        name = config.get('name', '')
        description = config.get('description', '')
        short_description = config.get('short_description', '')
        if not name and not description:
            return
        token = bot['token']
        number = bot['number']
        proxy_url = get_proxy_for_number(number)
        try:
            client = await self.get_client(proxy_url)
            # 设置名称
            url = f"https://api.telegram.org/bot{token}/setMyName"
            await client.post(url, json={"name": name}, timeout=10)
            await asyncio.sleep(3)
            # 设置简介
            url = f"https://api.telegram.org/bot{token}/setMyDescription"
            await client.post(url, json={"description": description}, timeout=10)
            await asyncio.sleep(3)
            # 设置短简介
            url = f"https://api.telegram.org/bot{token}/setMyShortDescription"
            await client.post(url, json={"short_description": short_description}, timeout=10)
            await asyncio.sleep(3)
            # 设置命令
            url = f"https://api.telegram.org/bot{token}/setMyCommands"
            commands = [{"command": "start", "description": "开始使用"}, {"command": "ad", "description": "预览消息"}, {"command": "help", "description": "帮助信息"}]
            await client.post(url, json={"commands": commands}, timeout=10)
            # 设置头像
            photo_path = self._get_photo_for_bot(number)
            if photo_path and os.path.exists(photo_path):
                try:
                    import aiohttp
                    url = f"https://api.telegram.org/bot{token}/setMyPhoto"
                    with open(photo_path, 'rb') as photo_file:
                        form = aiohttp.FormData()
                        form.add_field('photo', photo_file, filename='photo.jpg', content_type='image/jpeg')
                        async with aiohttp.ClientSession() as session:
                            async with session.post(url, data=form, proxy=proxy_url) as resp2:
                                pass
                except Exception as e:
                    logger.error(f"Bot#{number} auto setMyPhoto error: {e}")
            # 标记完成
            bot['profile_done'] = True
            self._save_config()
            logger.info(f"Bot#{number} 新Bot自动设置简介成功")
        except Exception as e:
            logger.error(f"Bot#{number} 新Bot自动设置简介失败: {e}")

    def _get_photo_for_bot(self, number):
        """获取分配给指定编号Bot的头像图片路径"""
        photos_dir = '/root/bot_panel/data/photos'
        if not os.path.exists(photos_dir):
            return None
        photos = sorted([f for f in os.listdir(photos_dir) if f.endswith(('.jpg', '.png', '.jpeg'))])
        if not photos:
            return None
        # 按编号循环分配图片
        idx = (number - 1) % len(photos)
        return os.path.join(photos_dir, photos[idx])
    
    async def handle_profile_progress(self, request):
        """查询set_profile进度"""
        progress = getattr(self, 'profile_progress', {"total": 0, "done": 0, "success": 0, "running": False})
        return web.json_response(progress)
    
    async def handle_upload_photos(self, request):
        """上传多张头像图片，保存到photos目录"""
        photos_dir = '/root/bot_panel/data/photos'
        os.makedirs(photos_dir, exist_ok=True)
        
        reader = await request.multipart()
        saved = 0
        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == 'photos':
                filename = part.filename or f'photo_{saved+1}.jpg'
                # 确保文件名安全
                safe_name = f'photo_{saved+1:03d}.jpg'
                filepath = os.path.join(photos_dir, safe_name)
                with open(filepath, 'wb') as f:
                    while True:
                        chunk = await part.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)
                saved += 1
                logger.info(f"保存头像图片: {safe_name}")
        
        # 列出所有已保存的图片
        all_photos = sorted([f for f in os.listdir(photos_dir) if f.endswith(('.jpg', '.png', '.jpeg'))])
        
        return web.json_response({
            "ok": True,
            "saved": saved,
            "total_photos": len(all_photos),
            "photos": all_photos
        })
    
    async def handle_list_photos(self, request):
        """列出已上传的头像图片"""
        photos_dir = '/root/bot_panel/data/photos'
        if not os.path.exists(photos_dir):
            return web.json_response({"photos": [], "total": 0})
        photos = sorted([f for f in os.listdir(photos_dir) if f.endswith(('.jpg', '.png', '.jpeg'))])
        return web.json_response({"photos": photos, "total": len(photos)})

    async def setup_bot_profile(self, bot_id):
        """为单个Bot设置头像和简介（新Bot加入时自动调用）"""
        bot = self.bots.get(bot_id)
        if not bot:
            return
        token = bot['token']
        number = bot['number']
        proxy_url = get_proxy_for_number(number)
        # 使用保存的配置或默认值
        config = getattr(self, 'profile_config', {})
        name = config.get('name', '马来西亚 🇲🇾 快约到家欢迎您')
        description = config.get('description', '快约到家 - 专业按摩·正规服务·安全放心\n官网: www.kuaiyue.vip\n频道: https://t.me/kuaiyue9\n咨询: @kuaiyue777')
        short_description = config.get('short_description', '🇲🇾 快约到家 - 专业按摩·正规服务·安全放心')
        try:
            client = await self.get_client(proxy_url)
            # 设置名称
            url = f"https://api.telegram.org/bot{token}/setMyName"
            await client.post(url, json={"name": name})
            # 设置简介
            url = f"https://api.telegram.org/bot{token}/setMyDescription"
            await client.post(url, json={"description": description})
            # 设置短简介
            url = f"https://api.telegram.org/bot{token}/setMyShortDescription"
            await client.post(url, json={"short_description": short_description})
            # 设置命令菜单
            url = f"https://api.telegram.org/bot{token}/setMyCommands"
            commands = [
                {"command": "start", "description": "开始使用"},
                {"command": "ad", "description": "预览消息"},
                {"command": "help", "description": "帮助信息"}
            ]
            await client.post(url, json={"commands": commands})
            # 设置头像（如果有分配的图片）
            photo_path = self._get_photo_for_bot(number)
            if photo_path and os.path.exists(photo_path):
                try:
                    url = f"https://api.telegram.org/bot{token}/setMyPhoto"
                    with open(photo_path, 'rb') as pf:
                        files = {'photo': ('photo.jpg', pf, 'image/jpeg')}
                        import httpx
                        async with httpx.AsyncClient(proxy=proxy_url, timeout=30) as hc:
                            await hc.post(url, files=files)
                except Exception:
                    pass
            logger.info(f"Bot#{number} profile设置完成")
        except Exception as e:
            logger.error(f"Bot#{number} setup_profile error: {e}")


    async def handle_health_check(self, request):
        """批量验证Bot Token"""
        results = []
        for bot_id, bot in list(self.bots.items()):
            proxy_url = get_proxy_for_number(bot['number'])
            try:
                client = await self.get_client(proxy_url)
                url = f"https://api.telegram.org/bot{bot['token']}/getMe"
                resp = await client.get(url, timeout=10)
                result = resp.json()
                if result.get('ok'):
                    username = result['result'].get('username', '')
                    bot['username'] = username
                    results.append({"number": bot['number'], "ok": True, "username": username})
                else:
                    results.append({"number": bot['number'], "ok": False, "error": "Token无效"})
            except Exception as e:
                results.append({"number": bot['number'], "ok": False, "error": str(e)[:50]})
            await asyncio.sleep(2)  # 避免过快
        self.save_config()
        return web.json_response({"ok": True, "results": results})


async def main():
    engine = BotEngine()

    app = web.Application()
    app.router.add_get('/status', engine.handle_status)
    app.router.add_post('/add_bot', engine.handle_add_bot)
    app.router.add_post('/batch_add', engine.handle_batch_add)
    app.router.add_post('/remove_bot', engine.handle_remove_bot)
    app.router.add_post('/start_all', engine.handle_start_all)
    app.router.add_post('/stop_all', engine.handle_stop_all)
    app.router.add_post('/update_ad', engine.handle_update_ad)
    app.router.add_get('/stats', engine.handle_stats)
    app.router.add_post('/upload_photo', engine.handle_upload_photo)
    app.router.add_post('/set_profile', engine.handle_set_profile)
    app.router.add_post('/health_check', engine.handle_health_check)
    app.router.add_get('/profile_progress', engine.handle_profile_progress)
    app.router.add_post('/upload_photos', engine.handle_upload_photos)
    app.router.add_get('/list_photos', engine.handle_list_photos)

    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Bot引擎API启动在端口 {PORT}")

    # 启动所有Bot的polling
    await engine.start_all_polling()

    # 启动后自动为未设置简介的Bot修改简介
    asyncio.create_task(engine.auto_set_all_profiles())
    # 保持运行
    try:
        while True:
            await asyncio.sleep(60)
            engine.reset_today_stats()
            # 检查并重启失败的polling任务
            for bot_id, bot in engine.bots.items():
                if bot.get('status') == 'running':
                    if bot_id not in engine.polling_tasks or engine.polling_tasks[bot_id].done():
                        task = asyncio.create_task(engine.poll_bot(bot_id))
                        engine.polling_tasks[bot_id] = task
    except asyncio.CancelledError:
        pass
    finally:
        await engine.stop_all_polling()
        for client in engine.clients.values():
            await client.aclose()
        await runner.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
