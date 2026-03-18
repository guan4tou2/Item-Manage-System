import json
import secrets
from datetime import datetime, timezone
from urllib import parse as urlparse
from urllib import request as urlrequest

from flask import Blueprint, abort, current_app, jsonify, redirect, request, session, url_for
from itsdangerous import BadSignature, URLSafeSerializer

from app import csrf, db
from app.models import TelegramUserLink, Travel, TravelItem
from app.utils.auth import login_required

bp = Blueprint("telegram", __name__, url_prefix="/telegram")


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt="telegram-account-link")


def _telegram_api(method: str, payload: dict) -> tuple[bool, dict]:
    token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return False, {"error": "telegram_bot_token_missing"}
    req = urlrequest.Request(
        url=f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=8) as resp:
            body = json.loads(resp.read().decode("utf-8") or "{}")
            return True, body
    except Exception as exc:
        return False, {"error": str(exc)}


def _send_message(chat_id: str, text: str, inline_keyboard: list[list[dict]] | None = None) -> None:
    payload = {"chat_id": chat_id, "text": text[:4000]}
    if inline_keyboard:
        payload["reply_markup"] = {"inline_keyboard": inline_keyboard}
    _telegram_api("sendMessage", payload)


def _get_linked_user(telegram_user_id: str) -> str | None:
    link = TelegramUserLink.query.filter_by(telegram_user_id=telegram_user_id).first()
    return link.user_id if link else None


def _upsert_link(user_id: str, telegram_user_id: str, chat_id: str) -> None:
    link = TelegramUserLink.query.filter_by(telegram_user_id=telegram_user_id).first()
    if not link:
        link = TelegramUserLink(user_id=user_id, telegram_user_id=telegram_user_id, chat_id=chat_id)
        db.session.add(link)
    else:
        link.user_id = user_id
        link.chat_id = chat_id
        link.last_seen_at = datetime.now(timezone.utc)
    db.session.commit()


def _travel_summary_for(user_id: str) -> str:
    travels = Travel.query.filter_by(owner=user_id).order_by(Travel.created_at.desc()).limit(5).all()
    if not travels:
        return "目前沒有旅行清單。"
    rows = []
    for travel in travels:
        total = TravelItem.query.filter_by(travel_id=travel.id).count()
        packed = TravelItem.query.filter_by(travel_id=travel.id, carried=True).count()
        rows.append(f"- {travel.id} {travel.name} ({packed}/{total})")
    return "你的旅行:\n" + "\n".join(rows)


def _items_for(user_id: str, scope: str) -> list[TravelItem]:
    query = (
        db.session.query(TravelItem)
        .join(Travel, TravelItem.travel_id == Travel.id)
        .filter(Travel.owner == user_id)
    )
    if scope == "personal":
        query = query.filter(TravelItem.list_scope == "personal", TravelItem.assignee == user_id)
    else:
        query = query.filter(TravelItem.list_scope == "common")
    return query.order_by(TravelItem.created_at.desc()).limit(8).all()


def _items_summary_for(user_id: str, scope: str) -> str:
    items = _items_for(user_id, scope)
    if not items:
        return "目前沒有可顯示項目。"
    title = "共同攜帶清單" if scope == "common" else "你的個人攜帶清單"
    rows = [f"- {item.id} {item.name} ({item.qty_packed}/{item.qty_required}) {'✔' if item.carried else '✘'}" for item in items]
    return title + ":\n" + "\n".join(rows)


def _done_buttons_for(user_id: str, scope: str) -> list[list[dict]]:
    items = [item for item in _items_for(user_id, scope) if not item.carried][:6]
    rows: list[list[dict]] = []
    for item in items:
        rows.append([
            {
                "text": f"完成 {item.name[:12]}",
                "callback_data": f"done:{item.id}",
            }
        ])
    rows.append(
        [
            {"text": "我的旅行", "callback_data": "cmd:my_trips"},
            {"text": "共同清單", "callback_data": "cmd:common"},
            {"text": "我的清單", "callback_data": "cmd:personal"},
        ]
    )
    return rows


