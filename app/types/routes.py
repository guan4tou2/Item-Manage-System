from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _

from app.services import type_service
from app.utils.auth import admin_required, get_current_user

bp = Blueprint("types", __name__)


@bp.route("/types", methods=["GET", "POST"])
@admin_required
def manage_types():
    user = get_current_user()
    types = type_service.list_types()

    if request.method == "POST":
        type_name = request.form.get("name", "").strip()
        if not type_name:
            flash(_("類型名稱不能為空"), "danger")
            return render_template("managetypes.html", User=user, itemtype=types)

        existing_names = [t.get("name") for t in types]
        if type_name in existing_names:
            flash(_("該類型已存在"), "danger")
            return render_template("managetypes.html", User=user, itemtype=types)

        parent_name = request.form.get("parent_name", "").strip()
        parent_id = None
        if parent_name:
            from app.repositories import type_repo
            parent = type_repo.get_type_by_name(parent_name)
            if parent:
                parent_id = parent.id if hasattr(parent, "id") else parent.get("_id")
        type_service.create_type({"name": type_name, "parent_id": parent_id})
        flash(_("類型新增成功！"), "success")
        return redirect(url_for("types.manage_types"))

    return render_template("managetypes.html", User=user, itemtype=types)


# Keep old route as redirect for backwards compatibility
@bp.route("/addtype", methods=["GET", "POST"])
@admin_required
def addtype():
    return redirect(url_for("types.manage_types"), code=301)


@bp.route("/types/edit", methods=["POST"])
@admin_required
def edit_type():
    old_name = request.form.get("old_name", "").strip()
    new_name = request.form.get("new_name", "").strip()

    if not old_name or not new_name:
        flash(_("請提供原始名稱和新名稱"), "danger")
        return redirect(url_for("types.manage_types"))

    ok, msg = type_service.update_type(old_name, new_name)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("types.manage_types"))


@bp.route("/types/delete/<name>", methods=["POST"])
@admin_required
def delete_type(name):
    ok, msg = type_service.delete_type(name)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("types.manage_types"))


@bp.route("/api/types/count/<name>")
@admin_required
def type_item_count(name):
    """API: get item count for a type."""
    from app.repositories import type_repo
    count = type_repo.count_items_by_type(name)
    return jsonify({"name": name, "count": count})


@bp.route("/api/types/tree")
@admin_required
def type_tree():
    """API: return hierarchical type tree as JSON."""
    tree = type_service.get_type_tree()
    return jsonify(tree)


@bp.route("/types/set-parent", methods=["POST"])
@admin_required
def set_type_parent():
    """Set the parent category for a type (form: type_name, parent_name)."""
    type_name = request.form.get("type_name", "").strip()
    parent_name = request.form.get("parent_name", "").strip()

    if not type_name:
        flash(_("請提供分類名稱"), "danger")
        return redirect(url_for("types.manage_types"))

    ok, msg = type_service.set_parent(type_name, parent_name or None)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("types.manage_types"))
