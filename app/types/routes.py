from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.services import type_service, user_service

bp = Blueprint("types", __name__)


def _require_login():
    if "UserID" not in session:
        return redirect(url_for("auth.signin"))
    return None


def _current_user():
    user_id = session.get("UserID")
    user = user_service.get_user(user_id) if user_id else None
    return user or {"User": user_id, "admin": False}


@bp.route("/addtype", methods=["GET", "POST"])
def addtype():
    need = _require_login()
    if need:
        return need

    user = _current_user()
    types = type_service.list_types()

    if request.method == "POST":
        type_service.create_type(dict(request.form))
        flash("類型新增成功！", "success")
        return redirect(url_for("types.addtype"))

    return render_template("addtype.html", User=user, itemtype=types)

