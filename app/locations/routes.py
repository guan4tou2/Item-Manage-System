import os

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app

from app.services import location_service
from app.utils.auth import admin_required, login_required, get_current_user

bp = Blueprint("locations", __name__)


@bp.route("/locations", methods=["GET", "POST"])
@admin_required
def manage_locations():
    user = get_current_user()
    locations = location_service.list_locations()
    floors, rooms, zones = location_service.list_choices()

    if request.method == "POST":
        action = request.form.get("action", "create")
        if action == "delete":
            loc_id = request.form.get("loc_id", "")
            location_service.delete_location(loc_id)
            flash("位置選項已刪除", "success")
        elif action == "update":
            loc_id = request.form.get("loc_id", "")
            doc = {
                "floor": request.form.get("floor", "").strip(),
                "room": request.form.get("room", "").strip(),
                "zone": request.form.get("zone", "").strip(),
            }
            if not any(doc.values()):
                flash("請至少保留一個欄位，避免空白位置選項", "danger")
                return redirect(url_for("locations.manage_locations"))
            location_service.update_location(loc_id, doc)
            flash("位置選項已更新", "success")
        else:
            doc = {
                "floor": request.form.get("floor", "").strip(),
                "room": request.form.get("room", "").strip(),
                "zone": request.form.get("zone", "").strip(),
            }
            ok, msg = location_service.create_location(doc)
            flash(msg, "success" if ok else "danger")
        return redirect(url_for("locations.manage_locations"))

    return render_template(
        "locations.html",
        User=user,
        locations=locations,
        floors=floors,
        rooms=rooms,
        zones=zones,
    )


@bp.route("/locations/update-order", methods=["POST"])
@admin_required
def update_order():
    """API: 更新位置排序"""
    try:
        data = request.get_json()
        order_list = data.get("order", [])

        if order_list:
            location_service.update_order(order_list)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ------------------------------------------------------------------
# Feature 18: Location Map Visualization
# ------------------------------------------------------------------

@bp.route("/locations/map")
@login_required
def location_map():
    """互動式平面圖頁面"""
    user = get_current_user()
    floors, _rooms, _zones = location_service.list_choices()
    selected_floor = request.args.get("floor", floors[0] if floors else "")
    floor_plan_image = location_service.get_floor_plan_image(selected_floor)
    return render_template(
        "location_map.html",
        User=user,
        floors=floors,
        selected_floor=selected_floor,
        floor_plan_image=floor_plan_image,
    )


@bp.route("/api/locations/floor-plan", methods=["POST"])
@admin_required
def upload_floor_plan():
    """API: 上傳平面圖圖片"""
    from app.utils import storage

    floor = request.form.get("floor", "").strip()
    if not floor:
        return jsonify({"success": False, "error": "缺少樓層名稱"}), 400

    file = request.files.get("floor_plan")
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "未選擇檔案"}), 400

    filename = storage.save_upload(file)
    if not filename:
        return jsonify({"success": False, "error": "不允許的檔案格式"}), 400

    ok = location_service.set_floor_plan_image(floor, filename)
    if not ok:
        storage.delete_file(filename)
        return jsonify({"success": False, "error": "找不到該樓層"}), 404

    image_url = url_for("static", filename=f"uploads/{filename}")
    return jsonify({"success": True, "filename": filename, "image_url": image_url})


@bp.route("/api/items/<item_id>/position", methods=["POST"])
@admin_required
def save_item_position(item_id: str):
    """API: 儲存物品在平面圖上的座標"""
    data = request.get_json(silent=True) or {}
    try:
        x = int(data.get("x", 0))
        y = int(data.get("y", 0))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "無效的座標值"}), 400

    ok = location_service.update_item_position(item_id, x, y)
    if not ok:
        return jsonify({"success": False, "error": "找不到物品"}), 404

    return jsonify({"success": True, "item_id": item_id, "x": x, "y": y})


@bp.route("/api/locations/map-data")
@login_required
def map_data():
    """API: 回傳指定樓層的所有已定位物品"""
    floor = request.args.get("floor", "")
    items = location_service.get_items_with_positions(floor)
    floor_plan_image = location_service.get_floor_plan_image(floor)
    image_url = (
        url_for("static", filename=f"uploads/{floor_plan_image}")
        if floor_plan_image
        else None
    )
    return jsonify({
        "success": True,
        "floor": floor,
        "floor_plan_image": image_url,
        "items": items,
    })
