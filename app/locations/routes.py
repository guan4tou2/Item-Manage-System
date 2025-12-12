from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.services import location_service
from app.utils.auth import admin_required, get_current_user

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

