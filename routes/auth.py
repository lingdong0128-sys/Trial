# -*- coding: utf-8 -*-
from flask import Blueprint, request, redirect, url_for, session, render_template

auth_bp = Blueprint("auth", __name__)

DEFAULT_USER = "root"
DEFAULT_PASSWORD = "itzx"


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    if username == DEFAULT_USER and password == DEFAULT_PASSWORD:
        session["logged_in"] = True
        session["username"] = username
        return redirect(url_for("chat.index"))
    return render_template("login.html", error="用户名或密码错误"), 401


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.pop("logged_in", None)
    session.pop("username", None)
    return redirect(url_for("auth.login"))
