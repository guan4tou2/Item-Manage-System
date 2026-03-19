from io import BytesIO, StringIO
import json
import csv
from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
    send_file,
    current_app,
    jsonify,
    Response,
    session,
)
from flask_babel import gettext as _

from typing import Any, Dict, List

from app.services import (
    item_service,
    type_service,
    location_service,
)
from app.services import log_service
from app.services import custom_field_service
from app import limiter
from app.repositories import user_repo
from app.utils.auth import login_required, admin_required, get_current_user
from app.models.item import Item
from app.models.item_type import ItemType
from app.models.location import Location
import qrcode
import barcode
from barcode.writer import ImageWriter

bp = Blueprint("items", __name__)



@bp.route("/uploads/<filename>")
@login_required
def uploaded_file(filename):
    from flask import abort
    try:
        # 檢查檔案是否屬於使用者有權限存取的物品
        user_id = session.get("UserID", "")
        user = get_current_user()
        if not user.get("admin"):
            from app import get_db_type, mongo
            db_type = get_db_type()
            if db_type == "postgres":
                item = Item.query.filter(
                    (Item.ItemPic == filename) | (Item.ItemThumb == filename)
                ).first()
                if item:
                    visibility = getattr(item, "visibility", "private") or "private"
                    if visibility == "private":
                        shared = item.shared_with or []
                        owner = item.ItemOwner or ""
                        if owner != user_id and user_id not in shared:
                            abort(403)
            else:
                item = mongo.db.items.find_one(
                    {"$or": [{"ItemPic": filename}, {"ItemThumb": filename}]}
                )
                if item:
                    visibility = item.get("visibility", "private") or "private"
                    if visibility == "private":
                        shared = item.get("shared_with") or []
                        owner = item.get("ItemOwner", "")
                        if owner != user_id and user_id not in shared:
                            abort(403)
        return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
    except (FileNotFoundError, OSError):
        abort(404)


_DEFAULT_DASHBOARD_WIDGETS = json.dumps([
    {"type": "alerts", "visible": True},
    {"type": "expiring", "visible": True},
    {"type": "low_stock", "visible": True},
    {"type": "maintenance", "visible": True},
    {"type": "quick_actions", "visible": True},
    {"type": "activity", "visible": True},
])


@bp.route("/api/dashboard/widgets", methods=["POST"])
@login_required
def save_dashboard_widgets():
    """Save user's dashboard widget configuration."""
    from app import db, get_db_type
    from flask import abort

    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify({"error": "invalid payload"}), 400

    # Validate each entry has required keys
    for entry in data:
        if not isinstance(entry, dict) or "type" not in entry or "visible" not in entry:
            return jsonify({"error": "invalid widget entry"}), 400

    widgets_json = json.dumps(data)

    db_type = get_db_type()
    if db_type == "postgres":
        from app.models.user import User as UserModel
        user_id = session.get("UserID")
        user_obj = UserModel.query.get(user_id)
        if not user_obj:
            abort(404)
        user_obj.dashboard_widgets = widgets_json
        db.session.commit()
    else:
        from app import mongo
        mongo.db.user.update_one(
            {"_id": session.get("UserID")},
            {"$set": {"dashboard_widgets": widgets_json}},
        )

    return jsonify({"ok": True})


@bp.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    settings = user_repo.get_notification_settings(session.get("UserID", ""))
    expiring = item_service.get_expiring_items(settings.get("notify_days", 30))
    low_stock = item_service.get_low_stock_items()
    replacement = item_service.get_replacement_items(settings)
    stats = item_service.get_stats()
    recent_logs = log_service.get_recent_logs(limit=10)

    # Load widget config – fall back to default if not yet set
    raw_widgets = getattr(user, "dashboard_widgets", None)
    if not raw_widgets:
        raw_widgets = _DEFAULT_DASHBOARD_WIDGETS
    try:
        widget_config = json.loads(raw_widgets)
    except (TypeError, ValueError):
        widget_config = json.loads(_DEFAULT_DASHBOARD_WIDGETS)

    # Build a quick-access dict: type -> visible
    widget_visibility = {w["type"]: w.get("visible", True) for w in widget_config}

    overdue_loans_count = 0
    try:
        from app.services import loan_service
        overdue_loans_count = loan_service.get_overdue_count()
    except Exception:
        pass

    return render_template(
        "dashboard.html",
        User=user,
        expiring_items=expiring.get("near_expiry", [])[:5],
        expired_items=expiring.get("expired", [])[:5],
        expiring_count=expiring.get("near_count", 0) + expiring.get("expired_count", 0),
        low_stock_items=low_stock.get("low_stock", [])[:5],
        low_stock_count=low_stock.get("low_stock_count", 0),
        maintenance_due=replacement.get("due", [])[:5],
        maintenance_count=len(replacement.get("due", [])),
        stats=stats,
        recent_logs=recent_logs,
        overdue_loans_count=overdue_loans_count,
        widget_config=widget_config,
        widget_visibility=widget_visibility,
    )


@bp.route("/home")
@login_required
def home():
    filters = {
        "q": request.args.get("q", ""),
        "place": request.args.get("place", ""),
        "type": request.args.get("type", ""),
        "floor": request.args.get("floor", ""),
        "room": request.args.get("room", ""),
        "zone": request.args.get("zone", ""),
        "visibility": request.args.get("visibility", ""),
        "sort": request.args.get("sort", ""),
        "condition": request.args.get("condition", ""),
    }
    page = request.args.get("page", 1, type=int)
    user = get_current_user()
    result = item_service.list_items(filters, page=page, current_username=user.get("User", ""))
    types = type_service.list_types()
    floors, rooms, zones = location_service.list_choices()
    stats = item_service.get_stats()
    notification_settings = user_repo.get_notification_settings(session.get("UserID", ""))
    replacement = item_service.get_replacement_items(notification_settings)
    item_service.annotate_maintenance_alerts(result["items"], notification_settings)
    return render_template(
        "home.html",
        User=user,
        items=result["items"],
        itemtype=types,
        floors=floors,
        rooms=rooms,
        zones=zones,
        selected_sort=filters["sort"],
        pagination=result,
        stats=stats,
        maintenance_due_count=len(replacement["due"]),
        maintenance_upcoming_count=len(replacement["upcoming"]),
    )


