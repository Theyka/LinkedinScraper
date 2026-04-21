import os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session

auth_bp = Blueprint("auth", __name__)


def check_credentials(username, password):
    admin_user = os.getenv("ADMIN_USER", "")
    admin_pass = os.getenv("ADMIN_PASSWORD", "")
    if not admin_user or not admin_pass:
        return False
    if username != admin_user:
        return False
    if password != admin_pass:
        return False
    return True


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("auth.login_page", next=request.url))
        return fn(*args, **kwargs)
    return wrapper


@auth_bp.route("/login", methods=["GET", "POST"])
def login_page():
    if session.get("logged_in"):
        return redirect(url_for("profile.index"))

    error = None

    if request.method == "POST":
        user = request.form.get("username", "")
        pwd = request.form.get("password", "")

        if check_credentials(user, pwd):
            session["logged_in"] = True
            session["username"] = user
            nxt = request.args.get("next")
            if not nxt:
                nxt = url_for("profile.index")
            return redirect(nxt)
        error = "Invalid credentials"

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))
