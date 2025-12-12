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

        if user_service.authenticate(username, password):
            session["UserID"] = username
            return redirect(url_for("items.home"))
        else:
            error = "帳號或密碼錯誤"
            return render_template("signin.html", error=error)

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


@bp.route("/signout")
def signout():
    session.pop("UserID", None)
    return redirect(url_for("auth.signin"))

