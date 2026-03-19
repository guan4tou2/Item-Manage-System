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


@bp.route("/profile/resend-verification", methods=["POST"])
@login_required
def resend_verification():
    """重新發送 Email 驗證信"""
    username = session.get("UserID")
    profile_data = user_service.get_profile(username)
    email = profile_data.get("email", "")
    if not email:
        flash("請先在個人設定中填寫 Email", "warning")
        return redirect(url_for("profile.profile"))
    try:
        from flask import url_for as _url_for
        from app.services.email_service import send_email_verification
        token = user_service.generate_email_verify_token(username)
        verify_url = _url_for("auth.verify_email_route", token=token, _external=True)
        send_email_verification(email, verify_url)
        flash("驗證信已重新發送，請檢查您的信箱", "success")
    except Exception:
        flash("驗證信發送失敗，請確認系統 Email 設定", "danger")
    return redirect(url_for("profile.profile"))


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
