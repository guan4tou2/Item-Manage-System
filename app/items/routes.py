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
)

from typing import Any, Dict, List

from app.services import (
    item_service,
    type_service,
    location_service,
)
from app.services import log_service
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
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


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
        "sort": request.args.get("sort", ""),
    }
    page = request.args.get("page", 1, type=int)
    result = item_service.list_items(filters, page=page)
    user = get_current_user()
    types = type_service.list_types()
    floors, rooms, zones = location_service.list_choices()
    stats = item_service.get_stats()
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
    )


@bp.route("/additem", methods=["GET", "POST"])
@admin_required
def additem():
    user = get_current_user()
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
@admin_required
def manageitem():
    user = get_current_user()

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
    page = request.args.get("page", 1, type=int)
    result = item_service.list_items(filters, page=page)
    floors, rooms, zones = location_service.list_choices()
    return render_template(
        "manageitem.html",
        User=user,
        items=result["items"],
        floors=floors,
        rooms=rooms,
        zones=zones,
        pagination=result,
    )


@bp.route("/edititem/<item_id>", methods=["GET", "POST"])
@admin_required
def edititem(item_id: str):
    user = get_current_user()
    item = item_service.get_item(item_id)
    
    if not item:
        flash("找不到該物品", "danger")
        return redirect(url_for("items.home"))
    
    types = type_service.list_types()
    floors, rooms, zones = location_service.list_choices()
    
    if request.method == "POST":
        form = dict(request.form)
        ok, msg = item_service.update_item(item_id, form, request.files.get("ItemPic"))
        if ok:
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
        flash("請選擇要移動的物品", "danger")
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
        flash("請輸入位置資訊", "danger")
        return redirect(url_for("items.manageitem"))
    
    success = 0
    for item_id in item_ids:
        item_id = item_id.strip()
        if item_id:
            item_service.update_item_place(item_id, updates)
            success += 1
    
    flash(f"成功移動 {success} 個物品", "success")
    return redirect(url_for("items.manageitem"))


@bp.route("/batch/delete", methods=["POST"])
@admin_required
def batch_delete():
    """批量刪除物品"""
    user = get_current_user()
    item_ids = request.form.get("item_ids", "").split(",")
    
    if not item_ids or not item_ids[0]:
        flash("請選擇要刪除的物品", "danger")
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
        flash(f"刪除完成：成功 {success} 個，失敗 {failed} 個", "warning")
    else:
        flash(f"成功刪除 {success} 個物品", "success")
    
    return redirect(url_for("items.manageitem"))


@bp.route("/search")
@login_required
def search():
    user = get_current_user()
    query = request.args.get("q", "")
    place = request.args.get("place", "")
    item_type = request.args.get("type", "")
    floor = request.args.get("floor", "")
    room = request.args.get("room", "")
    zone = request.args.get("zone", "")
    sort = request.args.get("sort", "")
    page = request.args.get("page", 1, type=int)
    
    result = item_service.list_items(
        {
            "q": query,
            "place": place,
            "type": item_type,
            "floor": floor,
            "room": room,
            "zone": zone,
            "sort": sort,
        },
        page=page,
    )
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
        flash("找不到該物品", "danger")
        return redirect(url_for("items.home"))
    
    return render_template("itemdetail.html", User=user, item=item)


@bp.route("/items/<item_id>/qrcode")
@login_required
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
@login_required
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


@bp.route("/notifications")
@login_required
def notifications():
    """到期通知頁面"""
    user = get_current_user()
    result = item_service.get_expiring_items()
    return render_template(
        "notifications.html",
        User=user,
        expired_items=result["expired"],
        near_expiry_items=result["near_expiry"],
        expired_count=result["expired_count"],
        near_count=result["near_count"],
        total_alerts=result["total_alerts"],
    )


