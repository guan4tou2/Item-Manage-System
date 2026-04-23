"""LINE Bot 通知服務（line-bot-sdk v3 messaging API）。

本模組設計為「安全可選」：
- 若未安裝 ``line-bot-sdk``，整個物件會處於未啟用狀態，呼叫各方法只會回傳 False。
- 若未設定 ``LINE_CHANNEL_ACCESS_TOKEN``，同樣處於未啟用狀態。

舊版 v2 SDK 的 import path（``from linebot import LineBotApi``）已不再使用。
"""

from __future__ import annotations

from typing import Iterable, Optional

try:
    from flask import current_app
except Exception:  # pragma: no cover
    current_app = None  # type: ignore[assignment]


class LineBotNotifier:
    """LINE 推送訊息封裝。"""

    def __init__(self, app=None):
        self._messaging = None  # MessagingApi 實例（v3）
        self._enabled = False
        if app is not None:
            self.init_app(app)

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------
    def init_app(self, app) -> None:
        token = (app.config.get("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()
        if not token:
            self._enabled = False
            return
        try:
            from linebot.v3.messaging import (  # type: ignore[import-not-found]
                ApiClient,
                Configuration,
                MessagingApi,
            )
        except ImportError:
            app.logger.info("line-bot-sdk 未安裝，LINE 通知將停用。")
            self._enabled = False
            return

        try:
            config = Configuration(access_token=token)
            self._messaging = MessagingApi(ApiClient(config))
            self._enabled = True
            app.logger.info("LINE Bot 已啟用。")
        except Exception as exc:  # pragma: no cover
            app.logger.warning("LINE Bot 初始化失敗：%s", exc)
            self._enabled = False

    # ------------------------------------------------------------------
    # 通用屬性
    # ------------------------------------------------------------------
    def is_configured(self) -> bool:
        return self._enabled and self._messaging is not None

    # ------------------------------------------------------------------
    # 推送
    # ------------------------------------------------------------------
    def _push(self, user_id: str, messages: list) -> bool:
        if not self.is_configured():
            return False
        try:
            from linebot.v3.messaging import PushMessageRequest  # type: ignore[import-not-found]

            self._messaging.push_message(
                PushMessageRequest(to=user_id, messages=messages)
            )
            return True
        except Exception as exc:  # pragma: no cover
            self._log_warning(f"LINE push 失敗：{exc}")
            return False

    def send_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        url: Optional[str] = None,
    ) -> bool:
        if not self.is_configured():
            return False
        from linebot.v3.messaging import TextMessage  # type: ignore[import-not-found]

        text = f"📢 {title}\n\n{body}"
        if url:
            text += f"\n\n👉 {url}"
        return self._push(user_id, [TextMessage(text=text)])

    def send_expiry_reminder(self, user_id: str, items: Iterable[dict]) -> bool:
        items = list(items)
        if not items:
            return False
        from linebot.v3.messaging import TextMessage  # type: ignore[import-not-found]

        lines = []
        for item in items[:5]:
            name = item.get("ItemName", "Unknown")
            expiry = item.get("UsageExpiry") or item.get("WarrantyExpiry") or ""
            lines.append(f"• {name} ({expiry})")
        text = "⏰ 到期提醒\n\n以下物品即將到期：\n" + "\n".join(lines)
        return self._push(user_id, [TextMessage(text=text)])

    def send_low_stock_alert(self, user_id: str, items: Iterable[dict]) -> bool:
        items = list(items)
        if not items:
            return False
        from linebot.v3.messaging import TextMessage  # type: ignore[import-not-found]

        lines = []
        for item in items[:5]:
            name = item.get("ItemName", "Unknown")
            qty = item.get("ItemQuantity", 0)
            min_qty = item.get("ItemStoreMin", 0)
            lines.append(f"• {name}: {qty}/{min_qty}")
        text = "⚠️ 庫存不足\n\n以下物品需要補貨：\n" + "\n".join(lines)
        return self._push(user_id, [TextMessage(text=text)])

    # ------------------------------------------------------------------
    # 內部
    # ------------------------------------------------------------------
    def _log_warning(self, message: str) -> None:
        if current_app is not None:
            try:
                current_app.logger.warning(message)
                return
            except Exception:
                pass
        import sys
        print(message, file=sys.stderr)


# 模組級單例（會被 ``init_line_bot`` 重新初始化）
line_notifier = LineBotNotifier()


def init_line_bot(app) -> None:
    """於 ``create_app`` 中呼叫以初始化通知器。"""
    line_notifier.init_app(app)
