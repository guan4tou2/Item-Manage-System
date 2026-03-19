"""倉庫管理藍圖路由"""
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash

from app.services import warehouse_service
from app.utils.auth import login_required, get_current_user
from app import db, get_db_type

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


@bp.route("/warehouses/transfers")
@login_required
def transfer_list():
    """調撥記錄列表頁"""
    user = get_current_user()
    username = user.get("User", "")
    transfers = []
    warehouses_map = {}
    if get_db_type() == "postgres":
        from app.models.transfer import WarehouseTransfer
        from app.models.warehouse import Warehouse
        rows = WarehouseTransfer.query.order_by(WarehouseTransfer.created_at.desc()).all()
        transfers = [r.to_dict() for r in rows]
        wh_rows = Warehouse.query.all()
        warehouses_map = {w.id: w.name for w in wh_rows}
    return render_template(
        "transfers.html",
        User=user,
        transfers=transfers,
        warehouses_map=warehouses_map,
    )


@bp.route("/api/warehouses/transfer", methods=["POST"])
@login_required
def create_transfer():
    """建立倉庫調撥申請"""
    user = get_current_user()
    username = user.get("User", "")
    data = request.get_json(silent=True) or {}
    item_id = data.get("item_id", "").strip()
    from_id = data.get("from_id")
    to_id = data.get("to_id")
    qty = int(data.get("qty", 1))
    notes = data.get("notes", "")

    if not item_id or not from_id or not to_id:
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400
    if from_id == to_id:
        return jsonify({"success": False, "message": "來源與目標倉庫不可相同"}), 400

    if get_db_type() == "postgres":
        from app.models.transfer import WarehouseTransfer
        from app.repositories import item_repo as _item_repo
        item = _item_repo.find_item_by_id(item_id)
        item_name = item.get("ItemName", item_id) if item else item_id
        transfer = WarehouseTransfer(
            item_id=item_id,
            item_name=item_name,
            from_warehouse_id=int(from_id),
            to_warehouse_id=int(to_id),
            quantity=qty,
            status="pending",
            requested_by=username,
            notes=notes or None,
        )
        db.session.add(transfer)
        db.session.commit()
        return jsonify({"success": True, "id": transfer.id})
    return jsonify({"success": False, "message": "MongoDB 尚未支援此功能"}), 501


@bp.route("/api/warehouses/transfer/<int:transfer_id>/complete", methods=["POST"])
@login_required
def complete_transfer(transfer_id: int):
    """完成調撥（更新物品所在倉庫）"""
    if get_db_type() == "postgres":
        from app.models.transfer import WarehouseTransfer
        transfer = db.session.get(WarehouseTransfer, transfer_id)
        if not transfer:
            return jsonify({"success": False, "message": "調撥記錄不存在"}), 404
        if transfer.status != "pending":
            return jsonify({"success": False, "message": "此調撥已處理"}), 400
        transfer.status = "completed"
        transfer.completed_at = datetime.utcnow()
        # Update item's warehouse_id
        from app.repositories import item_repo as _item_repo
        _item_repo.update_item_field(transfer.item_id, "warehouse_id", transfer.to_warehouse_id)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "MongoDB 尚未支援此功能"}), 501


@bp.route("/api/warehouses/transfer/<int:transfer_id>/cancel", methods=["POST"])
@login_required
def cancel_transfer(transfer_id: int):
    """取消調撥"""
    if get_db_type() == "postgres":
        from app.models.transfer import WarehouseTransfer
        transfer = db.session.get(WarehouseTransfer, transfer_id)
        if not transfer:
            return jsonify({"success": False, "message": "調撥記錄不存在"}), 404
        if transfer.status != "pending":
            return jsonify({"success": False, "message": "此調撥已處理"}), 400
        transfer.status = "cancelled"
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "MongoDB 尚未支援此功能"}), 501