@bp.route("/api/notifications/count")
@login_required
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
            flash("沒有可匯出的資料", "warning")
            return redirect(url_for("items.manageitem"))

        fieldnames = [
            "ItemID", "ItemName", "ItemDesc", "ItemPic", "ItemStorePlace",
            "ItemType", "ItemOwner", "ItemGetDate", "ItemFloor", "ItemRoom",
            "ItemZone", "Quantity", "SafetyStock", "ReorderLevel", "WarrantyExpiry", "UsageExpiry",
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

    flash("不支援的匯出格式", "danger")
    return redirect(url_for("items.manageitem"))


@bp.route("/import", methods=["GET", "POST"])
@admin_required
def import_items():
    """匯入物品資料"""
    user = get_current_user()
    
    if request.method == "POST":
        if "file" not in request.files:
            flash("請選擇要匯入的檔案", "danger")
            return redirect(url_for("items.import_items"))
        
        file = request.files["file"]
        if file.filename == "":
            flash("請選擇要匯入的檔案", "danger")
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
                flash("不支援的檔案格式，請使用 JSON 或 CSV 格式", "danger")
                return redirect(url_for("items.import_items"))
            
            success, failed = item_service.import_items(items_data)
            flash(f"匯入完成：成功 {success} 筆，失敗 {failed} 筆", "success" if failed == 0 else "warning")
            
        except json.JSONDecodeError:
            flash("JSON 格式錯誤", "danger")
        except Exception as e:
            flash(f"匯入失敗：{str(e)}", "danger")
        
        return redirect(url_for("items.manageitem"))
    
    return render_template("import.html", User=user)


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
        return jsonify({"success": False, "message": "無權限"}), 403
    
    if request.method == "POST":
        # 新增關聯
        data = request.get_json()
        related_id = data.get("related_id", "").strip()
        relation_type = data.get("type", "配件")
        
        if not related_id:
            return jsonify({"success": False, "message": "請選擇關聯物品"}), 400
        
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
            return jsonify({"success": False, "message": "位置不可為空"}), 400
        
        item_service.update_item_place(item_id, {"ItemStorePlace": new_location})
        
        return jsonify({"success": True, "message": "位置已更新"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@bp.route("/api/bulk/delete", methods=["POST"])
@admin_required
def bulk_delete():
    """批量刪除物品 API"""
    data = request.get_json() or {}
    item_ids = data.get("item_ids", [])
    
    if not item_ids:
        return jsonify({"success": False, "message": "未選擇任何物品"})
    
    success_count, failed_ids = item_service.bulk_delete_items(item_ids)
    
    return jsonify({
        "success": True,
        "success_count": success_count,
        "failed_ids": failed_ids,
        "message": f"成功刪除 {success_count} 個物品"
    })


@bp.route("/api/bulk/move", methods=["POST"])
@admin_required
def bulk_move():
    """批量移動物品 API"""
    data = request.get_json() or {}
    item_ids = data.get("item_ids", [])
    target_location = data.get("location", "").strip()
    
    if not item_ids:
        return jsonify({"success": False, "message": "未選擇任何物品"})
    
    if not target_location:
         return jsonify({"success": False, "message": "未指定目標位置"})
    
    success_count, failed_ids = item_service.bulk_move_items(item_ids, target_location)
    
    return jsonify({
        "success": True,
        "success_count": success_count,
        "failed_ids": failed_ids,
        "message": f"成功移動 {success_count} 個物品至 {target_location}"
    })


@bp.route("/api/search-suggestions")
@login_required
def search_suggestions():
    """API: 搜尋自動完成建議"""
    query = request.args.get("q", "").strip()
    
    if len(query) < 2:
        return jsonify({"suggestions": []})
    
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
    stats = item_service.get_stats()
    
    # 取得各類型的物品數量
    types = type_service.list_types()
    type_stats = []
    for t in types:
        count = item_service.count_by_type(t.get("name", ""))
        if count > 0:
            type_stats.append({"name": t.get("name"), "count": count})
    
    # 取得各位置的物品數量
    floors, rooms, zones = location_service.list_choices()
    floor_stats = []
    for f in floors:
        count = item_service.count_by_floor(f)
        if count > 0:
            floor_stats.append({"name": f, "count": count})
    
    # 到期統計
    expiry_stats = item_service.get_notification_count()
    
    return render_template(
        "statistics.html",
        User=user,
        stats=stats,
        type_stats=type_stats,
        floor_stats=floor_stats,
        expiry_stats=expiry_stats,
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
            "message": "已加入收藏" if is_favorite else "已取消收藏"
        })
    else:
        return jsonify({
            "success": False,
            "message": "操作失敗"
        }), 400


@bp.route("/favorites")
@login_required
def favorites():
    """收藏物品頁面"""
    user = get_current_user()
    user_id = user.get("User", "")
    
    items = item_service.get_favorites(user_id)
    
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
        "version": "1.1",
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
        return jsonify({"success": False, "message": "請選擇備份檔案"}), 400
    
    file = request.files["backup_file"]
    if not file.filename.endswith(".json"):
        return jsonify({"success": False, "message": "只支援 JSON 格式"}), 400
    
    try:
        data = json.load(file)
        
        if "items" not in data:
            return jsonify({"success": False, "message": "無效的備份檔案格式"}), 400
        
        restore_mode = request.form.get("mode", "merge")
        
        stats = {
            "items": item_repo.restore_items(data.get("items", []), restore_mode),
            "types": type_repo.restore_types(data.get("types", []), restore_mode),
            "locations": location_repo.restore_locations(data.get("locations", []), restore_mode),
        }
        
        return jsonify({
            "success": True,
            "message": f"還原完成：{stats['items']} 物品、{stats['types']} 類型、{stats['locations']} 位置",
            "stats": stats
        })
        
    except json.JSONDecodeError:
        return jsonify({"success": False, "message": "JSON 解析失敗"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


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
            flash("請選擇要列印的物品", "warning")
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
        
        # 取得列印設定
        label_size = request.form.get("label_size", "medium")
        show_name = request.form.get("show_name") == "on"
        show_id = request.form.get("show_id") == "on"
        show_location = request.form.get("show_location") == "on"
        
        return render_template(
            "print_preview.html",
            User=user,
            items=items,
            label_size=label_size,
            show_name=show_name,
            show_id=show_id,
            show_location=show_location,
        )
    
    # GET: 顯示選擇頁面
    filters = {"q": "", "place": "", "type": "", "floor": "", "room": "", "zone": "", "sort": ""}
    page = request.args.get("page", 1, type=int)
    result = item_service.list_items(filters, page=page, page_size=50)
    
    return render_template(
        "print_labels.html",
        User=user,
        items=result["items"],
        pagination=result,
    )


@bp.route("/api/quantity/<item_id>", methods=["POST"])
@admin_required
def adjust_quantity(item_id: str):
    """API: 快速調整物品數量 (+/-)"""
    data = request.get_json() or {}
    delta = data.get("delta", 0)
    
    try:
        delta = int(delta)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "無效的數量"}), 400
    
    success, new_qty, message = item_service.adjust_quantity(item_id, delta)
    
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
        return jsonify({"success": False, "message": "未提供更新資料"}), 400
    
    success_count, failed_ids = item_service.bulk_update_quantity(updates)
    
    return jsonify({
        "success": True,
        "success_count": success_count,
        "failed_ids": failed_ids,
        "message": f"成功更新 {success_count} 個物品"
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

