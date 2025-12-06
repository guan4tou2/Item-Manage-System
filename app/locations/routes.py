from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.services import location_service, user_service

bp = Blueprint("locations", __name__)


def _require_login():
    if "UserID" not in session:
        return redirect(url_for("auth.signin"))
    return None


def _current_user():
    user_id = session.get("UserID")
    user = user_service.get_user(user_id) if user_id else None
    return user or {"User": user_id, "admin": False}


@bp.route("/locations", methods=["GET", "POST"])
def manage_locations():
    need = _require_login()
    if need:
        return need

    user = _current_user()
    locations = location_service.list_locations()

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
            location_service.update_location(loc_id, doc)
            flash("位置選項已更新", "success")
        else:
            doc = {
                "floor": request.form.get("floor", "").strip(),
                "room": request.form.get("room", "").strip(),
                "zone": request.form.get("zone", "").strip(),
            }
            location_service.create_location(doc)
            flash("位置選項已新增", "success")
        return redirect(url_for("locations.manage_locations"))

    return render_template("locations.html", User=user, locations=locations)

