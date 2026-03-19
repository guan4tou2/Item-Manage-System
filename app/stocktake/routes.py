"""庫存盤點藍圖路由"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash

from app.services import stocktake_service
from app.utils.auth import admin_required, get_current_user

bp = Blueprint("stocktake", __name__)


@bp.route("/stocktake")
@admin_required
def stocktake_list():
    """盤點作業列表頁面"""
    user = get_current_user()
    sessions = stocktake_service.list_sessions()
    return render_template("stocktake_list.html", User=user, sessions=sessions)


@bp.route("/stocktake/create", methods=["POST"])
@admin_required
def stocktake_create():
    """建立新盤點作業"""
    user = get_current_user()
    created_by = user.get("User", "")
    name = request.form.get("name", "").strip()
    notes = request.form.get("notes", "").strip() or None

    ok, msg, session_id = stocktake_service.create_session(
        name=name,
        created_by=created_by,
        notes=notes,
    )
    if ok:
        flash(msg, "success")
        return redirect(url_for("stocktake.stocktake_detail", session_id=session_id))
    flash(msg, "danger")
    return redirect(url_for("stocktake.stocktake_list"))


@bp.route("/stocktake/<int:session_id>")
@admin_required
def stocktake_detail(session_id: int):
    """盤點作業詳細頁面"""
    user = get_current_user()
    sess = stocktake_service.get_session_detail(session_id)
    if not sess:
        flash("找不到盤點作業", "danger")
        return redirect(url_for("stocktake.stocktake_list"))
    return render_template("stocktake_detail.html", User=user, session=sess)


@bp.route("/api/stocktake/<int:session_id>/count", methods=["POST"])
@admin_required
def api_record_count(session_id: int):
    """API: 記錄盤點數量（JSON）"""
    user = get_current_user()
    counted_by = user.get("User", "")
    data = request.get_json() or {}

    item_id = str(data.get("item_id", "")).strip()
    actual_qty = data.get("actual_qty")

    if not item_id:
        return jsonify({"success": False, "message": "物品 ID 不可為空"}), 400

    ok, msg = stocktake_service.record_count(
        session_id=session_id,
        item_id=item_id,
        actual_qty=actual_qty,
        counted_by=counted_by,
    )
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "message": msg}), 400


@bp.route("/stocktake/<int:session_id>/start", methods=["POST"])
@admin_required
def stocktake_start(session_id: int):
    """開始盤點作業"""
    ok, msg = stocktake_service.start_session(session_id)
    if ok:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("stocktake.stocktake_detail", session_id=session_id))


@bp.route("/stocktake/<int:session_id>/complete", methods=["POST"])
@admin_required
def stocktake_complete(session_id: int):
    """完成盤點（進入審核）"""
    ok, msg = stocktake_service.complete_counting(session_id)
    if ok:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("stocktake.stocktake_detail", session_id=session_id))


@bp.route("/stocktake/<int:session_id>/commit", methods=["POST"])
@admin_required
def stocktake_commit(session_id: int):
    """提交盤點，更新庫存數量"""
    ok, msg = stocktake_service.commit_session(session_id)
    if ok:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("stocktake.stocktake_detail", session_id=session_id))
