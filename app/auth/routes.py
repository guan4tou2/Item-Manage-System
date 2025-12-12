from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.services import user_service

bp = Blueprint("auth", __name__)


@bp.route("/", methods=["GET", "POST"])
@bp.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        username = request.form.get("UserID", "").strip()
        password = request.form.get("Password", "")

        if not username or not password:
            flash("請輸入帳號與密碼", "danger")
            return render_template("signin.html", error="請輸入帳號與密碼")

        # 取得用戶 IP
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        success, error_msg = user_service.authenticate(username, password, ip_address)
        
        if success:
            session["UserID"] = username
            
            # 檢查是否需要強制修改密碼
            if user_service.needs_password_change(username):
                session["force_password_change"] = True
                flash("首次登入請修改預設密碼以確保安全", "warning")
                return redirect(url_for("auth.change_password"))
            
            return redirect(url_for("items.home"))
        else:
            return render_template("signin.html", error=error_msg)

    return render_template("signin.html")


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    """用戶註冊"""
    if request.method == "POST":
        username = request.form.get("UserID", "").strip()
        password = request.form.get("Password", "")
        confirm_password = request.form.get("ConfirmPassword", "")
        
        # 驗證輸入
        if not username or not password:
            flash("請填寫所有欄位", "danger")
            return render_template("signup.html", error="請填寫所有欄位")
        
        if len(username) < 3:
            flash("帳號至少需要 3 個字元", "danger")
            return render_template("signup.html", error="帳號至少需要 3 個字元")
        
        if len(password) < 6:
            flash("密碼至少需要 6 個字元", "danger")
            return render_template("signup.html", error="密碼至少需要 6 個字元")
        
        if password != confirm_password:
            flash("兩次輸入的密碼不一致", "danger")
            return render_template("signup.html", error="兩次輸入的密碼不一致")
        
        # 嘗試建立用戶
        if user_service.create_user(username, password, admin=False):
            flash("註冊成功！請登入", "success")
            return redirect(url_for("auth.signin"))
        else:
            flash("該帳號已被使用", "danger")
            return render_template("signup.html", error="該帳號已被使用")
    
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
            flash("請填寫所有欄位", "danger")
            return render_template("change_password.html", is_forced=is_forced)
        
        if new_password != confirm_password:
            flash("兩次輸入的密碼不一致", "danger")
            return render_template("change_password.html", is_forced=is_forced)
        
        # 強制修改時不需要舊密碼
        if is_forced:
            ok, msg = user_service.force_change_password(username, new_password)
        else:
            old_password = request.form.get("OldPassword", "")
            if not old_password:
                flash("請輸入舊密碼", "danger")
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
        flash("您沒有權限存取此頁面", "danger")
        return redirect(url_for("items.home"))
    
    users = user_service.list_users()
    
    return render_template(
        "admin_users.html",
        User=user,
        users=users,
    )


@bp.route("/admin/reset-password/<target_user>", methods=["POST"])
def admin_reset_password(target_user):
    """管理員重置用戶密碼"""
    username = session.get("UserID")
    if not username:
        return redirect(url_for("auth.signin"))
    
    user = user_service.get_user(username)
    if not user or not user.get("admin"):
        flash("您沒有權限執行此操作", "danger")
        return redirect(url_for("items.home"))
    
    ok, msg, new_password = user_service.admin_reset_password(target_user)
    
    if ok:
        flash(f"{msg}，新密碼為：{new_password}", "success")
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
        flash("您沒有權限執行此操作", "danger")
        return redirect(url_for("items.home"))
    
    if user_service.unlock_user(target_user):
        flash(f"已解鎖 {target_user} 的帳號", "success")
    else:
        flash("解鎖失敗", "danger")
    
    return redirect(url_for("auth.admin_users"))

