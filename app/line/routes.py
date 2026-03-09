import base64
import hashlib
import hmac
import json
import secrets
from urllib.parse import parse_qs
from urllib import request as urlrequest

from flask import Blueprint, abort, current_app, jsonify, redirect, request, session, url_for
from itsdangerous import BadSignature, URLSafeSerializer

from app import csrf, db
from app.models import LineUserLink, Travel, TravelItem
from app.utils.auth import login_required

bp = Blueprint("line", __name__, url_prefix="/line")


def _line_serializer() -> URLSafeSerializer:
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt="line-account-link")


def _verify_signature(raw_body: bytes, signature: str | None) -> bool:
    channel_secret = current_app.config.get("LINE_CHANNEL_SECRET", "")
    if not channel_secret or not signature:
        return False
    digest = hmac.new(channel_secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def _line_api_post(path: str, payload: dict) -> tuple[bool, dict]:
    token = current_app.config.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        return False, {"error": "line_channel_access_token_missing"}

    req = urlrequest.Request(
        url=f"https://api.line.me{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=8) as resp:
            body = resp.read().decode("utf-8") or "{}"
            return True, json.loads(body)
    except Exception as exc:
        return False, {"error": str(exc)}


def _default_quick_reply_items() -> list[dict]:
    return [
        {
            "type": "action",
            "action": {
                "type": "postback",
                "label": "我的旅行",
                "data": "cmd=my_trips",
                "displayText": "我的旅行",
            },
        },
        {
            "type": "action",
            "action": {
                "type": "postback",
                "label": "共同清單",
                "data": "cmd=common_list",
                "displayText": "共同清單",
            },
        },
        {
            "type": "action",
            "action": {
                "type": "postback",
                "label": "我的清單",
                "data": "cmd=personal_list",
                "displayText": "我的清單",
            },
        },
        {
            "type": "action",
            "action": {
                "type": "message",
                "label": "連結帳號",
                "text": "連結帳號",
            },
        },
    ]


def _travel_flex_for(user_id: str) -> dict | None:
    travels = Travel.query.filter_by(owner=user_id).order_by(Travel.created_at.desc()).limit(5).all()
    if not travels:
        return None

    rows = []
    for travel in travels:
        total = TravelItem.query.filter_by(travel_id=travel.id).count()
        packed = TravelItem.query.filter_by(travel_id=travel.id, carried=True).count()
        rows.append(
            {
                "type": "box",
                "layout": "baseline",
                "spacing": "sm",
                "contents": [
                    {"type": "text", "text": travel.name[:18], "size": "sm", "weight": "bold", "flex": 4},
                    {"type": "text", "text": f"{packed}/{total}", "size": "xs", "color": "#666666", "flex": 2, "align": "end"},
                ],
            }
        )

    return {
        "type": "flex",
        "altText": "旅行清單摘要",
        "contents": {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "我的旅行", "weight": "bold", "size": "lg"},
                    {"type": "text", "text": "打包進度", "size": "xs", "color": "#888888"},
                ],
            },
            "body": {"type": "box", "layout": "vertical", "spacing": "md", "contents": rows},
        },
    }


def _items_flex_for(user_id: str, scope: str) -> dict | None:
    query = (
        db.session.query(TravelItem)
        .join(Travel, TravelItem.travel_id == Travel.id)
        .filter(Travel.owner == user_id)
    )
    title = "共同攜帶"
    if scope == "personal":
        title = "我的攜帶"
        query = query.filter(TravelItem.list_scope == "personal", TravelItem.assignee == user_id)
    else:
        query = query.filter(TravelItem.list_scope == "common")

    items = query.order_by(TravelItem.created_at.desc()).limit(6).all()
    if not items:
        return None

    rows = []
    for item in items:
        state = "已完成" if item.carried else "未完成"
        color = "#1A7F37" if item.carried else "#B42318"
        rows.append(
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": [
                    {"type": "text", "text": item.name[:14], "size": "sm", "flex": 4},
                    {"type": "text", "text": f"{item.qty_packed}/{item.qty_required}", "size": "xs", "color": "#666666", "flex": 2, "align": "end"},
                    {"type": "text", "text": state, "size": "xs", "color": color, "flex": 2, "align": "end"},
                ],
            }
        )

    return {
        "type": "flex",
        "altText": f"{title}清單摘要",
        "contents": {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": title, "weight": "bold", "size": "lg"},
                    {"type": "text", "text": "可直接用下方按鈕標記完成", "size": "xs", "color": "#888888"},
                ],
            },
            "body": {"type": "box", "layout": "vertical", "spacing": "md", "contents": rows},
        },
    }