@bp.route("/additem", methods=["GET", "POST"])
@admin_required
def additem():
    user = get_current_user()
    types = type_service.list_types()
    floors, rooms, zones = location_service.list_choices()
    try:
        custom_fields = custom_field_service.list_fields()
    except Exception:
        custom_fields = []

    if request.method == "POST":
        form = dict(request.form)
        all_pics = request.files.getlist("ItemPic")
        main_pic = all_pics[0] if all_pics else None
        extra_pics = all_pics[1:] if len(all_pics) > 1 else []
        ok, msg = item_service.create_item(form, main_pic, extra_files=extra_pics)
        if ok:
            # Save custom field values after item creation
            item_id = form.get("ItemID", "").strip()
            try:
                if item_id and custom_fields:
                    custom_field_service.save_item_custom_values(item_id, form)
            except Exception:
                pass
            flash(_("物品新增成功！"), "success")
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
                custom_fields=custom_fields,
                custom_values={},
            )

    return render_template(
        "additem.html",
        User=user,
        itemtype=types,
        floors=floors,
        rooms=rooms,
        zones=zones,
        custom_fields=custom_fields,
        custom_values={},
    )


@bp.route("/manageitem", methods=["GET", "POST"])
@admin_required
def manageitem():
    user = get_current_user()
    notification_settings = user_repo.get_notification_settings(session.get("UserID", ""))

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
            flash(_("物品位置更新成功！"), "success")
        else:
            flash(_("請輸入位置資訊"), "danger")
        return redirect(url_for("items.manageitem"))

    maintenance = request.args.get("maintenance", "")
    filters = {"q": "", "place": "", "type": "", "floor": "", "room": "", "zone": "", "sort": ""}
    page = request.args.get("page", 1, type=int)
    _username = user.get("User", "")
    if maintenance:
        base_result = item_service.list_items(filters, page=1, page_size=5000, current_username=_username)
        item_service.annotate_maintenance_alerts(base_result["items"], notification_settings)
        filtered_items = item_service.filter_items_by_maintenance(base_result["items"], maintenance)
        result = item_service.paginate_items(filtered_items, page=page)
    else:
        result = item_service.list_items(filters, page=page, current_username=_username)
    item_service.annotate_maintenance_alerts(result["items"], notification_settings)
    floors, rooms, zones = location_service.list_choices()
    return render_template(
        "manageitem.html",
        User=user,
        items=result["items"],
        floors=floors,
        rooms=rooms,
        zones=zones,
        pagination=result,
        selected_maintenance=maintenance,
    )


@bp.route("/edititem/<item_id>", methods=["GET", "POST"])
@admin_required
def edititem(item_id: str):
    user = get_current_user()
    item = item_service.get_item(item_id)

    if not item:
        flash(_("找不到該物品"), "danger")
        return redirect(url_for("items.home"))

    types = type_service.list_types()
    floors, rooms, zones = location_service.list_choices()
    try:
        custom_fields = custom_field_service.list_fields()
        existing_cf_values = custom_field_service.get_item_custom_values(item_id)
        custom_values = {str(v["field_id"]): v["value"] for v in existing_cf_values}
    except Exception:
        custom_fields = []
        custom_values = {}

    if request.method == "POST":
        form = dict(request.form)
        all_pics = request.files.getlist("ItemPic")
        main_pic = all_pics[0] if all_pics else None
        extra_pics = all_pics[1:] if len(all_pics) > 1 else []
        ok, msg = item_service.update_item(item_id, form, main_pic, extra_files=extra_pics)
        if ok:
            try:
                if custom_fields:
                    custom_field_service.save_item_custom_values(item_id, form)
            except Exception:
                pass
            flash(msg, "success")
            return redirect(url_for("items.home"))
        else:
            flash(msg, "danger")

    return render_template(
        "edititem.html",
        User=user,
        item=item,
        itemtype=types,
        floors=floors,
        rooms=rooms,
        zones=zones,
        custom_fields=custom_fields,
        custom_values=custom_values,
    )


@bp.route("/deleteitem/<item_id>", methods=["POST"])
@admin_required
def deleteitem(item_id: str):
    ok, msg = item_service.delete_item(item_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("items.manageitem"))


@bp.route("/batch/move", methods=["POST"])
@admin_required
def batch_move():
    """批量移動物品"""
    user = get_current_user()
    item_ids = request.form.get("item_ids", "").split(",")
    new_place = request.form.get("new_place", "").strip()
    new_floor = request.form.get("ItemFloor", "").strip()
    new_room = request.form.get("ItemRoom", "").strip()
    new_zone = request.form.get("ItemZone", "").strip()
    
    if not item_ids or not item_ids[0]:
        flash(_("請選擇要移動的物品"), "danger")
        return redirect(url_for("items.manageitem"))
    
    updates = {}
    if new_place:
        updates["ItemStorePlace"] = new_place
    if new_floor:
        updates["ItemFloor"] = new_floor
    if new_room:
        updates["ItemRoom"] = new_room
    if new_zone:
        updates["ItemZone"] = new_zone
    
    if not updates:
        flash(_("請輸入位置資訊"), "danger")
        return redirect(url_for("items.manageitem"))

    success = 0
    for item_id in item_ids:
        item_id = item_id.strip()
        if item_id:
            item_service.update_item_place(item_id, updates)
            success += 1

    flash(_("成功移動 %(n)d 個物品", n=success), "success")
    return redirect(url_for("items.manageitem"))


@bp.route("/batch/delete", methods=["POST"])
@admin_required
def batch_delete():
    """批量刪除物品"""
    user = get_current_user()
    item_ids = request.form.get("item_ids", "").split(",")
    
    if not item_ids or not item_ids[0]:
        flash(_("請選擇要刪除的物品"), "danger")
        return redirect(url_for("items.manageitem"))
    
    success = 0
    failed = 0
    for item_id in item_ids:
        item_id = item_id.strip()
        if item_id:
            ok, _ = item_service.delete_item(item_id)
            if ok:
                success += 1
            else:
                failed += 1
    
    if failed > 0:
        flash(_("刪除完成：成功 %(s)d 個，失敗 %(f)d 個", s=success, f=failed), "warning")
    else:
        flash(_("成功刪除 %(n)d 個物品", n=success), "success")
    
    return redirect(url_for("items.manageitem"))


