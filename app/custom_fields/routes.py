"""自訂欄位管理路由"""
from flask import Blueprint, render_template, request, jsonify, session
from flask_babel import gettext as _

from app.utils.auth import login_required, admin_required, get_current_user
from app.services import custom_field_service

bp = Blueprint("custom_fields", __name__)


@bp.route("/admin/custom-fields")
@admin_required
def manage_custom_fields():
    """自訂欄位管理頁面"""
    user = get_current_user()
    fields = custom_field_service.list_fields()
    return render_template(
        "admin_custom_fields.html",
        User=user,
        fields=fields,
    )


@bp.route("/api/custom-fields", methods=["POST"])
@admin_required
def create_custom_field():
    """新增自訂欄位 (JSON)"""
    data = request.get_json() or {}
    user = get_current_user()
    created_by = user.get("User", "")

    name = data.get("name", "").strip()
    field_type = data.get("field_type", "text")
    options = data.get("options", "")
    required = bool(data.get("required", False))
    sort_order = data.get("sort_order", 0)

    ok, msg, field_id = custom_field_service.create_field(
        name=name,
        field_type=field_type,
        options=options,
        required=required,
        sort_order=sort_order,
        created_by=created_by,
    )

    if ok:
        return jsonify({"success": True, "message": msg, "field_id": field_id})
    return jsonify({"success": False, "message": msg}), 400


@bp.route("/api/custom-fields/<int:field_id>", methods=["POST"])
@admin_required
def update_custom_field(field_id: int):
    """更新自訂欄位"""
    data = request.get_json() or {}
    ok, msg = custom_field_service.update_field(field_id, data)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "message": msg}), 400


@bp.route("/api/custom-fields/<int:field_id>/delete", methods=["POST"])
@admin_required
def delete_custom_field(field_id: int):
    """刪除自訂欄位"""
    ok, msg = custom_field_service.delete_field(field_id)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "message": msg}), 404


@bp.route("/api/items/<item_id>/custom-fields", methods=["GET"])
@login_required
def get_item_custom_fields(item_id: str):
    """取得物品的自訂欄位值"""
    values = custom_field_service.get_item_custom_values(item_id)
    return jsonify({"success": True, "values": values})


@bp.route("/api/items/<item_id>/custom-fields", methods=["POST"])
@admin_required
def save_item_custom_fields(item_id: str):
    """儲存物品的自訂欄位值"""
    data = request.get_json() or {}
    custom_field_service.save_item_custom_values(item_id, data)
    return jsonify({"success": True, "message": _("自訂欄位已儲存")})
