from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
from models.content_based import recommend_products
from models.collaborative import recommend_from_similar_users
import json
import os

app = Flask(__name__)

# Load dataset (only for existing user check)
df = pd.read_csv("data/ecommerce_dataset_cleaned.csv")
existing_ids = set(df["user_id"].astype(str))

USERS_FILE = "data/users.json"

# Load or create users.json
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
else:
    users = {}

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
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
            save_users()
            return redirect(url_for("dashboard", user_id=user_id))

    return render_template("login.html", user_ids=sorted(existing_ids), message=message)


def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


# ---------------- DASHBOARD ----------------
@app.route("/dashboard/<user_id>")
def dashboard(user_id):
    if user_id not in users:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        name=users[user_id]["name"],
        user_id=user_id
    )


# ---------------- RECOMMENDATIONS ----------------
@app.route("/recommendations/<user_id>")
def recommendations(user_id):
    if user_id not in users:
        return redirect(url_for("login"))

    user_preferences = users[user_id].get("preferences", [])
    if not user_preferences:
        return redirect(url_for("preferences", user_id=user_id))

    # Content-based
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

    # Collaborative
    collaborative_categories = recommend_from_similar_users(
        user_id,
        "data/users.json",
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


# ---------------- ALL PRODUCTS ----------------
@app.route("/products/<user_id>")
def products(user_id):
    if user_id not in users:
        return redirect(url_for("login"))

    df = pd.read_csv("data/ecommerce_dataset_cleaned.csv")

    products = (
        df[["product_name", "category"]]
        .drop_duplicates()
        .to_dict(orient="records")
    )

    return render_template(
        "products.html",
        user_id=user_id,
        products=products
    )


# ---------------- PREFERENCES ----------------
@app.route("/preferences/<user_id>", methods=["GET", "POST"])
def preferences(user_id):
    if user_id not in users:
        return redirect(url_for("login"))

    if request.method == "POST":
        prefs = request.form.get("preferences", "")
        users[user_id]["preferences"] = [p for p in prefs.split(",") if p]
        save_users()
        return redirect(url_for("dashboard", user_id=user_id))

    return render_template(
        "preferences.html",
        user_id=user_id,
        existing_preferences=users[user_id].get("preferences", [])
    )


if __name__ == "__main__":
    app.run(debug=True)