@bp.route("/search")
@login_required
def search():
    user = get_current_user()
    notification_settings = user_repo.get_notification_settings(session.get("UserID", ""))
    query = request.args.get("q", "")
    place = request.args.get("place", "")
    item_type = request.args.get("type", "")
    floor = request.args.get("floor", "")
    room = request.args.get("room", "")
    zone = request.args.get("zone", "")
    visibility = request.args.get("visibility", "")
    sort = request.args.get("sort", "")
    maintenance = request.args.get("maintenance", "")
    page = request.args.get("page", 1, type=int)

    filters = {
        "q": query,
        "place": place,
        "type": item_type,
        "floor": floor,
        "room": room,
        "zone": zone,
        "visibility": visibility,
        "sort": sort,
    }

    _username = user.get("User", "")
    if maintenance:
        base_result = item_service.list_items(filters, page=1, page_size=5000, current_username=_username)
        item_service.annotate_maintenance_alerts(base_result["items"], notification_settings)
        filtered_items = item_service.filter_items_by_maintenance(base_result["items"], maintenance)
        result = item_service.paginate_items(filtered_items, page=page)
    else:
        result = item_service.list_items(filters, page=page, current_username=_username)

    item_service.annotate_maintenance_alerts(result["items"], notification_settings)
    types = type_service.list_types()
    floors, rooms, zones = location_service.list_choices()
    return render_template(
        "search.html",
        User=user,
        items=result["items"],
        query=query,
        place=place,
        itemtype=types,
        selected_type=item_type,
        floors=floors,
        rooms=rooms,
        zones=zones,
        selected_sort=sort,
        selected_maintenance=maintenance,
        pagination=result,
    )


@bp.route("/scan")
@login_required
def scan():
    user = get_current_user()
    return render_template("scan.html", User=user)


@bp.route("/item/<item_id>")
@login_required
def item_detail(item_id: str):
    """物品詳情頁面"""
    user = get_current_user()
    item = item_service.get_item(item_id)

    if not item:
        flash(_("找不到該物品"), "danger")
        return redirect(url_for("items.home"))

    try:
        custom_field_values = custom_field_service.get_item_custom_values(item_id)
    except Exception:
        custom_field_values = []
    return render_template(
        "itemdetail.html",
        User=user,
        item=item,
        custom_field_values=custom_field_values,
    )


@bp.route("/items/<item_id>/qrcode")
@login_required
def qrcode_image(item_id: str):
    item = item_service.get_item(item_id)
    if not item:
        flash(_("找不到物品"), "danger")
        return redirect(url_for("items.home"))

    img = qrcode.make(f"item:{item_id}")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name=f"{item_id}_qrcode.png")


@bp.route("/items/<item_id>/barcode")
@login_required
def barcode_image(item_id: str):
    item = item_service.get_item(item_id)
    if not item:
        flash(_("找不到物品"), "danger")
        return redirect(url_for("items.home"))

    code = barcode.get("code128", item_id, writer=ImageWriter())
    buf = BytesIO()
    code.write(buf)
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name=f"{item_id}_barcode.png")


@bp.route("/notifications")
@login_required
def notifications():
    """到期通知頁面"""
    user = get_current_user()
    result = item_service.get_expiring_items()
    settings = user_repo.get_notification_settings(session.get("UserID", ""))
    low_stock = item_service.get_low_stock_items()
    replacement = item_service.get_replacement_items(settings)
    overdue_loans = []
    try:
        from app.services.loan_service import get_overdue_loans
        overdue_loans = get_overdue_loans()
    except Exception:
        pass
    return render_template(
        "notifications.html",
        User=user,
        expired_items=result["expired"],
        near_expiry_items=result["near_expiry"],
        expired_count=result["expired_count"],
        near_count=result["near_count"],
        low_stock_items=low_stock["low_stock"],
        low_count=low_stock["low_stock_count"],
        replacement_due=replacement["due"],
        replacement_upcoming=replacement["upcoming"],
        overdue_loans=overdue_loans,
        total_alerts=result["total_alerts"] + low_stock["low_stock_count"] + replacement["total_alerts"] + len(overdue_loans),
    )


@bp.route("/notifications/summary")
@login_required
def notifications_summary():
    return notifications()


@bp.route("/api/notifications/count")
@login_required
@limiter.exempt
def notification_count():
    """API: 取得通知數量（用於導航欄即時更新）"""
    counts = item_service.get_notification_count()
    return jsonify(counts)


@bp.route("/export/<string:export_format>")
@admin_required
def export_items(export_format: str):
    filters = {
        key: value
        for key, value in {
            "ItemType": request.args.get("type"),
            "ItemOwner": request.args.get("owner"),
            "ItemFloor": request.args.get("floor"),
            "ItemRoom": request.args.get("room"),
            "ItemZone": request.args.get("zone"),
            "visibility": request.args.get("visibility"),
        }.items()
        if value
    }
    items = item_service.get_all_items_for_export(filters=filters)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if export_format == "json":
        output = json.dumps(items, ensure_ascii=False, indent=2)
        return Response(
            output,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename=items_export_{timestamp}.json"},
        )
    if export_format == "csv":
        if not items:
            flash(_("沒有可匯出的資料"), "warning")
            return redirect(url_for("items.manageitem"))

        fieldnames = [
            "ItemID", "ItemName", "ItemDesc", "ItemPic", "ItemStorePlace",
            "ItemType", "ItemOwner", "ItemGetDate", "ItemFloor", "ItemRoom",
            "ItemZone", "visibility", "shared_with", "Quantity", "SafetyStock", "ReorderLevel",
            "WarrantyExpiry", "UsageExpiry", "MaintenanceCategory", "MaintenanceIntervalDays",
            "LastMaintenanceDate",
        ]

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            writer.writerow(item)

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=items_export_{timestamp}.csv"},
        )

    flash(_("不支援的匯出格式"), "danger")
    return redirect(url_for("items.manageitem"))


