"""群組管理藍圖路由"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session

from app.services import group_service
from app.utils.auth import login_required, get_current_user

bp = Blueprint("groups", __name__)


@bp.route("/groups")
@login_required
def group_list():
    """列出使用者的群組"""
    user = get_current_user()
    username = user.get("User", "")
    groups = group_service.get_user_groups(username)
    return render_template("groups.html", User=user, groups=groups)


@bp.route("/groups/create", methods=["POST"])
@login_required
def create_group():
    """建立新群組"""
    user = get_current_user()
    username = user.get("User", "")
    name = request.form.get("name", "").strip()

    ok, msg, group_id = group_service.create_group(name, username)
    if ok:
        flash(msg, "success")
        return redirect(url_for("groups.group_detail", id=group_id))
    else:
        flash(msg, "danger")
        return redirect(url_for("groups.group_list"))


@bp.route("/groups/<int:id>")
@login_required
def group_detail(id: int):
    """群組詳細頁"""
    user = get_current_user()
    username = user.get("User", "")

    detail = group_service.get_group_detail(id)
    if not detail:
        flash("群組不存在", "danger")
        return redirect(url_for("groups.group_list"))

    # 確認有權限查看（是成員或擁有者）
    from app.repositories import group_repo
    if not group_repo.is_member(id, username):
        flash("您不是此群組成員", "danger")
        return redirect(url_for("groups.group_list"))

    return render_template("group_detail.html", User=user, group=detail)


@bp.route("/groups/<int:id>/members", methods=["POST"])
@login_required
def add_member(id: int):
    """新增群組成員（JSON）"""
    user = get_current_user()
    inviter = user.get("User", "")
    data = request.get_json() or {}
    username = str(data.get("username", "")).strip()
    role = str(data.get("role", "member")).strip()

    ok, msg = group_service.invite_member(id, username, role, inviter)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "message": msg}), 400


@bp.route("/groups/<int:id>/members/<username>/remove", methods=["POST"])
@login_required
def remove_member(id: int, username: str):
    """移除群組成員"""
    user = get_current_user()
    remover = user.get("User", "")

    ok, msg = group_service.remove_member(id, username, remover)
    if request.is_json:
        if ok:
            return jsonify({"success": True, "message": msg})
        return jsonify({"success": False, "message": msg}), 400

    if ok:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("groups.group_detail", id=id))