def _handle_text(telegram_user_id: str, chat_id: str, text: str) -> tuple[str, list[list[dict]] | None]:
    linked_user = _get_linked_user(telegram_user_id)
    normalized = (text or "").strip()

    if normalized.startswith("/start"):
        parts = normalized.split(maxsplit=1)
        if len(parts) > 1:
            token = parts[1].strip()
            try:
                payload = _serializer().loads(token)
                user_id = payload.get("u")
                if user_id:
                    _upsert_link(user_id, telegram_user_id, chat_id)
                    return "已完成 Telegram 帳號綁定。", _done_buttons_for(user_id, "common")
            except BadSignature:
                pass
        return "歡迎使用！請先從網站點擊 Telegram 綁定連結。", None

    if not linked_user:
        return "尚未綁定帳號，請先在網站通知設定頁完成 Telegram 綁定。", None

    if normalized in {"我的旅行", "/trips"}:
        return _travel_summary_for(linked_user), _done_buttons_for(linked_user, "common")
    if normalized in {"共同清單", "/common"}:
        return _items_summary_for(linked_user, "common"), _done_buttons_for(linked_user, "common")
    if normalized in {"我的清單", "/personal"}:
        return _items_summary_for(linked_user, "personal"), _done_buttons_for(linked_user, "personal")
    if normalized.startswith("打包完成 "):
        item_id = normalized.replace("打包完成 ", "", 1).strip()
        if not item_id.isdigit():
            return "格式錯誤，請輸入：打包完成 <項目ID>", None
        return _mark_done(linked_user, int(item_id))
    return "可用指令：我的旅行、共同清單、我的清單、打包完成 <項目ID>。", _done_buttons_for(linked_user, "common")


def _mark_done(user_id: str, item_id: int) -> tuple[str, list[list[dict]] | None]:
    item = db.session.get(TravelItem, item_id)
    if not item:
        return "找不到該項目。", None
    travel = db.session.get(Travel, item.travel_id)
    if not travel or travel.owner != user_id:
        return "你無法操作此項目。", None
    item.carried = True
    item.qty_packed = max(item.qty_packed, item.qty_required)
    db.session.commit()
    scope = item.list_scope if item.list_scope in {"common", "personal"} else "common"
    return f"已標記完成：{item.name}", _done_buttons_for(user_id, scope)


def _handle_callback(telegram_user_id: str, callback_data: str) -> tuple[str, list[list[dict]] | None]:
    linked_user = _get_linked_user(telegram_user_id)
    if not linked_user:
        return "尚未綁定帳號，請先在網站通知設定頁完成 Telegram 綁定。", None

    if callback_data.startswith("done:"):
        item_id = callback_data.replace("done:", "", 1)
        if not item_id.isdigit():
            return "無效項目。", None
        return _mark_done(linked_user, int(item_id))

    if callback_data == "cmd:my_trips":
        return _travel_summary_for(linked_user), _done_buttons_for(linked_user, "common")
    if callback_data == "cmd:common":
        return _items_summary_for(linked_user, "common"), _done_buttons_for(linked_user, "common")
    if callback_data == "cmd:personal":
        return _items_summary_for(linked_user, "personal"), _done_buttons_for(linked_user, "personal")

    return "未知操作。", None


@bp.route("/webhook", methods=["POST"])
@csrf.exempt
def webhook():
    secret = current_app.config.get("TELEGRAM_WEBHOOK_SECRET", "")
    if not secret:
        return jsonify({"error": "webhook_secret_not_configured"}), 401
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if header_secret != secret:
        return jsonify({"error": "invalid_secret"}), 401

    payload = request.get_json(silent=True) or {}

    message = payload.get("message")
    if message:
        from_user = message.get("from") or {}
        chat = message.get("chat") or {}
        telegram_user_id = str(from_user.get("id") or "")
        chat_id = str(chat.get("id") or "")
        text = message.get("text") or ""
        if telegram_user_id and chat_id:
            reply_text, keyboard = _handle_text(telegram_user_id, chat_id, text)
            _send_message(chat_id, reply_text, keyboard)

    callback_query = payload.get("callback_query")
    if callback_query:
        from_user = callback_query.get("from") or {}
        message = callback_query.get("message") or {}
        chat = message.get("chat") or {}
        telegram_user_id = str(from_user.get("id") or "")
        chat_id = str(chat.get("id") or "")
        callback_data = callback_query.get("data") or ""
        if telegram_user_id and chat_id:
            reply_text, keyboard = _handle_callback(telegram_user_id, callback_data)
            _send_message(chat_id, reply_text, keyboard)

    return jsonify({"ok": True})


@bp.route("/link", methods=["GET"])
@login_required
def link():
    bot_username = current_app.config.get("TELEGRAM_BOT_USERNAME", "")
    if not bot_username:
        abort(400)
    user_id = session.get("UserID")
    if not user_id:
        return redirect(url_for("auth.signin"))
    token = _serializer().dumps({"u": user_id, "n": secrets.token_urlsafe(16)})
    query = urlparse.urlencode({"start": token})
    return redirect(f"https://t.me/{bot_username}?{query}")


@bp.route("/api/links/me", methods=["GET"])
@login_required
def my_link_status():
    user_id = session.get("UserID")
    link = TelegramUserLink.query.filter_by(user_id=user_id).first()
    return jsonify(
        {
            "linked": bool(link),
            "telegram_user_id": link.telegram_user_id if link else None,
            "chat_id": link.chat_id if link else None,
        }
    )