@bp.route("/export/restock")
@admin_required
def export_restock():
    """匯出補貨清單（CSV/JSON）"""
    result = item_service.get_low_stock_items()
    level = request.args.get("level", "all")
    output_format = request.args.get("format", "csv")

    low_stock_items = result.get("low_stock", [])
    if level == "critical":
        items = [i for i in low_stock_items if i.get("stock_status") == "critical"]
    elif level == "warning":
        items = [i for i in low_stock_items if i.get("stock_status") == "warning"]
    else:
        items = low_stock_items

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_format == "json":
        payload = {
            "level": level,
            "count": len(items),
            "items": items,
        }
        return Response(
            json.dumps(payload, ensure_ascii=False, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename=restock_{level}_{timestamp}.json"},
        )

    if output_format == "csv":
        fieldnames = [
            "ItemID", "ItemName", "ItemStorePlace", "ItemFloor", "ItemRoom", "ItemZone",
            "ItemType", "Quantity", "SafetyStock", "ReorderLevel", "stock_status",
        ]
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            writer.writerow(item)

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=restock_{level}_{timestamp}.csv"},
        )

    flash(_("不支援的匯出格式"), "danger")
    return redirect(url_for("items.manageitem"))


@bp.route("/import", methods=["GET", "POST"])
@admin_required
def import_items():
    """匯入物品資料"""
    if request.method == "GET":
        return redirect(url_for("import.index"))
    
    if request.method == "POST":
        if "file" not in request.files:
            flash(_("請選擇要匯入的檔案"), "danger")
            return redirect(url_for("items.import_items"))

        file = request.files["file"]
        if file.filename == "":
            flash(_("請選擇要匯入的檔案"), "danger")
            return redirect(url_for("items.import_items"))
        
        filename = file.filename.lower()
        
        try:
            if filename.endswith(".json"):
                # JSON 格式匯入
                content = file.read().decode("utf-8")
                items_data = json.loads(content)
            elif filename.endswith(".csv"):
                # CSV 格式匯入
                content = file.read().decode("utf-8")
                reader = csv.DictReader(StringIO(content))
                items_data = list(reader)
            else:
                flash(_("不支援的檔案格式，請使用 JSON 或 CSV 格式"), "danger")
                return redirect(url_for("items.import_items"))
            
            success, failed = item_service.import_items(items_data)
            flash(_("匯入完成：成功 %(s)d 筆，失敗 %(f)d 筆", s=success, f=failed), "success" if failed == 0 else "warning")

        except json.JSONDecodeError:
            flash(_("JSON 格式錯誤"), "danger")
        except Exception as e:
            flash(_("匯入失敗：%(err)s", err=str(e)), "danger")
        
        return redirect(url_for("items.manageitem"))
    
    return redirect(url_for("import.index"))


@bp.route("/api/locations/cascade")
@login_required
def get_cascade_locations():
    """API: 取得級聯位置選項"""
    floor = request.args.get("floor", "")
    room = request.args.get("room", "")
    
    locations = location_service.list_locations()
    
    if floor:
        # 根據樓層篩選房間
        rooms = sorted({
            loc.get("room", "") 
            for loc in locations 
            if loc.get("floor") == floor and loc.get("room")
        })
        return jsonify({"rooms": rooms})
    
    if room:
        # 根據房間篩選區域
        zones = sorted({
            loc.get("zone", "") 
            for loc in locations 
            if loc.get("room") == room and loc.get("zone")
        })
        return jsonify({"zones": zones})
    
    return jsonify({"rooms": [], "zones": []})


@bp.route("/api/generate-id")
@login_required  
def generate_item_id():
    """API: 自動產生物品 ID"""
    import uuid
    
    # 產生基於時間的短 ID
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = uuid.uuid4().hex[:6].upper()
    item_id = f"ITEM-{timestamp[-6:]}-{random_part}"
    
    return jsonify({"item_id": item_id})


@bp.route("/api/related-items/<item_id>", methods=["GET", "POST", "DELETE"])
@login_required
def manage_related_items(item_id: str):
    """API: 管理物品關聯"""
    user = get_current_user()
    
    if request.method == "GET":
        # 取得關聯物品
        related = item_service.get_related_items(item_id)
        return jsonify({"success": True, "related_items": related})
    
    if not user.get("admin"):
        return jsonify({"success": False, "message": _("無權限")}), 403
    
    if request.method == "POST":
        # 新增關聯
        data = request.get_json()
        related_id = data.get("related_id", "").strip()
        relation_type = data.get("type", "配件")
        
        if not related_id:
            return jsonify({"success": False, "message": _("請選擇關聯物品")}), 400
        
        ok, msg = item_service.add_related_item(item_id, related_id, relation_type)
        return jsonify({"success": ok, "message": msg})
    
    if request.method == "DELETE":
        # 移除關聯
        data = request.get_json()
        related_id = data.get("related_id", "")
        
        ok, msg = item_service.remove_related_item(item_id, related_id)
        return jsonify({"success": ok, "message": msg})


@bp.route("/api/quick-update-location/<item_id>", methods=["POST"])
@admin_required
def quick_update_location(item_id: str):
    """API: 快速更新物品位置"""
    try:
        data = request.get_json()
        new_location = data.get("location", "").strip()
        
        if not new_location:
            return jsonify({"success": False, "message": _("位置不可為空")}), 400

        item_service.update_item_place(item_id, {"ItemStorePlace": new_location})

        return jsonify({"success": True, "message": _("位置已更新")})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@bp.route("/api/bulk/delete", methods=["POST"])
@admin_required
def bulk_delete():
    """批量刪除物品 API"""
    try:
        data = request.get_json() or {}
        item_ids = data.get("item_ids", [])

        if not item_ids:
            return jsonify({"success": False, "message": _("未選擇任何物品")})

        success_count, failed_ids = item_service.bulk_delete_items(item_ids)

        return jsonify({
            "success": True,
            "success_count": success_count,
            "failed_ids": failed_ids,
            "message": _("成功刪除 %(n)d 個物品", n=success_count)
        })
    except Exception as e:
        return jsonify({"success": False, "message": _("刪除失敗：%(err)s", err=str(e))}), 500