def _reply_message(
    reply_token: str,
    text: str,
    extra_quick_reply_items: list[dict] | None = None,
    flex_message: dict | None = None,
) -> None:
    quick_reply_items = list(extra_quick_reply_items or [])
    quick_reply_items.extend(_default_quick_reply_items())
    quick_reply_items = quick_reply_items[:13]

    messages = []
    if flex_message:
        messages.append(flex_message)
    messages.append(
        {
            "type": "text",
            "text": text[:1000],
            "quickReply": {"items": quick_reply_items},
        }
    )

    _line_api_post(
        "/v2/bot/message/reply",
        {
            "replyToken": reply_token,
            "messages": messages,
        },
    )


def _get_linked_user(line_user_id: str) -> str | None:
    link = LineUserLink.query.filter_by(line_user_id=line_user_id).first()
    return link.user_id if link else None


def _upsert_link(user_id: str, line_user_id: str) -> None:
    link = LineUserLink.query.filter_by(line_user_id=line_user_id).first()
    if not link:
        link = LineUserLink(user_id=user_id, line_user_id=line_user_id)
        db.session.add(link)
    else:
        link.user_id = user_id
    db.session.commit()


def _travel_summary_for(user_id: str) -> str:
    travels = Travel.query.filter_by(owner=user_id).order_by(Travel.created_at.desc()).limit(5).all()
    if not travels:
        return "目前沒有旅行清單。"
    lines = [f"- {t.id}: {t.name}" for t in travels]
    return "你的旅行:\n" + "\n".join(lines)


def _common_items_for(user_id: str) -> str:
    items = (
        db.session.query(TravelItem)
        .join(Travel, TravelItem.travel_id == Travel.id)
        .filter(Travel.owner == user_id, TravelItem.list_scope == "common")
        .order_by(TravelItem.created_at.desc())
        .limit(8)
        .all()
    )
    if not items:
        return "目前沒有共同攜帶物品。"
    lines = [f"- {i.id}: {i.name} ({i.qty_packed}/{i.qty_required})" for i in items]
    return "共同攜帶清單:\n" + "\n".join(lines)


def _personal_items_for(user_id: str) -> str:
    items = (
        db.session.query(TravelItem)
        .join(Travel, TravelItem.travel_id == Travel.id)
        .filter(Travel.owner == user_id, TravelItem.list_scope == "personal", TravelItem.assignee == user_id)
        .order_by(TravelItem.created_at.desc())
        .limit(8)
        .all()
    )
    if not items:
        return "目前沒有你的個人攜帶物品。"
    lines = [f"- {i.id}: {i.name} ({i.qty_packed}/{i.qty_required})" for i in items]
    return "你的個人攜帶清單:\n" + "\n".join(lines)


def _pending_items_quick_reply(user_id: str, scope: str) -> list[dict]:
    query = (
        db.session.query(TravelItem)
        .join(Travel, TravelItem.travel_id == Travel.id)
        .filter(Travel.owner == user_id, TravelItem.carried.is_(False))
    )
    if scope == "personal":
        query = query.filter(TravelItem.list_scope == "personal", TravelItem.assignee == user_id)
    else:
        query = query.filter(TravelItem.list_scope == "common")

    items = query.order_by(TravelItem.created_at.desc()).limit(6).all()
    quick_items: list[dict] = []
    for item in items:
        quick_items.append(
            {
                "type": "action",
                "action": {
                    "type": "postback",
                    "label": f"完成 {item.name[:10]}",
                    "data": f"cmd=mark_done&item_id={item.id}",
                    "displayText": f"打包完成 {item.id}",
                },
            }
        )
    return quick_items


def _handle_text_message(line_user_id: str, text: str) -> tuple[str, list[dict], dict | None]:
    user_id = _get_linked_user(line_user_id)
    if text.strip() == "連結帳號":
        ok, data = _line_api_post(f"/v2/bot/user/{line_user_id}/linkToken", {})
        if not ok:
            return "目前無法建立連結，請稍後再試。", [], None
        link_token = data.get("linkToken")
        if not link_token:
            return "目前無法建立連結，請稍後再試。", [], None
        app_link = url_for("line.account_link", linkToken=link_token, _external=True)
        return f"請點擊連結綁定帳號:\n{app_link}", [], None

    if not user_id:
        return "請先輸入「連結帳號」完成綁定。", [], None

    normalized = text.strip()
    if normalized == "我的旅行":
        return _travel_summary_for(user_id), [], _travel_flex_for(user_id)
    if normalized == "共同清單":
        return _common_items_for(user_id), _pending_items_quick_reply(user_id, "common"), _items_flex_for(user_id, "common")
    if normalized == "我的清單":
        return _personal_items_for(user_id), _pending_items_quick_reply(user_id, "personal"), _items_flex_for(user_id, "personal")
    if normalized.startswith("打包完成 "):
        item_id = normalized.replace("打包完成 ", "", 1).strip()
        if not item_id.isdigit():
            return "格式錯誤，請輸入：打包完成 <項目ID>", [], None
        item = db.session.get(TravelItem, int(item_id))
        if not item:
            return "找不到該項目。", [], None
        travel = db.session.get(Travel, item.travel_id)
        if not travel or travel.owner != user_id:
            return "你無法操作此項目。", [], None
        item.carried = True
        item.qty_packed = max(item.qty_packed, item.qty_required)
        db.session.commit()
        return f"已標記完成：{item.name}", [], None
    return "可用指令：我的旅行、共同清單、我的清單、打包完成 <項目ID>、連結帳號", [], None


