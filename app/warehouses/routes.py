"""倉庫管理藍圖路由"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash

from app.services import warehouse_service
from app.utils.auth import login_required, get_current_user

bp = Blueprint("warehouses", __name__)


@bp.route("/warehouses")
@login_required
def warehouse_list():
    """列出使用者的倉庫"""
    user = get_current_user()
    username = user.get("User", "")
    warehouses = warehouse_service.get_user_warehouses(username)
    active = warehouse_service.get_active_warehouse(username)
    return render_template(
        "warehouses.html",
        User=user,
        warehouses=warehouses,
        active_warehouse=active,
    )


@bp.route("/warehouses/create", methods=["POST"])
@login_required
def create_warehouse():
    """建立新倉庫"""
    user = get_current_user()
    username = user.get("User", "")
    name = request.form.get("name", "").strip()
    address = request.form.get("address", "").strip()

    ok, msg, warehouse_id = warehouse_service.create_warehouse(name, username, address)
    if ok:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("warehouses.warehouse_list"))


@bp.route("/api/warehouses/switch/<int:id>", methods=["POST"])
@login_required
def switch_warehouse(id: int):
    """切換作用中倉庫（更新 session）"""
    user = get_current_user()
    username = user.get("User", "")

    ok, msg = warehouse_service.switch_warehouse(username, id)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "message": msg}), 400


@bp.route("/warehouses/<int:id>/delete", methods=["POST"])
@login_required
def delete_warehouse(id: int):
    """刪除倉庫"""
    user = get_current_user()
    username = user.get("User", "")

    ok, msg = warehouse_service.delete_warehouse(username, id)
    if ok:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("warehouses.warehouse_list"))


@bp.route("/api/warehouses/list")
@login_required
def api_warehouse_list():
    """API: 取得使用者的倉庫列表（含作用中狀態），供導覽列選擇器使用"""
    user = get_current_user()
    username = user.get("User", "")
    warehouses = warehouse_service.get_user_warehouses(username)
    active = warehouse_service.get_active_warehouse(username)
    active_id = active["id"] if active else None
    active_name = active["name"] if active else ""

    result = []
    for w in warehouses:
        result.append({
            "id": w["id"],
            "name": w["name"],
            "address": w.get("address", ""),
            "is_default": w.get("is_default", False),
            "is_active": w["id"] == active_id,
        })

    return jsonify({
        "warehouses": result,
        "active_id": active_id,
        "active_name": active_name,
    })
