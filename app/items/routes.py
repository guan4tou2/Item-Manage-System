import os
from typing import Dict, Any
from io import BytesIO

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
    send_file,
    current_app,
)

from app.services import (
    item_service,
    user_service,
    type_service,
    location_service,
)
import qrcode
import barcode
from barcode.writer import ImageWriter

bp = Blueprint("items", __name__)


def _require_login():
    if "UserID" not in session:
        return redirect(url_for("auth.signin"))
    return None


def _current_user() -> Dict[str, Any]:
    user_id = session.get("UserID")
    user = user_service.get_user(user_id) if user_id else None
    return user or {"User": user_id, "admin": False}


@bp.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@bp.route("/home")
def home():
    need = _require_login()
    if need:
        return need

    filters = {
        "q": request.args.get("q", ""),
        "place": request.args.get("place", ""),
        "type": request.args.get("type", ""),
        "floor": request.args.get("floor", ""),
        "room": request.args.get("room", ""),
        "zone": request.args.get("zone", ""),
        "sort": request.args.get("sort", ""),
    }
    items = item_service.list_items(filters)
    user = _current_user()
    types = type_service.list_types()
    floors, rooms, zones = location_service.list_choices()
    return render_template(
        "home.html",
        User=user,
        items=items,
        itemtype=types,
        floors=floors,
        rooms=rooms,
        zones=zones,
        selected_sort=filters["sort"],
    )


@bp.route("/additem", methods=["GET", "POST"])
def additem():
    need = _require_login()
    if need:
        return need

    user = _current_user()
    types = type_service.list_types()
    floors, rooms, zones = location_service.list_choices()

    if request.method == "POST":
        form = dict(request.form)
        ok, msg = item_service.create_item(form, request.files.get("ItemPic"))
        if ok:
            flash("物品新增成功！", "success")
            return redirect(url_for("items.home"))
        else:
            flash(msg, "danger")
            return render_template(
                "additem.html",
                User=user,
                itemtype=types,
                floors=floors,
                rooms=rooms,
                zones=zones,
                form=form,
            )

    return render_template(
        "additem.html",
        User=user,
        itemtype=types,
        floors=floors,
        rooms=rooms,
        zones=zones,
    )


@bp.route("/manageitem", methods=["GET", "POST"])
def manageitem():
    need = _require_login()
    if need:
        return need

    user = _current_user()

    if request.method == "POST":
        item_id = request.form.get("item_id")
        new_place = request.form.get("new_place", "").strip()
        new_floor = request.form.get("ItemFloor", "").strip()
        new_room = request.form.get("ItemRoom", "").strip()
        new_zone = request.form.get("ItemZone", "").strip()
        updates = {}
        if new_place:
            updates["ItemStorePlace"] = new_place
        if new_floor:
            updates["ItemFloor"] = new_floor
        if new_room:
            updates["ItemRoom"] = new_room
        if new_zone:
            updates["ItemZone"] = new_zone
        if item_id and updates:
            item_service.update_item_place(item_id, updates)
            flash("物品位置更新成功！", "success")
        else:
            flash("請輸入位置資訊", "danger")
        return redirect(url_for("items.manageitem"))

    filters = {"q": "", "place": "", "type": "", "floor": "", "room": "", "zone": "", "sort": ""}
    items = item_service.list_items(filters)
    floors, rooms, zones = location_service.list_choices()
    return render_template("manageitem.html", User=user, items=items, floors=floors, rooms=rooms, zones=zones)


@bp.route("/search")
def search():
    need = _require_login()
    if need:
        return need

    user = _current_user()
    query = request.args.get("q", "")
    place = request.args.get("place", "")
    item_type = request.args.get("type", "")
    floor = request.args.get("floor", "")
    room = request.args.get("room", "")
    zone = request.args.get("zone", "")
    sort = request.args.get("sort", "")
    items = item_service.list_items(
        {
            "q": query,
            "place": place,
            "type": item_type,
            "floor": floor,
            "room": room,
            "zone": zone,
            "sort": sort,
        }
    )
    types = type_service.list_types()
    floors, rooms, zones = location_service.list_choices()
    return render_template(
        "search.html",
        User=user,
        items=items,
        query=query,
        place=place,
        itemtype=types,
        selected_type=item_type,
        floors=floors,
        rooms=rooms,
        zones=zones,
        selected_sort=sort,
    )


@bp.route("/scan")
def scan():
    need = _require_login()
    if need:
        return need
    user = _current_user()
    return render_template("scan.html", User=user)


@bp.route("/items/<item_id>/qrcode")
def qrcode_image(item_id: str):
    item = item_service.get_item(item_id)
    if not item:
        flash("找不到物品", "danger")
        return redirect(url_for("items.home"))

    img = qrcode.make(f"item:{item_id}")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name=f"{item_id}_qrcode.png")


@bp.route("/items/<item_id>/barcode")
def barcode_image(item_id: str):
    item = item_service.get_item(item_id)
    if not item:
        flash("找不到物品", "danger")
        return redirect(url_for("items.home"))

    code = barcode.get("code128", item_id, writer=ImageWriter())
    buf = BytesIO()
    code.write(buf)
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name=f"{item_id}_barcode.png")

