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


@bp.route("/signout")
def signout():
    session.pop("UserID", None)
    return redirect(url_for("auth.signin"))

