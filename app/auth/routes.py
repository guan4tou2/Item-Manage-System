from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_babel import gettext as _

from app import limiter
from app.services import user_service
from app.utils.validators import validate_password_strength

bp = Blueprint("auth", __name__)


@bp.route("/", methods=["GET", "POST"])
@bp.route("/signin", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def signin():
    if request.method == "POST":
        username = request.form.get("UserID", "").strip()
        password = request.form.get("Password", "")

        if not username or not password:
            flash(_("請輸入帳號與密碼"), "danger")
            return render_template("signin.html", error=_("請輸入帳號與密碼"))

        # 取得用戶 IP（使用 remote_addr 避免 X-Forwarded-For 偽造）
        ip_address = request.remote_addr or ""
        
        success, error_msg = user_service.authenticate(username, password, ip_address)
        
        if success:
            session.clear()
            session["UserID"] = username
            
            # 檢查是否需要強制修改密碼
            if user_service.needs_password_change(username):
                session["force_password_change"] = True
                flash(_("首次登入請修改預設密碼以確保安全"), "warning")
                return redirect(url_for("auth.change_password"))
            
            return redirect(url_for("items.dashboard"))
        else:
            return render_template("signin.html", error=error_msg)

    return render_template("signin.html")


@bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def signup():
    """用戶註冊"""
    if request.method == "POST":
        username = request.form.get("UserID", "").strip()
        password = request.form.get("Password", "")
        confirm_password = request.form.get("ConfirmPassword", "")
        
        # 驗證輸入
        if not username or not password:
            flash(_("請填寫所有欄位"), "danger")
            return render_template("signup.html", error=_("請填寫所有欄位"))

        if len(username) < 3:
            flash(_("帳號至少需要 3 個字元"), "danger")
            return render_template("signup.html", error=_("帳號至少需要 3 個字元"))

        pw_errors = validate_password_strength(password)
        if pw_errors:
            for err in pw_errors:
                flash(_(err), "danger")
            return render_template("signup.html", error=_(pw_errors[0]))

        if password != confirm_password:
            flash(_("兩次輸入的密碼不一致"), "danger")
            return render_template("signup.html", error=_("兩次輸入的密碼不一致"))

        # 嘗試建立用戶
        email = request.form.get("Email", "").strip()
        if user_service.create_user(username, password, admin=False):
            # 若有提供 email，發送驗證信
            if email:
                try:
                    from app.services.email_service import send_email_verification
                    token = user_service.generate_email_verify_token(username)
                    verify_url = url_for("auth.verify_email_route", token=token, _external=True)
                    send_email_verification(email, verify_url)
                except Exception:
                    pass
            flash(_("註冊成功！請登入"), "success")
            return redirect(url_for("auth.signin"))
        else:
            flash(_("該帳號已被使用"), "danger")
            return render_template("signup.html", error=_("該帳號已被使用"))
    
    return render_template("signup.html")


@bp.route("/change-password", methods=["GET", "POST"])
def change_password():
    """修改密碼頁面"""
    # 檢查是否已登入
    username = session.get("UserID")
    if not username:
        return redirect(url_for("auth.signin"))
    
    is_forced = session.get("force_password_change", False)
    
    if request.method == "POST":
        new_password = request.form.get("NewPassword", "")
        confirm_password = request.form.get("ConfirmPassword", "")
        
        if not new_password or not confirm_password:
            flash(_("請填寫所有欄位"), "danger")
            return render_template("change_password.html", is_forced=is_forced)

        if new_password != confirm_password:
            flash(_("兩次輸入的密碼不一致"), "danger")
            return render_template("change_password.html", is_forced=is_forced)

        pw_errors = validate_password_strength(new_password)
        if pw_errors:
            for err in pw_errors:
                flash(_(err), "danger")
            return render_template("change_password.html", is_forced=is_forced)

        # 強制修改時不需要舊密碼
        if is_forced:
            ok, msg = user_service.force_change_password(username, new_password)
        else:
            old_password = request.form.get("OldPassword", "")
            if not old_password:
                flash(_("請輸入舊密碼"), "danger")
                return render_template("change_password.html", is_forced=is_forced)
            ok, msg = user_service.change_password(username, old_password, new_password)
        
        if ok:
            session.pop("force_password_change", None)
            flash(msg, "success")
            return redirect(url_for("items.home"))
        else:
            flash(msg, "danger")
            return render_template("change_password.html", is_forced=is_forced)
    
    return render_template("change_password.html", is_forced=is_forced)


@bp.route("/verify-email/<token>")
def verify_email_route(token: str):
    """Email 驗證連結"""
    ok, msg = user_service.verify_email(token)
    flash(_(msg), "success" if ok else "danger")
    return redirect(url_for("auth.signin"))


@bp.route("/signout")
def signout():
    session.pop("UserID", None)
    session.pop("force_password_change", None)
    return redirect(url_for("auth.signin"))


@bp.route("/admin/users")
def admin_users():
    """用戶管理頁面（僅管理員）"""
    username = session.get("UserID")
    if not username:
        return redirect(url_for("auth.signin"))
    
    user = user_service.get_user(username)
    if not user or not user.get("admin"):
        flash(_("您沒有權限存取此頁面"), "danger")
        return redirect(url_for("items.home"))
    
    users = user_service.list_users()
    
    return render_template(
        "admin_users.html",
        User=user,
        users=users,
    )


@bp.route("/admin/users/create", methods=["POST"])
def admin_create_user():
    """管理員新增用戶"""
    username = session.get("UserID")
    if not username:
        return redirect(url_for("auth.signin"))

    user = user_service.get_user(username)
    if not user or not user.get("admin"):
        flash(_("您沒有權限執行此操作"), "danger")
        return redirect(url_for("items.home"))

    new_username = request.form.get("UserID", "").strip()
    password = request.form.get("Password", "")
    confirm_password = request.form.get("ConfirmPassword", "")
    is_admin = request.form.get("admin") == "on"

    if not new_username or not password or not confirm_password:
        flash(_("請填寫新增用戶所需欄位"), "danger")
        return redirect(url_for("auth.admin_users"))

    if len(new_username) < 3:
        flash(_("帳號至少需要 3 個字元"), "danger")
        return redirect(url_for("auth.admin_users"))

    if password != confirm_password:
        flash(_("兩次輸入的密碼不一致"), "danger")
        return redirect(url_for("auth.admin_users"))

    ok, msg = user_service.validate_new_password(password)
    if not ok:
        flash(msg, "danger")
        return redirect(url_for("auth.admin_users"))

    if user_service.create_user(new_username, password, admin=is_admin):
        role_label = _("管理員") if is_admin else _("一般用戶")
        flash(_("已新增 %(username)s（%(role)s）", username=new_username, role=role_label), "success")
    else:
        flash(_("新增失敗，帳號可能已存在或密碼不符合規則"), "danger")

    return redirect(url_for("auth.admin_users"))


@bp.route("/admin/reset-password/<target_user>", methods=["POST"])
def admin_reset_password(target_user):
    """管理員重置用戶密碼"""
    username = session.get("UserID")
    if not username:
        return redirect(url_for("auth.signin"))
    
    user = user_service.get_user(username)
    if not user or not user.get("admin"):
        flash(_("您沒有權限執行此操作"), "danger")
        return redirect(url_for("items.home"))

    ok, msg, new_password = user_service.admin_reset_password(target_user)

    if ok:
        flash(_("%(msg)s，新密碼為：%(pw)s", msg=msg, pw=new_password), "success")
    else:
        flash(msg, "danger")
    
    return redirect(url_for("auth.admin_users"))


@bp.route("/admin/unlock-user/<target_user>", methods=["POST"])
def admin_unlock_user(target_user):
    """管理員解鎖用戶帳號"""
    username = session.get("UserID")
    if not username:
        return redirect(url_for("auth.signin"))
    
    user = user_service.get_user(username)
    if not user or not user.get("admin"):
        flash(_("您沒有權限執行此操作"), "danger")
        return redirect(url_for("items.home"))

    if user_service.unlock_user(target_user):
        flash(_("已解鎖 %(user)s 的帳號", user=target_user), "success")
    else:
        flash(_("解鎖失敗"), "danger")
    
    return redirect(url_for("auth.admin_users"))


@bp.route("/admin/delete-user/<target_user>", methods=["POST"])
def admin_delete_user(target_user):
    """管理員刪除用戶"""
    username = session.get("UserID")
    if not username:
        return redirect(url_for("auth.signin"))

    user = user_service.get_user(username)
    if not user or not user.get("admin"):
        flash(_("您沒有權限執行此操作"), "danger")
        return redirect(url_for("items.home"))

    ok, msg = user_service.delete_user(username, target_user)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("auth.admin_users"))
