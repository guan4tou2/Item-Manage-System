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

from app.services import (
    item_service,
    type_service,
    location_service,
)
from app.services import log_service
from app.utils.auth import login_required, admin_required, get_current_user
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


@bp.route("/export/<format>")
@admin_required
def export_items(format: str):
    """匯出物品資料"""
    items = item_service.get_all_items_for_export()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == "json":
        # JSON 格式匯出
        output = json.dumps(items, ensure_ascii=False, indent=2)
        return Response(
            output,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename=items_export_{timestamp}.json"}
        )
    elif format == "csv":
        # CSV 格式匯出
        if not items:
            flash("沒有可匯出的資料", "warning")
            return redirect(url_for("items.manageitem"))
        
        # 取得所有欄位
        fieldnames = [
            "ItemID", "ItemName", "ItemDesc", "ItemPic", "ItemStorePlace",
            "ItemType", "ItemOwner", "ItemGetDate", "ItemFloor", "ItemRoom",
            "ItemZone", "WarrantyExpiry", "UsageExpiry"
        ]
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        
        for item in items:
            writer.writerow(item)
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=items_export_{timestamp}.csv"}
        )
    else:
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


@bp.route("/api/search-suggestions")
@login_required
def search_suggestions():
    """API: 搜尋自動完成建議"""
    query = request.args.get("q", "").strip()
    
    if len(query) < 2:
        return jsonify({"suggestions": []})
    
    # 搜尋物品名稱和 ID
    from app import mongo
    
    suggestions = []
    
    # 搜尋名稱
    name_results = mongo.db.item.find(
        {"ItemName": {"$regex": query, "$options": "i"}},
        {"ItemName": 1, "ItemID": 1, "ItemType": 1, "_id": 0}
    ).limit(5)
    
    for item in name_results:
        suggestions.append({
            "text": item.get("ItemName", ""),
            "id": item.get("ItemID", ""),
            "type": item.get("ItemType", ""),
            "category": "name"
        })
    
    # 搜尋 ID
    id_results = mongo.db.item.find(
        {"ItemID": {"$regex": query, "$options": "i"}},
        {"ItemName": 1, "ItemID": 1, "ItemType": 1, "_id": 0}
    ).limit(3)
    
    for item in id_results:
        # 避免重複
        if not any(s["id"] == item.get("ItemID") for s in suggestions):
            suggestions.append({
                "text": item.get("ItemID", ""),
                "id": item.get("ItemID", ""),
                "name": item.get("ItemName", ""),
                "type": item.get("ItemType", ""),
                "category": "id"
            })
    
    return jsonify({"suggestions": suggestions[:8]})


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
    from app import mongo
    
    backup_data = {
        "version": "1.0",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": list(mongo.db.item.find({}, {"_id": 0})),
        "types": list(mongo.db.type.find({}, {"_id": 0})),
        "locations": list(mongo.db.locations.find({}, {"_id": 0})),
    }
    
    # 建立 JSON 回應
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
    from app import mongo
    
    if "backup_file" not in request.files:
        return jsonify({"success": False, "message": "請選擇備份檔案"}), 400
    
    file = request.files["backup_file"]
    if not file.filename.endswith(".json"):
        return jsonify({"success": False, "message": "只支援 JSON 格式"}), 400
    
    try:
        data = json.load(file)
        
        # 驗證資料格式
        if "items" not in data:
            return jsonify({"success": False, "message": "無效的備份檔案格式"}), 400
        
        restore_mode = request.form.get("mode", "merge")  # merge 或 replace
        
        stats = {"items": 0, "types": 0, "locations": 0}
        
        # 還原物品
        for item in data.get("items", []):
            if restore_mode == "replace":
                mongo.db.item.delete_one({"ItemID": item.get("ItemID")})
            
            if not mongo.db.item.find_one({"ItemID": item.get("ItemID")}):
                mongo.db.item.insert_one(item)
                stats["items"] += 1
            elif restore_mode == "merge":
                mongo.db.item.update_one(
                    {"ItemID": item.get("ItemID")},
                    {"$set": item}
                )
                stats["items"] += 1
        
        # 還原類型
        for t in data.get("types", []):
            if not mongo.db.type.find_one({"name": t.get("name")}):
                mongo.db.type.insert_one(t)
                stats["types"] += 1
        
        # 還原位置
        for loc in data.get("locations", []):
            existing = mongo.db.locations.find_one({
                "floor": loc.get("floor"),
                "room": loc.get("room"),
                "zone": loc.get("zone")
            })
            if not existing:
                mongo.db.locations.insert_one(loc)
                stats["locations"] += 1
        
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