@bp.route("/api/bulk/move", methods=["POST"])
@admin_required
def bulk_move():
    """批量移動物品 API"""
    try:
        data = request.get_json() or {}
        item_ids = data.get("item_ids", [])
        target_location = data.get("location", "").strip()

        if not item_ids:
            return jsonify({"success": False, "message": _("未選擇任何物品")})

        if not target_location:
            return jsonify({"success": False, "message": _("未指定目標位置")})

        success_count, failed_ids = item_service.bulk_move_items(item_ids, target_location)

        return jsonify({
            "success": True,
            "success_count": success_count,
            "failed_ids": failed_ids,
            "message": _("成功移動 %(n)d 個物品至 %(loc)s", n=success_count, loc=target_location)
        })
    except Exception as e:
        return jsonify({"success": False, "message": _("移動失敗：%(err)s", err=str(e))}), 500


@bp.route("/api/bulk/maintenance", methods=["POST"])
@admin_required
def bulk_maintenance():
    """批量更新保養日 API"""
    data = request.get_json() or {}
    item_ids = data.get("item_ids", [])
    maintenance_date = str(data.get("maintenance_date", "")).strip()

    if not item_ids:
        return jsonify({"success": False, "message": _("未選擇任何物品")})
    if not maintenance_date:
        return jsonify({"success": False, "message": _("未指定保養日期")})

    success_count, failed_ids = item_service.bulk_update_last_maintenance(item_ids, maintenance_date)

    if success_count == 0 and failed_ids:
        return jsonify({"success": False, "message": _("保養日期格式錯誤或物品不存在"), "failed_ids": failed_ids}), 400

    return jsonify({
        "success": True,
        "success_count": success_count,
        "failed_ids": failed_ids,
        "message": _("成功更新 %(n)d 個物品的上次保養日", n=success_count)
    })


@bp.route("/api/search")
@login_required
def api_search():
    """API: Full-text search endpoint.

    GET /api/search?q=<query>&page=<n>&page_size=<n>

    Returns JSON with 'items' list and 'total' count.
    """
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    page_size = max(1, min(page_size, 100))  # clamp to [1, 100]

    if not q:
        return jsonify({"items": [], "total": 0, "page": page, "page_size": page_size})

    result = item_service.full_text_search(q, page=page, page_size=page_size)
    return jsonify({
        "items": result["items"],
        "total": result["total"],
        "page": page,
        "page_size": page_size,
    })


@bp.route("/api/search-suggestions")
@login_required
def search_suggestions():
    """API: 搜尋自動完成建議"""
    query = request.args.get("q", "").strip()
    
    if len(query) < 2:
        return jsonify({"suggestions": []})
    
    from app.services import item_service
    from app.repositories import item_repo
    suggestions = item_repo.search_suggestions(query)
    
    return jsonify({"suggestions": suggestions})


@bp.route("/logs")
@admin_required
def activity_logs():
    """操作日誌頁面"""
    user = get_current_user()
    page = request.args.get("page", 1, type=int)
    result = log_service.get_logs_paginated(page=page)
    
    return render_template(
        "logs.html",
        User=user,
        logs=result["logs"],
        pagination=result,
    )


@bp.route("/statistics")
@login_required
def statistics():
    """統計圖表頁面"""
    user = get_current_user()
    notification_settings = user_repo.get_notification_settings(session.get("UserID", ""))
    stats = {
        "total": 0,
        "with_photo": 0,
        "with_location": 0,
        "with_type": 0,
        **(item_service.get_stats() or {}),
    }

    items = item_service.get_all_items_for_export()

    type_counts: Dict[str, int] = {}
    floor_counts: Dict[str, int] = {}
    for item in items:
        item_type = str(item.get("ItemType") or "").strip()
        item_floor = str(item.get("ItemFloor") or "").strip()
        if item_type:
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
        if item_floor:
            floor_counts[item_floor] = floor_counts.get(item_floor, 0) + 1

    types = type_service.list_types()
    type_stats = []
    for t in types:
        type_name = str(t.get("name", "")).strip()
        count = type_counts.get(type_name, 0)
        if type_name and count > 0:
            type_stats.append({"name": type_name, "count": count})
    type_stats.sort(key=lambda item: (-item["count"], item["name"]))

    floors, rooms, zones = location_service.list_choices()
    floor_stats = []
    for f in floors:
        floor_name = str(f).strip()
        count = floor_counts.get(floor_name, 0)
        if floor_name and count > 0:
            floor_stats.append({"name": floor_name, "count": count})
    floor_stats.sort(key=lambda item: (-item["count"], item["name"]))
    
    # 到期統計
    expiry_stats = item_service.get_notification_count()
    replacement = item_service.get_replacement_items(notification_settings)
    maintenance_stats = {
        "due": len(replacement.get("due", [])),
        "upcoming": len(replacement.get("upcoming", [])),
        "total": int(replacement.get("total_alerts", 0) or 0),
    }
    
    return render_template(
        "statistics.html",
        User=user,
        stats=stats,
        type_stats=type_stats,
        floor_stats=floor_stats,
        expiry_stats=expiry_stats,
        maintenance_stats=maintenance_stats,
    )


@bp.route("/api/favorite/<item_id>", methods=["POST"])
@login_required
def toggle_favorite(item_id: str):
    """API: 切換收藏狀態"""
    user = get_current_user()
    user_id = user.get("User", "")
    
    success, is_favorite = item_service.toggle_favorite(item_id, user_id)
    
    if success:
        return jsonify({
            "success": True,
            "is_favorite": is_favorite,
            "message": _("已加入收藏") if is_favorite else _("已取消收藏")
        })
    else:
        return jsonify({
            "success": False,
            "message": _("操作失敗")
        }), 400


@bp.route("/favorites")
@login_required
def favorites():
    """收藏物品頁面"""
    user = get_current_user()
    user_id = user.get("User", "")
    notification_settings = user_repo.get_notification_settings(user_id)
    
    items = item_service.get_favorites(user_id)
    item_service.annotate_maintenance_alerts(items, notification_settings)
    
    return render_template(
        "favorites.html",
        User=user,
        items=items,
    )


@bp.route("/backup")
@admin_required
def backup_page():
    """備份與還原頁面"""
    user = get_current_user()
    stats = item_service.get_stats()
    types = type_service.list_types()
    floors, rooms, zones = location_service.list_choices()
    
    return render_template(
        "backup.html",
        User=user,
        stats=stats,
        type_count=len(types),
        location_count=len(floors) + len(rooms) + len(zones),
    )