def _handle_postback(line_user_id: str, data: str) -> tuple[str, list[dict], dict | None]:
    if not data:
        return "無效操作。", [], None
    user_id = _get_linked_user(line_user_id)
    if not user_id:
        return "請先輸入「連結帳號」完成綁定。", [], None

    parsed = parse_qs(data, keep_blank_values=False)
    command = (parsed.get("cmd") or [""])[0]
    if command == "my_trips":
        return _travel_summary_for(user_id), [], _travel_flex_for(user_id)
    if command == "common_list":
        return _common_items_for(user_id), _pending_items_quick_reply(user_id, "common"), _items_flex_for(user_id, "common")
    if command == "personal_list":
        return _personal_items_for(user_id), _pending_items_quick_reply(user_id, "personal"), _items_flex_for(user_id, "personal")
    if command == "mark_done":
        item_id = (parsed.get("item_id") or [""])[0]
        if not item_id.isdigit():
            return "項目ID格式錯誤。", [], None
        item = db.session.get(TravelItem, int(item_id))
        if not item:
            return "找不到該項目。", [], None
        travel = db.session.get(Travel, item.travel_id)
        if not travel or travel.owner != user_id:
            return "你無法操作此項目。", [], None
        item.carried = True
        item.qty_packed = max(item.qty_packed, item.qty_required)
        db.session.commit()
        return f"已標記完成：{item.name}", [], None
    return "未知操作。", [], None


@bp.route("/webhook", methods=["POST"])
@csrf.exempt
def webhook():
    raw_body = request.get_data(cache=True)
    signature = request.headers.get("X-Line-Signature")
    if not _verify_signature(raw_body, signature):
        return jsonify({"error": "invalid_signature"}), 401

    try:
        body = json.loads(raw_body.decode("utf-8") or "{}")
    except Exception:
        body = {}
    events = body.get("events") or []

    for event in events:
        event_type = event.get("type")
        source = event.get("source") or {}
        line_user_id = source.get("userId")
        reply_token = event.get("replyToken")

        if event_type == "accountLink" and line_user_id:
            link_info = event.get("link") or {}
            nonce = link_info.get("nonce")
            result = link_info.get("result")
            if result == "ok" and nonce:
                try:
                    payload = _line_serializer().loads(nonce)
                    target_user_id = payload.get("u")
                    if target_user_id:
                        _upsert_link(target_user_id, line_user_id)
                except BadSignature:
                    pass
            continue

        if event_type == "message" and line_user_id and reply_token:
            message = event.get("message") or {}
            if message.get("type") == "text":
                reply_text, quick_items, flex_message = _handle_text_message(line_user_id, message.get("text", ""))
                _reply_message(reply_token, reply_text, quick_items, flex_message)

        if event_type == "postback" and line_user_id and reply_token:
            postback = event.get("postback") or {}
            reply_text, quick_items, flex_message = _handle_postback(line_user_id, postback.get("data", ""))
            _reply_message(reply_token, reply_text, quick_items, flex_message)

    return jsonify({"ok": True})


@bp.route("/account-link", methods=["GET"])
@login_required
def account_link():
    link_token = request.args.get("linkToken", "")
    if not link_token:
        abort(400)

    user_id = session.get("UserID")
    if not user_id:
        return redirect(url_for("auth.signin"))

    nonce = _line_serializer().dumps({"u": user_id, "n": secrets.token_urlsafe(16)})
    redirect_url = f"https://access.line.me/dialog/bot/accountLink?linkToken={link_token}&nonce={nonce}"
    return redirect(redirect_url)


@bp.route("/api/links/me", methods=["GET"])
@login_required
def my_link_status():
    user_id = session.get("UserID")
    link = LineUserLink.query.filter_by(user_id=user_id).first()
    return jsonify(
        {
            "linked": bool(link),
            "line_user_id": link.line_user_id if link else None,
        }
    )
