from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.services import type_service
from app.utils.auth import admin_required, get_current_user

bp = Blueprint("types", __name__)


@bp.route("/addtype", methods=["GET", "POST"])
@admin_required
def addtype():
    user = get_current_user()
    types = type_service.list_types()

    if request.method == "POST":
        type_name = request.form.get("name", "").strip()
        if not type_name:
            flash("類型名稱不能為空", "danger")
            return render_template("addtype.html", User=user, itemtype=types)
        
        # 檢查是否已存在
        existing_names = [t.get("name") for t in types]
        if type_name in existing_names:
            flash("該類型已存在", "danger")
            return render_template("addtype.html", User=user, itemtype=types)
        
        type_service.create_type({"name": type_name})
        flash("類型新增成功！", "success")
        return redirect(url_for("types.addtype"))

    return render_template("addtype.html", User=user, itemtype=types)

