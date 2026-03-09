from flask import Blueprint, render_template, request, redirect, url_for
import json
import os

register_bp = Blueprint("register", __name__)

ACCOUNTS_FILE = "data/accounts.json"


# --------------------------------------------------
# LOAD ACCOUNTS
# --------------------------------------------------
def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    return {}


# --------------------------------------------------
# SAVE ACCOUNTS
# --------------------------------------------------
def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=4)


# --------------------------------------------------
# REGISTER
# --------------------------------------------------
@register_bp.route("/register", methods=["GET", "POST"])
def register():
    message = None
    accounts = load_accounts()

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()

        if not email or not password:
            message = "All fields are required ❌"

        elif email in accounts:
            message = "Email already registered ❌"

        else:
            accounts[email] = {
                "password": password  # plain password (demo purpose)
            }
            save_accounts(accounts)
            return redirect(url_for("user_login"))  # ✅ FIXED

    return render_template("register.html", message=message)


# --------------------------------------------------
# FORGOT PASSWORD
# --------------------------------------------------
@register_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    message = None
    accounts = load_accounts()

    if request.method == "POST":
        email = request.form["email"].strip().lower()

        if email not in accounts:
            message = "Email not found ❌"
        else:
            return redirect(
                url_for("register.reset_password", email=email)
            )

    return render_template("forgot_password.html", message=message)


# --------------------------------------------------
# RESET PASSWORD
# --------------------------------------------------
@register_bp.route("/reset-password/<email>", methods=["GET", "POST"])
def reset_password(email):
    accounts = load_accounts()
    message = None

    if email not in accounts:
        return redirect(url_for("register.forgot_password"))

    if request.method == "POST":
        new_password = request.form["password"].strip()

        if not new_password:
            message = "Password cannot be empty ❌"
        else:
            accounts[email]["password"] = new_password
            save_accounts(accounts)
            return redirect(url_for("user_login"))  # ✅ FIXED

    return render_template(
        "reset_password.html",
        email=email,
        message=message
    )
