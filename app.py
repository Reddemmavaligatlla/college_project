from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import json
import os

# --------------------------------------------------
# BLUEPRINT
# --------------------------------------------------
from auth.register import register_bp

app = Flask(__name__)
app.register_blueprint(register_bp)

# --------------------------------------------------
# FILE PATHS
# --------------------------------------------------
USERS_FILE = "data/users.json"
ACCOUNTS_FILE = "data/accounts.json"

# --------------------------------------------------
# LOAD DATASET (EXISTING USER IDS)
# --------------------------------------------------
df = pd.read_csv("data/ecommerce_dataset_cleaned.csv")
existing_ids = set(df["user_id"].astype(str))

# --------------------------------------------------
# LOAD USERS
# --------------------------------------------------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# --------------------------------------------------
# LOAD ACCOUNTS
# --------------------------------------------------
def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    return {}

# ==================================================
# 1️⃣ EMAIL + PASSWORD LOGIN
# ==================================================
@app.route("/login", methods=["GET", "POST"])
def email_login():
    message = None
    accounts = load_accounts()

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()

        if email not in accounts:
            message = "Email not registered ❌"
        elif accounts[email]["password"] != password:
            message = "Incorrect password ❌"
        else:
            return redirect(url_for("user_login"))

    return render_template("email_login.html", message=message)

# ==================================================
# 2️⃣ USER ID LOGIN
# ==================================================
@app.route("/", methods=["GET", "POST"])
def user_login():
    users = load_users()
    message = None

    if request.method == "POST":
        user_id = request.form["user_id"].strip()
        name = request.form["name"].strip()

        if user_id in users:
            if users[user_id]["name"].lower() != name.lower():
                message = f"Oops 😄 we already have a name for you: {users[user_id]['name']}"
            else:
                return redirect(url_for("dashboard", user_id=user_id))
        else:
            users[user_id] = {"name": name, "preferences": []}
            save_users(users)
            return redirect(url_for("dashboard", user_id=user_id))

    return render_template(
        "login.html",
        user_ids=sorted(existing_ids),
        message=message
    )

# ==================================================
# DASHBOARD
# ==================================================
@app.route("/dashboard/<user_id>")
def dashboard(user_id):
    users = load_users()

    if user_id not in users:
        return redirect(url_for("user_login"))

    return render_template(
        "dashboard.html",
        name=users[user_id]["name"],
        user_id=user_id
    )

# ==================================================
# 📂 CATEGORY SELECTION PAGE
# ==================================================
@app.route("/categories/<user_id>")
def categories(user_id):
    users = load_users()

    if user_id not in users:
        return redirect(url_for("user_login"))

    return render_template("categories.html", user_id=user_id)

# ==================================================
# 🛍️ ALL PRODUCTS
# ==================================================
@app.route("/products/<user_id>")
def products(user_id):
    users = load_users()

    if user_id not in users:
        return redirect(url_for("user_login"))

    df = pd.read_csv("data/ecommerce_dataset_cleaned.csv")

    products = (
        df[["product_name", "category", "price"]]
        .drop_duplicates()
        .to_dict(orient="records")
    )

    return render_template(
        "products.html",
        user_id=user_id,
        products=products
    )

# ==================================================
# 🧩 CATEGORY-WISE PRODUCTS (UPDATED LOGIC ✅)
# ==================================================
@app.route("/products/<category>/<user_id>")
def category_products(category, user_id):
    users = load_users()

    if user_id not in users:
        return redirect(url_for("user_login"))

    df = pd.read_csv("data/ecommerce_dataset_cleaned.csv")

    # ✅ IMPROVED CATEGORY MAPPING
    if category.lower() == "all":
        filtered = df

    elif category.lower() == "men":
        filtered = df[df["category"].str.lower().isin(["electronics", "fashion"])]

    elif category.lower() == "women":
        filtered = df[df["category"].str.lower().isin(["beauty", "fashion"])]

    elif category.lower() == "kids":
        filtered = df[df["category"].str.lower().isin(["toys", "kids wear"])]

    else:
        filtered = df

    products = (
        filtered[["product_name", "category", "price"]]
        .drop_duplicates()
        .to_dict(orient="records")
    )

    return render_template(
        "category_products.html",
        user_id=user_id,
        category=category,
        products=products
    )

# ==================================================
# ⭐ RECOMMENDATIONS
# ==================================================
@app.route("/recommendations/<user_id>")
def recommendations(user_id):
    users = load_users()

    if user_id not in users:
        return redirect(url_for("user_login"))

    user_preferences = users[user_id].get("preferences", [])

    if not user_preferences:
        return redirect(url_for("preferences", user_id=user_id))

    from models.content_based import recommend_products
    from models.collaborative import recommend_from_similar_users

    content_df = recommend_products(
        "data/ecommerce_dataset_cleaned.csv",
        user_preferences,
        top_n=5
    )

    content_recs = (
        content_df[["product_name", "category"]]
        .drop_duplicates()
        .to_dict(orient="records")
    )

    collaborative_categories = recommend_from_similar_users(
        user_id,
        USERS_FILE,
        top_n=5
    )

    df = pd.read_csv("data/ecommerce_dataset_cleaned.csv")
    collab_df = df[df["category"].isin(collaborative_categories)]

    collab_recs = (
        collab_df[["product_name", "category"]]
        .drop_duplicates()
        .head(5)
        .to_dict(orient="records")
    )

    return render_template(
        "recommendations.html",
        user_id=user_id,
        content_recommendations=content_recs,
        collaborative_recommendations=collab_recs
    )

# ==================================================
# ⚙️ PREFERENCES
# ==================================================
@app.route("/preferences/<user_id>", methods=["GET", "POST"])
def preferences(user_id):
    users = load_users()

    if user_id not in users:
        return redirect(url_for("user_login"))

    if request.method == "POST":
        prefs = request.form.get("preferences", "")
        users[user_id]["preferences"] = [p for p in prefs.split(",") if p]
        save_users(users)
        return redirect(url_for("dashboard", user_id=user_id))

    return render_template(
        "preferences.html",
        user_id=user_id,
        existing_preferences=users[user_id].get("preferences", [])
    )

# --------------------------------------------------
# RUN
# --------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
