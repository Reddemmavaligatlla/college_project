from flask import Flask, jsonify, redirect, render_template, request, url_for
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
DATASET_FILE = "data/ecommerce_dataset_cleaned.csv"

# --------------------------------------------------
# LOAD DATASET (EXISTING USER IDS)
# --------------------------------------------------
df = pd.read_csv(DATASET_FILE)
existing_ids = set(df["user_id"].astype(str))


def normalize_category(value):
    if value is None:
        return ""
    return str(value).strip().lower().replace("&", "and")


def format_category(value):
    normalized = normalize_category(value)
    title = normalized.title()
    return title.replace("And", "&")


def generate_description(product_name, category, price, rating):
    normalized = normalize_category(category)

    category_lines = {
        "electronics": "Reliable daily-use electronics focused on utility and performance.",
        "fashion": "Comfort-first fashion item suitable for regular wear.",
        "beauty": "Personal care product designed for routine skin and self-care needs.",
        "books": "A reader-friendly title that supports learning and leisure.",
        "home and kitchen": "Practical home and kitchen product for everyday convenience.",
        "groceries": "Essential grocery item for regular household use.",
        "grocery": "Essential grocery item for regular household use.",
        "sports": "Active-lifestyle product built for training and daily movement.",
        "toys": "Fun and safe kids-oriented item for play and learning.",
        "kids wear": "Comfortable kids wear designed for daily activity.",
    }

    base_line = category_lines.get(
        normalized,
        "Useful product selected from your shopping interests.",
    )

    rating_line = ""
    if pd.notna(rating):
        rating_line = f" Customer rating: {float(rating):.1f}/5."

    return (
        f"{product_name.title()} belongs to {format_category(category)} category. "
        f"{base_line} Price: ₹{int(float(price))}.{rating_line}"
    ).strip()


def get_product_catalog():
    data = pd.read_csv(DATASET_FILE)
    if "description" not in data.columns:
        data["description"] = ""

    products = (
        data[["product_id", "product_name", "category", "price", "rating", "description"]]
        .drop_duplicates(subset=["product_id"])
        .copy()
    )
    products["category_display"] = products["category"].apply(format_category)
    products["category_norm"] = products["category"].apply(normalize_category)
    products["description"] = products.apply(
        lambda row: (
            str(row["description"]).strip()
            if str(row["description"]).strip()
            else generate_description(
                row["product_name"],
                row["category"],
                row["price"],
                row["rating"],
            )
        ),
        axis=1,
    )
    return products


def get_product_by_id(product_id):
    products = get_product_catalog()
    match = products[products["product_id"].astype(str) == str(product_id)]
    if match.empty:
        return None
    return match.iloc[0].to_dict()

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

    catalog = get_product_catalog()
    products = catalog.sort_values("product_name").to_dict(orient="records")

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

    catalog = get_product_catalog()

    # ✅ IMPROVED CATEGORY MAPPING
    if category.lower() == "all":
        filtered = catalog

    elif category.lower() == "men":
        filtered = catalog[catalog["category_norm"].isin(["electronics", "fashion"])]

    elif category.lower() == "women":
        filtered = catalog[catalog["category_norm"].isin(["beauty", "fashion"])]

    elif category.lower() == "kids":
        filtered = catalog[catalog["category_norm"].isin(["toys", "kids wear"])]

    else:
        filtered = catalog

    products = filtered.sort_values("product_name").to_dict(orient="records")

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

    content_recs = content_df[["product_name", "category"]].drop_duplicates()
    content_recs["category"] = content_recs["category"].apply(format_category)
    content_recs = content_recs.to_dict(orient="records")

    collaborative_categories = recommend_from_similar_users(
        user_id,
        USERS_FILE,
        top_n=5
    )

    catalog = get_product_catalog()
    collaborative_norm = {normalize_category(cat) for cat in collaborative_categories}
    collab_df = catalog[catalog["category_norm"].isin(collaborative_norm)]

    collab_recs = (
        collab_df[["product_name", "category_display"]]
        .head(5)
        .rename(columns={"category_display": "category"})
        .to_dict(orient="records")
    )

    trend_df = pd.read_csv(DATASET_FILE)
    trending_names = (
        trend_df["product_name"]
        .value_counts()
        .head(5)
        .index
        .tolist()
    )
    trending_df = catalog[catalog["product_name"].isin(trending_names)].copy()
    trending_df = (
        trending_df.set_index("product_name")
        .loc[[name for name in trending_names if name in trending_df["product_name"].values]]
        .reset_index()
    )
    trending_recs = (
        trending_df[["product_name", "category_display"]]
        .rename(columns={"category_display": "category"})
        .to_dict(orient="records")
    )

    return render_template(
        "recommendations.html",
        user_id=user_id,
        content_recommendations=content_recs,
        collaborative_recommendations=collab_recs,
        trending_recommendations=trending_recs,
    )


# ==================================================
# 📦 PRODUCT DETAILS
# ==================================================
@app.route("/product/<user_id>/<product_id>")
def product_details(user_id, product_id):
    users = load_users()
    if user_id not in users:
        return redirect(url_for("user_login"))

    product = get_product_by_id(product_id)
    if not product:
        return redirect(url_for("products", user_id=user_id))

    return render_template("product_details.html", user_id=user_id, product=product)


# ==================================================
# 💳 BUY PAGE
# ==================================================
@app.route("/buy/<user_id>/<product_id>")
def buy_product(user_id, product_id):
    users = load_users()
    if user_id not in users:
        return redirect(url_for("user_login"))

    product = get_product_by_id(product_id)
    if not product:
        return redirect(url_for("products", user_id=user_id))

    return render_template("buy.html", user_id=user_id, product=product)


# ==================================================
# 🧠 TRACK INTERACTION (USED BY PRODUCT ACTIONS)
# ==================================================
@app.route("/track_interaction/<user_id>", methods=["POST"])
def track_interaction(user_id):
    users = load_users()
    if user_id not in users:
        return jsonify({"status": "error", "message": "Invalid user"}), 404

    payload = request.get_json(silent=True) or {}
    category = payload.get("category", "").strip()
    if not category:
        return jsonify({"status": "ok"})

    stored_preferences = users[user_id].get("preferences", [])
    normalized_current = normalize_category(category)

    updated_preferences = [
        pref for pref in stored_preferences
        if normalize_category(pref) != normalized_current
    ]
    updated_preferences.insert(0, format_category(category))

    users[user_id]["preferences"] = updated_preferences[:5]
    save_users(users)

    return jsonify({"status": "ok"})

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
        users[user_id]["preferences"] = [p.strip() for p in prefs.split(",") if p.strip()]
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
