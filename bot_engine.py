"""
Bot引擎 v5 - Webhook模式
从Long Polling改为Webhook，大幅降低CPU使用
Telegram主动推送消息到服务器，响应速度<1秒
"""
import asyncio
import httpx
import json
import time
import os
import hashlib
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

# Webhook配置
WEBHOOK_DOMAIN = "https://tg99999.pw"
WEBHOOK_SECRET_PREFIX = "wh_"  # webhook路径前缀

# 代理线路配置（270个Bot / 20条线路）
PROXY_LINES = {
    1: {"proxy": "socks5://X7V1S9l4m2u4:H3A2c1n2Y5y5@103.129.197.88:9270", "range": (1, 14)},
    2: {"proxy": "socks5://k7H6v2u5h8C6:j3l0u9j6b9O8@103.129.197.102:9270", "range": (15, 28)},
    3: {"proxy": "socks5://N5T0h9B2J2w8:V5P2u7u5p7K5@103.129.197.153:9270", "range": (29, 42)},
    4: {"proxy": "socks5://y7f7x9P8i2i3:u3J6N8x6x2X5@103.129.197.171:9270", "range": (43, 56)},
    5: {"proxy": "socks5://W8L7L1U4i8X7:n3L5a5j2r2l2@103.129.197.184:9270", "range": (57, 70)},
    6: {"proxy": "socks5://Y5K4p0F0c7v7:c3b6Z6H5l1j8@103.129.197.186:9270", "range": (71, 84)},
    7: {"proxy": "socks5://L5d5t7A0f1G9:L9c7k4B4L1z4@103.129.197.236:9270", "range": (85, 98)},
    8: {"proxy": "socks5://s8H9r7D2K3J5:y0D4p8i4E7e7@103.116.47.15:9270", "range": (99, 112)},
    9: {"proxy": "socks5://J1p8w3M9D3q9:m5X9S5e6K6R8@103.116.47.32:9270", "range": (113, 126)},
    10: {"proxy": "socks5://p7n4I2G7U4J1:R0N4b0y0Y2J4@103.116.47.34:9270", "range": (127, 140)},
    11: {"proxy": "socks5://u9O2g2E8K2v0:v9C5x8o6f0M5@103.116.47.61:9270", "range": (141, 153)},
    12: {"proxy": "socks5://E5L3e4Q5e4n0:l9X5Q9Z4h1T2@103.116.47.65:9270", "range": (154, 166)},
    13: {"proxy": "socks5://C5x3K2g8J8g0:h0V2r1H3Y2n3@103.116.47.87:9270", "range": (167, 179)},
    14: {"proxy": "socks5://L0d3x9t9d8w7:X2H1H0K5F1h8@103.116.47.95:9270", "range": (180, 192)},
    15: {"proxy": "socks5://f1r1u6n3P7y1:g4V5f3N2h2h2@103.116.47.101:9270", "range": (193, 205)},
    16: {"proxy": "socks5://w5N1m2j0M2J6:L5c8k5m8u4q4@103.116.47.119:9270", "range": (206, 218)},
    17: {"proxy": "socks5://G2f6S5f7H3m4:o9f7p1B3C5C2@103.116.47.159:9270", "range": (219, 231)},
    18: {"proxy": "socks5://t1l5s0d3W8k1:K7t7W0G0f8V0@103.116.47.225:9270", "range": (232, 244)},
    19: {"proxy": "socks5://O8h8D5s0X9w2:T8u4w5c3B7m4@103.116.47.239:9270", "range": (245, 257)},
    20: {"proxy": "socks5://Q6p6x7m6R6X4:O4V9f3l6f7N7@103.116.45.114:9866", "range": (258, 270)},
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
    {"api_id": 31034207, "api_hash": "c6d49c6a93371381efb3fa3033d7c73a"},
    {"api_id": 37900420, "api_hash": "417d6f1b7e58418e81dff5b2c4f33943"},
    {"api_id": 38928927, "api_hash": "e5e54a03a61c3c9083899d9dffecabaf"},
    {"api_id": 36961078, "api_hash": "d4d9bafec6afed118856cd20f0c88c9a"},
    {"api_id": 36404424, "api_hash": "4fe722fcee7095dd78dab10ce3a7d1f0"},
    {"api_id": 39269216, "api_hash": "1114d86031ed03ce4aeec6e4a03be84d"},
    {"api_id": 39249840, "api_hash": "6f84364761b7a35af521a5bd5efec612"},
    {"api_id": 14530972, "api_hash": "4cb9f0631f064eab9bfb5e3b19E24E2"},
    {"api_id": 31864297, "api_hash": "4f285240ee6703396489c530876804a2"},
    {"api_id": 33219075, "api_hash": "9a0290f6951c020dcb15ff03096ceda3"},
    {"api_id": 24701885, "api_hash": "6FE8f295d213368f7b489982c68d6b6d"},
    {"api_id": 34783567, "api_hash": "0651774c408e8aec6b0972a9d6cc58a1"},
    {"api_id": 31055556, "api_hash": "7df74caff42422020f952cc5b532d1b5"},
    {"api_id": 32053459, "api_hash": "da7eab7df5996fe90188c628d6c128c2"},
    {"api_id": 33853337, "api_hash": "49bc1f37ae5a5ea5732215af2b336a5c"},
    {"api_id": 32885401, "api_hash": "08e5c4b9befafd18488e88a5d26c1645"},
    {"api_id": 31351042, "api_hash": "fd6d872bbccde181291ba561d07bc62a"},
    {"api_id": 31016054, "api_hash": "bda2382b78864bc45219b1aec4ea9e5b"},
    {"api_id": 33835697, "api_hash": "c1b216558292e093a5cfd6060e72ce6e"},
    {"api_id": 30548968, "api_hash": "bbe4acf228f7d9d363acb897c4737dd9"},
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

def get_webhook_secret(token):
    """根据Bot token生成唯一的webhook路径密钥"""
    return hashlib.sha256(token.encode()).hexdigest()[:32]


class BotEngine:
    def __init__(self):
        self.bots = {}
        self.api_last_call = {}
        self.stats = {
            "total_sent": 0, "total_success": 0, "total_failed": 0,
            "today_sent": 0, "today_success": 0, "today_failed": 0,
            "last_date": str(date.today())
        }
        self.ad_config = {}
        self.running = False
        self.webhook_registered = {}  # bot_id -> True/False
        self.last_check_result = None
        self.clients = {}  # proxy_url -> httpx.AsyncClient
        # token -> bot_id 快速查找映射
        self.token_to_bot_id = {}
        # webhook_secret -> bot_id 快速查找映射
        self.secret_to_bot_id = {}
        self.load_config()
        self.load_stats()
        self.load_ad_config()
        self._build_lookup_maps()

    def _build_lookup_maps(self):
        """构建token和webhook_secret到bot_id的映射"""
        self.token_to_bot_id = {}
        self.secret_to_bot_id = {}
        for bot_id, bot in self.bots.items():
            token = bot['token']
            self.token_to_bot_id[token] = bot_id
            secret = get_webhook_secret(token)
            self.secret_to_bot_id[secret] = bot_id

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
                if 'ads' in raw and isinstance(raw['ads'], list) and raw['ads']:
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

    async def get_client(self, proxy_url, bot_id=None):
        """获取或创建httpx客户端（按代理线路共享）"""
        if proxy_url not in self.clients:
            self.clients[proxy_url] = httpx.AsyncClient(
                proxy=proxy_url,
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
                http2=False
            )
        return self.clients[proxy_url]

    # ==================== Webhook核心逻辑 ====================

    async def handle_webhook(self, request):
        """接收Telegram Webhook推送的消息"""
        secret = request.match_info.get('secret', '')
        bot_id = self.secret_to_bot_id.get(secret)
        if not bot_id:
            return web.Response(status=404)

        try:
            update = await request.json()
            # 异步处理消息，立即返回200给Telegram
            asyncio.create_task(self.handle_update(bot_id, update))
        except Exception as e:
            logger.error(f"Webhook解析错误: {e}")

        return web.Response(status=200, text="ok")

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
                f"\U0001f1f2\U0001f1fe 欢迎来到 马来西亚-快约到家！\n\n"
                f"• 管理推广素材 [图片+文案+按钮]\n"
                f"• 预览推广消息效果\n"
                f"• 自动轮换发送，避免限流\n"
                f"• 频率控制，保护账号安全\n\n"
                f"请使用下方菜单操作 \U0001f447\n"
                f"或输入 /help 查看详细帮助"
            )
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": welcome_text}
            await client.post(url, json=payload)

            await asyncio.sleep(0.3)
            await self.send_ad_to_chat(token, proxy_url, chat_id)
        except Exception as e:
            logger.error(f"发送欢迎消息失败: {e}")

    async def send_ad_to_chat(self, token, proxy_url, chat_id):
        """发送广告到指定聊天"""
        if not self.ad_config or not self.ad_config.get('text'):
            await self.reload_ad_config()
            if not self.ad_config or not self.ad_config.get('text'):
                self.ad_config = {
                    "name": "default_ad",
                    "text": "\u2728 欢迎光临快约到家 \u2728\n\n\U0001f1f2\U0001f1fe 马来西亚专业上门服务\n\u2705 正规按摩 \u00b7 安全放心\n\u2705 美女技师 \u00b7 服务专业\n\u2705 全城覆盖 \u00b7 快速上门\n\n\U0001f4f1 官网: www.kuaiyue.vip\n\U0001f4e2 频道: @kuaiyue9\n\U0001f4ac 咨询: @kuaiyue123456789",
                    "buttons": [
                        [{"text": "\U0001f310 访问官网", "url": "https://www.kuaiyue.vip"}],
                        [{"text": "\U0001f4e2 加入频道", "url": "https://t.me/kuaiyue9"}],
                        [{"text": "\U0001f4ac 咨询客户", "url": "https://t.me/kuaiyue123456789"}]
                    ]
                }
                try:
                    with open(AD_CONFIG_FILE, 'w', encoding='utf-8') as _f:
                        json.dump(self.ad_config, _f, ensure_ascii=False, indent=2)
                    logger.info("自动创建默认广告配置")
                except:
                    pass

        try:
            client = await self.get_client(proxy_url)
            caption = self.ad_config.get('text', '')
            buttons = self.ad_config.get('buttons', [])

            inline_keyboard = []
            for btn in buttons:
                if isinstance(btn, list):
                    inline_keyboard.append(btn)
                elif isinstance(btn, dict):
                    inline_keyboard.append([{"text": btn['text'], "url": btn['url']}])

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
                "\U0001f4cb 命令列表:\n\n"
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

    # ==================== Webhook注册管理 ====================

    async def register_webhook(self, bot_id):
        """为单个Bot注册Webhook"""
        bot = self.bots.get(bot_id)
        if not bot:
            return False
        token = bot['token']
        number = bot['number']
        proxy_url = get_proxy_for_number(number)
        secret = get_webhook_secret(token)
        webhook_url = f"{WEBHOOK_DOMAIN}/webhook/{secret}"

        try:
            client = await self.get_client(proxy_url, bot_id)
            # 先删除旧webhook
            del_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
            await client.post(del_url, json={"drop_pending_updates": False})
            await asyncio.sleep(0.2)

            # 设置新webhook
            set_url = f"https://api.telegram.org/bot{token}/setWebhook"
            payload = {
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"],
                "max_connections": 40
            }
            resp = await client.post(set_url, json=payload)
            result = resp.json()

            if result.get('ok'):
                self.webhook_registered[bot_id] = True
                logger.info(f"Bot #{number} Webhook注册成功")
                return True
            else:
                logger.error(f"Bot #{number} Webhook注册失败: {result.get('description', '')}")
                self.webhook_registered[bot_id] = False
                return False
        except Exception as e:
            logger.error(f"Bot #{number} Webhook注册异常: {e}")
            self.webhook_registered[bot_id] = False
            return False

    async def unregister_webhook(self, bot_id):
        """注销单个Bot的Webhook"""
        bot = self.bots.get(bot_id)
        if not bot:
            return
        token = bot['token']
        number = bot['number']
        proxy_url = get_proxy_for_number(number)

        try:
            client = await self.get_client(proxy_url, bot_id)
            url = f"https://api.telegram.org/bot{token}/deleteWebhook"
            await client.post(url, json={"drop_pending_updates": False})
            self.webhook_registered[bot_id] = False
            logger.info(f"Bot #{number} Webhook已注销")
        except Exception as e:
            logger.error(f"Bot #{number} 注销Webhook失败: {e}")

    async def register_all_webhooks(self):
        """为所有Bot注册Webhook（分批进行）"""
        self.running = True
        bot_ids = [bid for bid, bot in self.bots.items() if bot.get('status') == 'running']
        logger.info(f"准备为 {len(bot_ids)} 个Bot注册Webhook")

        success = 0
        failed = 0
        batch_size = 10
        for i in range(0, len(bot_ids), batch_size):
            batch = bot_ids[i:i+batch_size]
            tasks = [self.register_webhook(bot_id) for bot_id in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if r is True:
                    success += 1
                else:
                    failed += 1
            await asyncio.sleep(1)  # 每批间隔1秒

        logger.info(f"Webhook注册完成: 成功{success} 失败{failed}")

    async def unregister_all_webhooks(self):
        """注销所有Bot的Webhook"""
        for bot_id in list(self.bots.keys()):
            await self.unregister_webhook(bot_id)
            await asyncio.sleep(0.2)

    # ==================== 面板API接口（保持兼容） ====================

    async def handle_status(self, request):
        """返回所有Bot状态（含线路分组）"""
        self.reset_today_stats()
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

        for bot_id, bot in list(self.bots.items()):
            webhook_active = self.webhook_registered.get(bot_id, False)
            number = bot['number']
            line_id = str(get_line_for_number(number))
            api_info = get_api_for_number(number)
            bot_info = {
                "id": bot_id,
                "name": str(number),
                "number": number,
                "token_short": bot['token'][:20] + "...",
                "username": bot.get("username", ""),
                "token_id": bot["token"].split(":")[0][-4:],
                "line": int(line_id),
                "api_id": api_info["api_id"],
                "status": "running" if webhook_active else bot.get('status', 'stopped'),
                "sent_total": bot.get('sent', 0),
                "sent_success": bot.get('success', 0),
                "sent_failed": bot.get('failed', 0),
                "ad_configured": bool(self.ad_config)
            }
            if line_id in lines:
                lines[line_id]["bots"].append(bot_info)
                lines[line_id]["bot_count"] += 1

        for line_id in lines:
            lines[line_id]["bots"].sort(key=lambda x: x["number"])

        active_webhooks = sum(1 for v in self.webhook_registered.values() if v)
        agent_status = "online" if self.running and active_webhooks > 0 else "offline"
        return web.json_response({
            "status": agent_status,
            "mode": "webhook",
            "total_bots": len(self.bots),
            "max_bots": 500,
            "polling_count": active_webhooks,  # 兼容面板显示，实际是webhook数
            "webhook_count": active_webhooks,
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
        if ' ' in token:
            token = token.split(' ', 1)[-1].strip()
        if not token or ':' not in token:
            return web.json_response({"ok": False, "error": "无效Token"}, status=400)

        for bot_id, bot in list(self.bots.items()):
            if bot['token'] == token:
                return web.json_response({"ok": False, "error": "Token已存在"}, status=400)

        used_numbers = {bot['number'] for bot in self.bots.values()}
        number = 1
        while number in used_numbers:
            number += 1

        bot_id = f"bot_{number}"
        proxy_url = get_proxy_for_number(number)

        username = ""
        try:
            client = await self.get_client(proxy_url, bot_id)
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
            "proxy": get_proxy_for_number(number),
            "line": get_line_for_number(number),
            "status": "running",
            "sent": 0, "success": 0, "failed": 0,
            "added_at": datetime.now().isoformat()
        }
        self.save_config()
        self._build_lookup_maps()

        # 注册Webhook
        asyncio.create_task(self.register_webhook(bot_id))
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
            if ' ' in token:
                parts = token.split(' ', 1)
                token = parts[-1].strip()
            if not token or ':' not in token:
                results.append({"token": token[:20], "ok": False, "error": "格式错误"})
                continue

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
            # 注册Webhook
            asyncio.create_task(self.register_webhook(bot_id))
            asyncio.create_task(self.setup_bot_profile(bot_id))
            results.append({"token": token[:20], "ok": True, "number": number})

        self.save_config()
        self._build_lookup_maps()
        return web.json_response({"ok": True, "results": results})

    async def handle_remove_bot(self, request):
        """删除Bot"""
        data = await request.json()
        bot_id = data.get('bot_id', '')
        if bot_id in self.bots:
            # 注销Webhook
            await self.unregister_webhook(bot_id)
            del self.bots[bot_id]
            self.webhook_registered.pop(bot_id, None)
            self.save_config()
            self._build_lookup_maps()
            return web.json_response({"ok": True})
        return web.json_response({"ok": False, "error": "Bot不存在"}, status=404)

    async def handle_start_all(self, request):
        """启动所有Bot（注册Webhook）"""
        for bot_id, bot in list(self.bots.items()):
            bot['status'] = 'running'
        self.save_config()
        asyncio.create_task(self.register_all_webhooks())
        return web.json_response({"ok": True})

    async def handle_stop_all(self, request):
        """停止所有Bot（注销Webhook）"""
        for bot_id, bot in list(self.bots.items()):
            bot['status'] = 'stopped'
        self.webhook_registered.clear()
        self.save_config()
        asyncio.create_task(self.unregister_all_webhooks())
        return web.json_response({"ok": True})

    async def handle_update_ad(self, request):
        """更新广告配置"""
        data = await request.json()
        self.ad_config = data
        with open(AD_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"广告配置已更新: {data.get('name', '')}")
        return web.json_response({"ok": True})

    async def handle_stats(self, request):
        """获取统计数据"""
        self.reset_today_stats()
        return web.json_response(self.stats)

    async def handle_upload_photo(self, request):
        """上传广告图片"""
        reader = await request.multipart()
        field = await reader.next()
        if field:
            data = await field.read()
            with open(AD_IMAGE_FILE, 'wb') as f:
                f.write(data)
            logger.info(f"广告图片已上传: {len(data)} bytes")
            return web.json_response({"ok": True})
        return web.json_response({"ok": False, "error": "无文件"})

    async def handle_set_profile(self, request):
        """设置Bot简介"""
        data = await request.json()
        name = data.get('name', '')
        description = data.get('description', '')
        short_description = data.get('short_description', '')
        asyncio.create_task(self._do_set_profile(name, description, short_description))
        return web.json_response({"ok": True, "message": "简介设置已启动"})

    async def _do_set_profile(self, name, description, short_description):
        """批量设置所有Bot的简介"""
        async def call_api_safe(client, url, json_data, number):
            try:
                resp = await client.post(url, json=json_data, timeout=15)
                result = resp.json()
                if resp.status_code == 429:
                    retry_after = result.get('parameters', {}).get('retry_after', 30)
                    logger.warning(f"Bot #{number} 限流，等待{retry_after}秒")
                    await asyncio.sleep(retry_after)
                    resp = await client.post(url, json=json_data, timeout=15)
                    result = resp.json()
                elif resp.status_code == 401:
                    return {"ok": False, "description": "Token无效"}
                return result
            except Exception as e:
                return {"ok": False, "description": str(e)[:50]}

        async def process_one_bot(bot_id, bot):
            token = bot['token']
            number = bot['number']
            proxy_url = get_proxy_for_number(number)
            client = await self.get_client(proxy_url, bot_id)
            results = {}

            if name:
                url = f"https://api.telegram.org/bot{token}/setMyName"
                r = await call_api_safe(client, url, {"name": name}, number)
                results['name'] = r.get('ok', False)

            if description:
                url = f"https://api.telegram.org/bot{token}/setMyDescription"
                r = await call_api_safe(client, url, {"description": description}, number)
                results['description'] = r.get('ok', False)

            if short_description:
                url = f"https://api.telegram.org/bot{token}/setMyShortDescription"
                r = await call_api_safe(client, url, {"short_description": short_description}, number)
                results['short_description'] = r.get('ok', False)

            return results

        async def process_line(line_bots):
            for bot_id, bot in line_bots:
                await process_one_bot(bot_id, bot)
                await asyncio.sleep(3)

        # 按线路分组并行处理
        line_groups = {}
        for bot_id, bot in self.bots.items():
            line = get_line_for_number(bot['number'])
            if line not in line_groups:
                line_groups[line] = []
            line_groups[line].append((bot_id, bot))

        tasks = [process_line(bots) for bots in line_groups.values()]
        await asyncio.gather(*tasks)
        logger.info("所有Bot简介设置完成")

    async def auto_set_all_profiles(self):
        """启动后自动为未设置简介的Bot设置"""
        await asyncio.sleep(60)  # 等待1分钟
        for bot_id, bot in list(self.bots.items()):
            if not bot.get('profile_set'):
                await self._auto_set_profile_for_new_bot(bot_id, bot)
                await asyncio.sleep(5)

    async def _auto_set_profile_for_new_bot(self, bot_id, bot):
        """为新Bot自动设置简介和头像"""
        token = bot['token']
        number = bot['number']
        proxy_url = get_proxy_for_number(number)

        try:
            client = await self.get_client(proxy_url, bot_id)

            # 设置名称
            name_url = f"https://api.telegram.org/bot{token}/setMyName"
            await client.post(name_url, json={"name": "快约到家"}, timeout=15)
            await asyncio.sleep(1)

            # 设置描述
            desc_url = f"https://api.telegram.org/bot{token}/setMyDescription"
            desc = "\U0001f1f2\U0001f1fe 马来西亚-快约到家\n\n\u2705 正规按摩 \u00b7 安全放心\n\u2705 美女技师 \u00b7 服务专业\n\u2705 全城覆盖 \u00b7 快速上门\n\n\U0001f4f1 官网: www.kuaiyue.vip"
            await client.post(desc_url, json={"description": desc}, timeout=15)
            await asyncio.sleep(1)

            # 设置短描述
            short_desc_url = f"https://api.telegram.org/bot{token}/setMyShortDescription"
            await client.post(short_desc_url, json={"short_description": "\U0001f1f2\U0001f1fe 快约到家 - 马来西亚专业上门服务"}, timeout=15)
            await asyncio.sleep(1)

            # 设置头像
            photo_path = self._get_photo_for_bot(number)
            if photo_path and os.path.exists(photo_path):
                photo_url = f"https://api.telegram.org/bot{token}/setUserProfilePhoto"
                with open(photo_path, 'rb') as img:
                    files = {'photo': ('photo.jpg', img, 'image/jpeg')}
                    await client.post(photo_url, files=files, timeout=30)

            # 设置命令
            cmd_url = f"https://api.telegram.org/bot{token}/setMyCommands"
            commands = [
                {"command": "start", "description": "开始使用"},
                {"command": "ad", "description": "预览消息"},
                {"command": "help", "description": "帮助信息"}
            ]
            await client.post(cmd_url, json={"commands": commands}, timeout=15)

            bot['profile_set'] = True
            self.save_config()
            logger.info(f"Bot #{number} 简介设置完成")
        except Exception as e:
            logger.error(f"Bot #{number} 自动设置简介失败: {e}")

    def _get_photo_for_bot(self, number):
        """获取Bot对应的头像文件"""
        photos_dir = '/root/bot_panel/data/photos'
        if os.path.exists(photos_dir):
            photos = sorted([f for f in os.listdir(photos_dir) if f.endswith(('.jpg', '.png', '.jpeg'))])
            if photos:
                idx = (number - 1) % len(photos)
                return os.path.join(photos_dir, photos[idx])
        return None

    async def handle_profile_progress(self, request):
        """获取简介设置进度"""
        total = len(self.bots)
        done = sum(1 for b in self.bots.values() if b.get('profile_set'))
        return web.json_response({"total": total, "done": done, "progress": done/total*100 if total > 0 else 0})

    async def handle_upload_photos(self, request):
        """批量上传头像"""
        photos_dir = '/root/bot_panel/data/photos'
        os.makedirs(photos_dir, exist_ok=True)
        reader = await request.multipart()
        count = 0
        async for field in reader:
            if field.filename:
                data = await field.read()
                filepath = os.path.join(photos_dir, field.filename)
                with open(filepath, 'wb') as f:
                    f.write(data)
                count += 1
        return web.json_response({"ok": True, "count": count})

    async def handle_list_photos(self, request):
        """列出已上传的头像"""
        photos_dir = '/root/bot_panel/data/photos'
        photos = []
        if os.path.exists(photos_dir):
            photos = sorted([f for f in os.listdir(photos_dir) if f.endswith(('.jpg', '.png', '.jpeg'))])
        return web.json_response({"photos": photos, "count": len(photos)})

    async def setup_bot_profile(self, bot_id):
        """为新添加的Bot设置简介"""
        await asyncio.sleep(3)
        bot = self.bots.get(bot_id)
        if bot and not bot.get('profile_set'):
            await self._auto_set_profile_for_new_bot(bot_id, bot)

    # ==================== 自动检测 ====================

    async def auto_check_loop(self):
        """每小时自动检测所有Bot是否正常"""
        logger.info("自动检测循环启动 - 每小时检测一次Bot状态")
        while True:
            try:
                await asyncio.sleep(300 if not hasattr(self, "_first_check_done") else 3600)
                logger.info("=== 开始自动检测所有Bot状态 ===")
                await self.run_auto_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自动检测循环异常: {e}")
                await asyncio.sleep(120)

    async def run_auto_check(self):
        """执行一次完整的Bot检测"""
        check_results = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(self.bots),
            "ok": 0,
            "fixed": 0,
            "failed": 0,
            "details": []
        }

        for bot_id, bot in list(self.bots.items()):
            number = bot['number']
            token = bot['token']
            proxy_url = get_proxy_for_number(number)
            result = await self.check_and_fix_bot(bot_id, bot, token, proxy_url)
            check_results['details'].append(result)

            if result['status'] == 'ok':
                check_results['ok'] += 1
            elif result['status'] == 'fixed':
                check_results['fixed'] += 1
            else:
                check_results['failed'] += 1

            await asyncio.sleep(0.3)

        self.last_check_result = check_results
        self._first_check_done = True
        check_file = '/root/bot_panel/data/last_check.json'
        with open(check_file, 'w') as f:
            json.dump(check_results, f, indent=2, ensure_ascii=False)

        logger.info(f"=== 检测完成: 正常{check_results['ok']} 修复{check_results['fixed']} 失败{check_results['failed']} ===")
        return check_results

    async def check_and_fix_bot(self, bot_id, bot, token, proxy_url):
        """检测单个Bot并自动修复（Webhook版）"""
        number = bot['number']
        result = {"number": number, "bot_id": bot_id}
        try:
            client = await self.get_client(proxy_url, bot_id)
            # 步骤1: 检查Bot是否在线（getMe）
            url = f"https://api.telegram.org/bot{token}/getMe"
            resp = await client.get(url, timeout=15)
            data = resp.json()
            if not data.get('ok'):
                result['status'] = 'failed'
                result['error'] = data.get('description', 'Token无效')
                logger.warning(f"Bot #{number} Token无效: {data.get('description','')}")
                return result

            # 步骤2: 检查Webhook是否正常注册
            wh_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
            wh_resp = await client.get(wh_url, timeout=15)
            wh_data = wh_resp.json()
            if wh_data.get('ok'):
                wh_info = wh_data.get('result', {})
                expected_secret = get_webhook_secret(token)
                expected_url = f"{WEBHOOK_DOMAIN}/webhook/{expected_secret}"
                if wh_info.get('url') != expected_url:
                    # Webhook未正确设置，重新注册
                    logger.warning(f"Bot #{number} Webhook未正确设置，重新注册")
                    success = await self.register_webhook(bot_id)
                    if success:
                        result['status'] = 'fixed'
                        result['action'] = '重新注册Webhook'
                    else:
                        result['status'] = 'failed'
                        result['error'] = 'Webhook注册失败'
                    return result

            # 步骤3: 检查广告配置
            if not self.ad_config or not self.ad_config.get('text'):
                await self.reload_ad_config()
                if not self.ad_config:
                    result['status'] = 'failed'
                    result['error'] = '广告配置缺失'
                    return result

            # Bot在线且Webhook正常
            self.webhook_registered[bot_id] = True
            result['status'] = 'ok'
        except Exception as e:
            error_msg = str(e)[:80] or type(e).__name__
            logger.warning(f"Bot #{number} 检测异常: {error_msg}")
            # 尝试修复：重新注册Webhook
            try:
                success = await self.register_webhook(bot_id)
                if success:
                    result['status'] = 'fixed'
                    result['action'] = f'异常修复: {error_msg}'
                else:
                    result['status'] = 'failed'
                    result['error'] = error_msg
            except:
                result['status'] = 'failed'
                result['error'] = error_msg
        return result

    async def reload_ad_config(self):
        """重新加载广告配置"""
        try:
            if os.path.exists(AD_CONFIG_FILE):
                with open(AD_CONFIG_FILE) as f:
                    self.ad_config = json.load(f)
                logger.info("广告配置已重新加载")
        except Exception as e:
            logger.error(f"重新加载广告配置失败: {e}")

    async def handle_check_result(self, request):
        """获取最近一次检测结果"""
        check_file = '/root/bot_panel/data/last_check.json'
        if os.path.exists(check_file):
            with open(check_file) as f:
                data = json.load(f)
            return web.json_response(data)
        return web.json_response({"error": "暂无检测记录"})

    async def handle_manual_check(self, request):
        """手动触发一次检测"""
        asyncio.create_task(self.run_auto_check())
        return web.json_response({"ok": True, "message": "检测已启动，请稍后查看结果"})

    async def handle_health_check(self, request):
        """批量验证Bot Token"""
        results = []
        for bot_id, bot in list(self.bots.items()):
            proxy_url = get_proxy_for_number(bot['number'])
            try:
                client = await self.get_client(proxy_url, bot_id)
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
            await asyncio.sleep(2)
        self.save_config()
        return web.json_response({"ok": True, "results": results})


async def main():
    engine = BotEngine()

    app = web.Application(client_max_size=200*1024*1024)

    # Webhook接收端点
    app.router.add_post('/webhook/{secret}', engine.handle_webhook)

    # 面板API端点（保持兼容）
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
    app.router.add_get('/check_result', engine.handle_check_result)
    app.router.add_post('/manual_check', engine.handle_manual_check)
    app.router.add_post('/upload_photos', engine.handle_upload_photos)
    app.router.add_get('/list_photos', engine.handle_list_photos)

    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Bot引擎API启动在端口 {PORT} (Webhook模式)")

    # 注册所有Bot的Webhook
    await engine.register_all_webhooks()

    # 启动自动检测和自动设置简介
    asyncio.create_task(engine.auto_set_all_profiles())
    asyncio.create_task(engine.auto_check_loop())

    # 保持运行
    try:
        while True:
            await asyncio.sleep(60)
            engine.reset_today_stats()
    except asyncio.CancelledError:
        pass
    finally:
        # 关闭时不注销Webhook（保持Bot在线）
        for client in engine.clients.values():
            await client.aclose()
        await runner.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
