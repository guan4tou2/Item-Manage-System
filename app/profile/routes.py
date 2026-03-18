from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_babel import gettext as _

from app.services import user_service
from app.utils.auth import login_required, get_current_user

bp = Blueprint("profile", __name__)


@bp.route("/profile", methods=["GET"])
@login_required
def profile():
    user = get_current_user()
    username = session.get("UserID")
    profile_data = user_service.get_profile(username)
    return render_template("profile.html", User=user, profile=profile_data)


@bp.route("/profile", methods=["POST"])
@login_required
def update_profile():
    username = session.get("UserID")
    data = {
        "display_name": request.form.get("display_name", "").strip(),
        "theme_preference": request.form.get("theme_preference", "light"),
        "language": request.form.get("language", "zh_TW"),
        "email": request.form.get("email", "").strip(),
    }
    ok, msg = user_service.update_profile(username, data)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("profile.profile"))