@bp.route("/api/backup/full")
@admin_required
def full_backup():
    """API: 完整資料備份"""
    from app import get_db_type
    from app.repositories import item_repo, type_repo, location_repo

    db_type = get_db_type()
    backup_data = {
        "version": "1.2",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "db_type": db_type,
        "items": item_repo.get_all_items_for_backup(),
        "types": type_repo.get_all_types_for_backup(),
        "locations": location_repo.get_all_locations_for_backup(),
    }

    response = Response(
        json.dumps(backup_data, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )

    return response


@bp.route("/api/backup/restore", methods=["POST"])
@admin_required
def restore_backup():
    """API: 還原備份資料"""
    from app.repositories import item_repo, type_repo, location_repo
    
    if "backup_file" not in request.files:
        return jsonify({"success": False, "message": _("請選擇備份檔案")}), 400

    file = request.files["backup_file"]
    if not file.filename:
        return jsonify({"success": False, "message": _("請選擇備份檔案")}), 400
    if not file.filename.endswith(".json"):
        return jsonify({"success": False, "message": _("只支援 JSON 格式")}), 400
    
    try:
        data = json.load(file)
        
        if "items" not in data:
            return jsonify({"success": False, "message": _("無效的備份檔案格式")}), 400
        
        restore_mode = request.form.get("mode", "merge")
        
        stats = {
            "items": item_repo.restore_items(data.get("items", []), restore_mode),
            "types": type_repo.restore_types(data.get("types", []), restore_mode),
            "locations": location_repo.restore_locations(data.get("locations", []), restore_mode),
        }
        
        return jsonify({
            "success": True,
            "message": _("還原完成：%(items)d 物品、%(types)d 類型、%(locs)d 位置",
                         items=stats['items'], types=stats['types'], locs=stats['locations']),
            "stats": stats,
            "mode": restore_mode,
        })

    except json.JSONDecodeError:
        return jsonify({"success": False, "message": _("JSON 解析失敗")}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/backup/config", methods=["GET"])
@admin_required
def get_backup_config():
    """API: 取得排程備份設定"""
    from app.services import backup_service
    cfg = backup_service.get_config()
    return jsonify({"success": True, "config": cfg})


@bp.route("/api/backup/config", methods=["POST"])
@admin_required
def save_backup_config():
    """API: 儲存排程備份設定"""
    from app.services import backup_service
    data = request.get_json() or {}
    try:
        cfg = backup_service.update_config(data)
        return jsonify({"success": True, "config": cfg})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/backup/run-now", methods=["POST"])
@admin_required
def run_backup_now():
    """API: 立即執行備份"""
    from app.services import backup_service
    result = backup_service.run_backup()
    if result["success"]:
        return jsonify(result)
    return jsonify(result), 500


@bp.route("/api/backups/list", methods=["GET"])
@admin_required
def list_backups():
    """API: 列出所有本地備份檔案"""
    from app.services import backup_service
    backups = backup_service.list_backups()
    return jsonify({"success": True, "backups": backups})


@bp.route("/print-labels", methods=["GET", "POST"])
@admin_required
def print_labels():
    """批量列印 QR 標籤頁面"""
    user = get_current_user()
    
    if request.method == "POST":
        # 取得選中的物品 ID
        item_ids = request.form.get("item_ids", "").split(",")
        item_ids = [id.strip() for id in item_ids if id.strip()]
        
        if not item_ids:
            flash(_("請選擇要列印的物品"), "warning")
            return redirect(url_for("items.print_labels"))
        
        # 取得物品資料
        items = []
        for item_id in item_ids:
            item = item_service.get_item(item_id)
            if item:
                # 產生 QR 碼的 base64
                img = qrcode.make(f"item:{item_id}")
                buf = BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                import base64
                qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                item['qr_code'] = f"data:image/png;base64,{qr_base64}"
                items.append(item)
        
        # 取得列印設定 (M20: 支援更多版面參數)
        label_size = request.form.get("label_size", "medium")
        show_name = request.form.get("show_name") == "on"
        show_id = request.form.get("show_id") == "on"
        show_location = request.form.get("show_location") == "on"
        show_type = request.form.get("show_type") == "on"
        show_qr = request.form.get("show_qr", "on") == "on"
        labels_per_row = request.form.get("labels_per_row", "3")
        font_size = request.form.get("font_size", "medium")

        return render_template(
            "print_preview.html",
            User=user,
            items=items,
            label_size=label_size,
            show_name=show_name,
            show_id=show_id,
            show_location=show_location,
            show_type=show_type,
            show_qr=show_qr,
            labels_per_row=labels_per_row,
            font_size=font_size,
        )
    
    # GET: 顯示選擇頁面
    filters = {"q": "", "place": "", "type": "", "floor": "", "room": "", "zone": "", "sort": ""}
    page = request.args.get("page", 1, type=int)
    result = item_service.list_items(filters, page=page, page_size=50, current_username=user.get("User", ""))
    
    return render_template(
        "print_labels.html",
        User=user,
        items=result["items"],
        pagination=result,
    )


@bp.route("/api/quantity-history/<item_id>")
@login_required
def quantity_history(item_id: str):
    """API: 取得物品數量變動記錄"""
    from app.repositories import quantity_log_repo
    logs = quantity_log_repo.get_logs_by_item(item_id)
    return jsonify(logs)


@bp.route("/api/quantity/<item_id>", methods=["POST"])
@admin_required
def adjust_quantity(item_id: str):
    """API: 快速調整物品數量 (+/-)"""
    data = request.get_json() or {}
    delta = data.get("delta", 0)
    reason = data.get("reason")

    try:
        delta = int(delta)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": _("無效的數量")}), 400

    user = get_current_user()
    user_id = user.get("User", "")
    success, new_qty, message = item_service.adjust_quantity(item_id, delta, user=user_id, reason=reason)

    if success:
        item = item_service.get_item(item_id)
        safety_stock = (item.get("SafetyStock") or 0) if item else 0
        reorder_level = (item.get("ReorderLevel") or 0) if item else 0
        
        status = "ok"
        if reorder_level > 0 and new_qty <= reorder_level:
            status = "critical"
        elif safety_stock > 0 and new_qty <= safety_stock:
            status = "low"
        
        return jsonify({
            "success": True,
            "quantity": new_qty,
            "status": status,
            "message": message
        })
    
    return jsonify({"success": False, "message": message}), 400


@bp.route("/reorder")
@login_required
def reorder_list():
    """補貨清單頁面"""
    user = get_current_user()
    result = item_service.get_low_stock_items()
    
    return render_template(
        "reorder.html",
        User=user,
        low_stock_items=result["low_stock"],
        need_reorder_items=result["need_reorder"],
        low_stock_count=result["low_stock_count"],
        reorder_count=result["reorder_count"],
        total_alerts=result["total_alerts"],
    )


@bp.route("/api/bulk/quantity", methods=["POST"])
@admin_required
def bulk_update_quantity():
    """API: 批量更新物品數量"""
    data = request.get_json() or {}
    updates = data.get("updates", [])
    
    if not updates:
        return jsonify({"success": False, "message": _("未提供更新資料")}), 400

    success_count, failed_ids = item_service.bulk_update_quantity(updates)

    return jsonify({
        "success": True,
        "success_count": success_count,
        "failed_ids": failed_ids,
        "message": _("成功更新 %(n)d 個物品", n=success_count)
    })


@bp.route("/api/stock/count")
@login_required
def stock_alert_count():
    """API: 取得庫存警告數量（用於導航欄即時更新）"""
    result = item_service.get_low_stock_items()
    return jsonify({
        "low_stock": result["low_stock_count"],
        "reorder": result["reorder_count"],
        "total": result["total_alerts"],
    })


@bp.route("/api/maintenance/count")
@login_required
def maintenance_alert_count():
    """API: 取得保養提醒數量（用於首頁即時更新）"""
    settings = user_repo.get_notification_settings(session.get("UserID", ""))
    result = item_service.get_replacement_items(settings)
    return jsonify({
        "due": len(result["due"]),
        "upcoming": len(result["upcoming"]),
        "total": result["total_alerts"],
    })


@bp.route("/assets")
@login_required
def assets():
    """資產報表頁面"""
    user = get_current_user()
    report = item_service.get_asset_report()
    return render_template(
        "assets.html",
        User=user,
        report=report,
    )


@bp.route("/assets/print")
@login_required
def assets_print():
    """M14: 可列印的資產報表"""
    from app import get_db_type
    user = get_current_user()
    report = item_service.get_asset_report()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template(
        "assets_print.html",
        User=user,
        report=report,
        now=now,
    )


@bp.route("/stocktake/<int:session_id>/print")
@login_required
def stocktake_print(session_id: int):
    """M14: 可列印的盤點報表"""
    from app.services import stocktake_service
    user = get_current_user()
    sess = stocktake_service.get_session_detail(session_id)
    if not sess:
        flash(_("找不到盤點作業"), "danger")
        return redirect(url_for("stocktake.stocktake_list"))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template(
        "stocktake_print.html",
        User=user,
        session=sess,
        now=now,
    )


@bp.route("/calendar")
@login_required
def calendar_view():
    """M15: 行事曆視圖"""
    user = get_current_user()
    return render_template("calendar.html", User=user)


@bp.route("/api/calendar/events")
@login_required
def calendar_events():
    """M15: 行事曆事件 API（依月份）"""
    month_str = request.args.get("month", "")
    if not month_str:
        from datetime import date as _date
        month_str = _date.today().strftime("%Y-%m")

    try:
        year, month = int(month_str[:4]), int(month_str[5:7])
    except (ValueError, IndexError):
        return jsonify({"error": "invalid month"}), 400

    from app import get_db_type
    from datetime import date as _date, timedelta
    import calendar as _cal

    events: list = []
    db_type = get_db_type()

    if db_type == "postgres":
        # 計算月份範圍
        first_day = _date(year, month, 1)
        last_day = _date(year, month, _cal.monthrange(year, month)[1])

        # WarrantyExpiry 到期 (紅)
        warranty_items = Item.query.filter(
            Item.WarrantyExpiry >= first_day,
            Item.WarrantyExpiry <= last_day,
            Item.is_deleted == False,
        ).all()
        for item in warranty_items:
            events.append({
                "date": item.WarrantyExpiry.strftime("%Y-%m-%d"),
                "type": "warranty",
                "color": "red",
                "label": f"保固到期：{item.ItemName}",
                "item_id": item.ItemID,
            })

        # UsageExpiry 到期 (橙)
        usage_items = Item.query.filter(
            Item.UsageExpiry >= first_day,
            Item.UsageExpiry <= last_day,
            Item.is_deleted == False,
        ).all()
        for item in usage_items:
            events.append({
                "date": item.UsageExpiry.strftime("%Y-%m-%d"),
                "type": "usage",
                "color": "orange",
                "label": f"使用期限：{item.ItemName}",
                "item_id": item.ItemID,
            })

        # 保養到期 (藍) - LastMaintenanceDate + MaintenanceIntervalDays 落在此月
        maintenance_items = Item.query.filter(
            Item.LastMaintenanceDate.isnot(None),
            Item.MaintenanceIntervalDays.isnot(None),
            Item.is_deleted == False,
        ).all()
        for item in maintenance_items:
            if item.LastMaintenanceDate and item.MaintenanceIntervalDays:
                due = item.LastMaintenanceDate + timedelta(days=int(item.MaintenanceIntervalDays))
                if first_day <= due <= last_day:
                    events.append({
                        "date": due.strftime("%Y-%m-%d"),
                        "type": "maintenance",
                        "color": "blue",
                        "label": f"保養到期：{item.ItemName}",
                        "item_id": item.ItemID,
                    })

        # 借出歸還 (綠) — 尚未還回 (status != returned)
        from app.models.item_loan import ItemLoan
        loans = ItemLoan.query.filter(
            ItemLoan.expected_return >= first_day,
            ItemLoan.expected_return <= last_day,
            ItemLoan.status != "returned",
        ).all()
        for loan in loans:
            events.append({
                "date": loan.expected_return.strftime("%Y-%m-%d"),
                "type": "loan_return",
                "color": "green",
                "label": f"借出歸還：{loan.item_name or loan.item_id}",
                "item_id": loan.item_id,
            })

    return jsonify({"month": month_str, "events": events})


@bp.route("/api/templates")
@login_required
def api_templates():
    """M19: 列出所有物品模板"""
    from app.models.item_template import ItemTemplate
    templates = ItemTemplate.query.order_by(ItemTemplate.name).all()
    return jsonify([t.to_dict() for t in templates])


@bp.route("/api/templates/<int:template_id>")
@login_required
def api_template_detail(template_id: int):
    """M19: 取得單一物品模板"""
    from app.models.item_template import ItemTemplate
    t = ItemTemplate.query.get_or_404(template_id)
    return jsonify(t.to_dict())


@bp.route("/api/items/<item_id>/purchase-links")
@login_required
def purchase_links(item_id: str):
    """API: 取得物品的購買連結（Feature 21）。"""
    item = item_service.get_item(item_id)
    if not item:
        return jsonify({"error": "找不到物品"}), 404
    links = item_service.generate_purchase_links(item.get("ItemName", item_id))
    return jsonify({
        "item_id": item_id,
        "item_name": item.get("ItemName", ""),
        "purchase_url": item.get("purchase_url", ""),
        "preferred_store": item.get("preferred_store", ""),
        "links": links,
    })


@bp.route("/trash")
@admin_required
def trash():
    """M6: 回收站頁面"""
    user = get_current_user()
    items = item_service.list_trash()
    return render_template("trash.html", User=user, items=items)


@bp.route("/api/items/<item_id>/restore", methods=["POST"])
@admin_required
def restore_item(item_id: str):
    """M6: 從回收站還原物品"""
    ok, msg = item_service.restore_item(item_id)
    return jsonify({"success": ok, "message": msg})


@bp.route("/api/trash/empty", methods=["POST"])
@admin_required
def empty_trash():
    """M6: 清空回收站（永久刪除所有軟刪除物品）"""
    count = item_service.empty_trash()
    return jsonify({"success": True, "message": f"已永久刪除 {count} 個物品", "count": count})


@bp.route("/api/items/<item_id>/permanent-delete", methods=["POST"])
@admin_required
def permanent_delete_item(item_id: str):
    """M6: 永久刪除單一物品（需先在回收站中）"""
    from app.repositories import item_repo as _item_repo
    from app.utils import storage as _storage
    item = _item_repo.find_item_by_id(item_id)
    if not item:
        return jsonify({"success": False, "message": "找不到物品"}), 404
    if item.get("ItemPic"):
        _storage.delete_file(item["ItemPic"])
    if item.get("ItemThumb"):
        _storage.delete_file(item["ItemThumb"])
    ok = _item_repo.permanent_delete_item(item_id)
    return jsonify({"success": ok, "message": "已永久刪除" if ok else "刪除失敗"})


@bp.route("/export-zip")
@admin_required
def export_zip():
    """M7: 匯出物品資料為含照片的 ZIP 壓縮檔"""
    from datetime import datetime as _dt
    filters = {
        key: value
        for key, value in {
            "ItemType": request.args.get("type"),
            "ItemOwner": request.args.get("owner"),
            "ItemFloor": request.args.get("floor"),
            "ItemRoom": request.args.get("room"),
            "ItemZone": request.args.get("zone"),
        }.items()
        if value
    }
    items = item_service.get_all_items_for_export(filters=filters)
    timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
    buf = item_service.export_items_with_photos(items)
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"items_with_photos_{timestamp}.zip",
    )


@bp.route("/api/items/reorder", methods=["POST"])
@admin_required
def reorder_items():
    """M10: 根據拖曳後的順序更新 sort_order"""
    data = request.get_json() or {}
    item_ids = data.get("item_ids", [])
    if not isinstance(item_ids, list):
        return jsonify({"success": False, "message": "item_ids 必須為陣列"}), 400
    ok, msg = item_service.reorder_items(item_ids)
    return jsonify({"success": ok, "message": msg})


@bp.route("/api/items/<item_id>/versions")
@login_required
def item_versions(item_id: str):
    """M11: 取得物品版本歷史"""
    versions = item_service.get_item_versions(item_id)
    return jsonify({"success": True, "versions": versions})


@bp.route("/move-history")
@login_required
def move_history():
    """移動歷史頁面"""
    user = get_current_user()
    page = request.args.get("page", 1, type=int)
    item_filter = request.args.get("item", "").strip()
    location_filter = request.args.get("location", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    result = item_service.get_all_move_history(
        page=page,
        page_size=50,
        item_filter=item_filter,
        location_filter=location_filter,
        date_from=date_from,
        date_to=date_to,
    )

    return render_template(
        "move_history.html",
        User=user,
        records=result["items"],
        pagination=result,
        item_filter=item_filter,
        location_filter=location_filter,
        date_from=date_from,
        date_to=date_to,
    )


# M12: AI Image Recognition
@bp.route("/api/items/analyze-image", methods=["POST"])
@login_required
def analyze_image():
    """接收上傳圖片，返回 AI 建議欄位（目前使用檔名啟發式方法）"""
    from app.services.ai_service import analyze_image as _analyze
    from app.utils.storage import save_upload

    photo = request.files.get("photo")
    if not photo or not photo.filename:
        return jsonify({"success": False, "message": "請上傳圖片"}), 400

    filename = save_upload(photo)
    if not filename:
        return jsonify({"success": False, "message": "圖片儲存失敗"}), 500

    image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    result = _analyze(image_path)
    return jsonify({"success": True, **result})


# M13: OCR Receipt Scanning
@bp.route("/api/items/scan-receipt", methods=["POST"])
@login_required
def scan_receipt():
    """接收收據圖片，嘗試 OCR 提取採購資訊"""
    from app.services.ai_service import scan_receipt as _scan
    from app.utils.storage import save_upload

    photo = request.files.get("photo")
    if not photo or not photo.filename:
        return jsonify({"success": False, "message": "請上傳收據圖片"}), 400

    filename = save_upload(photo)
    if not filename:
        return jsonify({"success": False, "message": "圖片儲存失敗"}), 500

    image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    result = _scan(image_path)
    return jsonify({"success": True, **result})
