"""
Telegram Bot Notification Service
==============================
"""

import requests

try:
    from flask import current_app, url_for
except Exception:  # pragma: no cover
    current_app = None  # type: ignore[assignment]

    def url_for(*_args, **_kwargs):  # type: ignore[no-redef]
        return ""


class TelegramBotNotifier:
    """Telegram Bot notification handler"""
    
    def __init__(self, app=None):
        self.bot_token = None
        self.api_base = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        token = (app.config.get('TELEGRAM_BOT_TOKEN') or '').strip()
        self.bot_token = token or None
        if self.bot_token:
            self.api_base = f'https://api.telegram.org/bot{self.bot_token}'
            app.logger.info('Telegram Bot initialized')
        else:
            self.api_base = None

    def is_configured(self):
        """Check if Telegram Bot is configured"""
        return bool(self.bot_token)
    
    def _request(self, method: str, endpoint: str, data: dict = None):
        """Make API request"""
        if not self.is_configured():
            return None
        
        url = f'{self.api_base}/{endpoint}'
        try:
            response = requests.post(url, json=data, timeout=10)
            return response.json() if response.ok else None
        except requests.RequestException as e:
            if current_app is not None:
                try:
                    current_app.logger.error(f'Telegram API error: {e}')
                except Exception:
                    pass
            return None
    
    def send_message(self, chat_id: str, text: str, parse_mode: str = 'Markdown'):
        """Send text message"""
        return self._request('POST', 'sendMessage', {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        })
    
    def send_notification(self, chat_id: str, title: str, body: str, url: str = None):
        """
        Send notification to user.
        
        Args:
            chat_id: Telegram chat ID
            title: Notification title
            body: Notification body
            url: Optional URL to open
        """
        message = f"📢 *{title}*\n\n{body}"
        
        if url:
            message += f"\n[查看詳情]({url})"
        
        return self.send_message(chat_id, message)
    
    def send_expiry_reminder(self, chat_id: str, items: list, with_auth=False):
        """Send expiry reminder for items"""
        if not self.is_configured() or not items:
            return False
        
        item_texts = []
        for item in items[:5]:
            name = item.get('ItemName', 'Unknown')
            expiry = item.get('UsageExpiry') or item.get('WarrantyExpiry')
            item_texts.append(f"• {name} → {expiry}")
        
        message = f"⏰ *到期提醒*\n\n以下物品即將到期：\n" + "\n".join(item_texts)
        
        if with_auth:
            # Add link to auth
            login_url = url_for('auth.signin', _external=True)
            message += f"\n\n[登入系統]({login_url})"
        
        return self.send_message(chat_id, message)
    
    def send_low_stock_alert(self, chat_id: str, items: list, with_auth=False):
        """Send low stock alert"""
        if not self.is_configured() or not items:
            return False
        
        item_texts = []
        for item in items[:5]:
            name = item.get('ItemName', 'Unknown')
            qty = item.get('ItemQuantity', 0)
            min_qty = item.get('ItemStoreMin', 0)
            item_texts.append(f"• {name}: {qty}/{min_qty}")
        
        message = f"⚠️ *庫存不足*\n\n以下物品需要補貨：\n" + "\n".join(item_texts)
        
        if with_auth:
            login_url = url_for('auth.signin', _external=True)
            message += f"\n\n[登入系統]({login_url})"
        
        return self.send_message(chat_id, message)
    
    def set_webhook(self, webhook_url: str):
        """Set webhook URL"""
        return self._request('POST', 'setWebhook', {
            'url': webhook_url
        })
    
    def get_me(self):
        """Get bot info"""
        return self._request('POST', 'getMe')


telegram_notifier = TelegramBotNotifier()


def init_telegram_bot(app):
    """Initialize Telegram Bot"""
    global telegram_notifier
    telegram_notifier.init_app(app)


# Telegram Bot Webhook Handler Function
def handle_telegram_webhook(update: dict):
    """
    Handle incoming Telegram webhook.
    
    Args:
        update: Telegram update object
    
    Returns:
        Response message or None
    """
    if not update:
        return None
    
    message = update.get('message', {})
    if not message:
        return None
    
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    
    if not chat_id or not text:
        return None
    
    # Parse command
    command = text.strip().split()[0] if text else ''
    
    # Command handlers
    commands = {
        '/start': '歡迎使用物品管理系統！\n\n指令：\n/items - 物品列表\n/search <關鍵字> - 搜尋\n/help - 說明',
        '/help': '📖 物品管理系統 Bot\n\n可用指令：\n/start - 開始\n/items - 查看物品列表\n/search <關鍵字> - 搜尋物品\n/help - 說明',
        '/items': '請訪問網頁查看所有物品',
        '/status': '系統運作中 ✓',
    }
    
    # Add search command handler
    if text.startswith('/search '):
        keyword = text[8:].strip()
        return f'搜尋功能需訪問網頁使用\n關鍵字：{keyword}'
    
    response = commands.get(command, '未知指令，請輸入 /help')
    
    telegram_notifier.send_message(chat_id, response)
    return response