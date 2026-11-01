import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "campus-bites-demo-key-change-me")
app.config["DATABASE"] = os.environ.get("CAMPUS_BITES_DB", str(BASE_DIR / "instance" / "campus_bites.db"))

PICKUP_TIMES = ["10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM", "1:00 PM", "1:30 PM", "2:00 PM", "2:30 PM", "3:00 PM"]
ORDER_STATUSES = ["Pending", "Preparing", "Ready", "Completed", "Cancelled"]
FOOD_IMAGES = {
    "Chicken Biriyani": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=800&q=80",
    "Egg Biriyani": "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?auto=format&fit=crop&w=800&q=80",
    "Meals": "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80",
    "Samosa": "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=800&q=80",
    "Chicken Roll": "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=800&q=80",
    "Coffee": "https://images.unsplash.com/photo-1497636577773-f1231844b336?auto=format&fit=crop&w=800&q=80",
    "Tea": "https://images.unsplash.com/photo-1515823064-d6e0c04616a7?auto=format&fit=crop&w=800&q=80",
    "Watermelon Juice": "https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?auto=format&fit=crop&w=800&q=80",
    "Lime Juice": "https://images.unsplash.com/photo-1546173159-315724a31696?auto=format&fit=crop&w=800&q=80",
}


def get_db():
    """Open a fresh SQLite connection for the current request or operation."""
    database_path = app.config["DATABASE"]
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    """Create the relational schema and seed the menu once."""
    connection = get_db()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS CATEGORY (
            Category_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Category_Name TEXT NOT NULL UNIQUE,
            Description TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS STUDENT (
            Student_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Email TEXT NOT NULL UNIQUE,
            Phone TEXT NOT NULL,
            Department TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS FOOD_ITEM (
            Food_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Food_Name TEXT NOT NULL,
            Price REAL NOT NULL CHECK (Price >= 0),
            Availability INTEGER NOT NULL DEFAULT 1 CHECK (Availability IN (0, 1)),
            Category_ID INTEGER NOT NULL,
            FOREIGN KEY (Category_ID) REFERENCES CATEGORY(Category_ID)
        );
        CREATE TABLE IF NOT EXISTS ORDERS (
            Order_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Order_Date TEXT NOT NULL,
            Total_Amount REAL NOT NULL CHECK (Total_Amount >= 0),
            Order_Status TEXT NOT NULL DEFAULT 'Pending',
            Student_ID INTEGER NOT NULL,
            Pickup_Time TEXT NOT NULL,
            FOREIGN KEY (Student_ID) REFERENCES STUDENT(Student_ID)
        );
        CREATE TABLE IF NOT EXISTS ORDER_ITEM (
            Order_Item_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Quantity INTEGER NOT NULL CHECK (Quantity > 0),
            Unit_Price REAL NOT NULL CHECK (Unit_Price >= 0),
            Order_ID INTEGER NOT NULL,
            Food_ID INTEGER NOT NULL,
            FOREIGN KEY (Order_ID) REFERENCES ORDERS(Order_ID) ON DELETE CASCADE,
            FOREIGN KEY (Food_ID) REFERENCES FOOD_ITEM(Food_ID)
        );
        CREATE TABLE IF NOT EXISTS PAYMENT (
            Payment_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Amount REAL NOT NULL CHECK (Amount >= 0),
            Payment_Method TEXT NOT NULL,
            Payment_Status TEXT NOT NULL,
            Payment_Date TEXT NOT NULL,
            Order_ID INTEGER NOT NULL UNIQUE,
            FOREIGN KEY (Order_ID) REFERENCES ORDERS(Order_ID) ON DELETE CASCADE
        );
        """
    )

    custom_categories = [
        ("South Indian", "Fresh and spicy favourites from the kitchen."),
        ("Snacks", "Quick bites for your breaks."),
        ("Drinks", "Cool and refreshing beverages."),
    ]
    existing_categories = connection.execute("SELECT Category_Name FROM CATEGORY").fetchall()
    existing_names = {row["Category_Name"] for row in existing_categories}

    if len(existing_names) != len(custom_categories) or any(name not in existing_names for name, _ in custom_categories):
        connection.execute("DELETE FROM PAYMENT")
        connection.execute("DELETE FROM ORDER_ITEM")
        connection.execute("DELETE FROM ORDERS")
        connection.execute("DELETE FROM FOOD_ITEM")
        connection.execute("DELETE FROM CATEGORY")
        connection.executemany("INSERT INTO CATEGORY (Category_Name, Description) VALUES (?, ?)", custom_categories)
        category_ids = {row["Category_Name"]: row["Category_ID"] for row in connection.execute("SELECT * FROM CATEGORY")}
        foods = [
            ("Chicken Biriyani", 80, 1, category_ids["South Indian"]),
            ("Egg Biriyani", 40, 1, category_ids["South Indian"]),
            ("Meals", 30, 1, category_ids["South Indian"]),
            ("Samosa", 10, 1, category_ids["Snacks"]),
            ("Chicken Roll", 20, 1, category_ids["Snacks"]),
            ("Coffee", 15, 1, category_ids["Drinks"]),
            ("Tea", 10, 1, category_ids["Drinks"]),
            ("Watermelon Juice", 25, 1, category_ids["Drinks"]),
            ("Lime Juice", 20, 1, category_ids["Drinks"]),
        ]
        connection.executemany(
            "INSERT INTO FOOD_ITEM (Food_Name, Price, Availability, Category_ID) VALUES (?, ?, ?, ?)", foods
        )

    connection.commit()
    connection.close()


def menu_data():
    connection = get_db()
    foods = connection.execute(
        """SELECT f.Food_ID, f.Food_Name, f.Price, f.Availability, f.Category_ID,
                  c.Category_Name
           FROM FOOD_ITEM f JOIN CATEGORY c ON c.Category_ID = f.Category_ID
           ORDER BY f.Food_ID"""
    ).fetchall()
    categories = connection.execute("SELECT * FROM CATEGORY ORDER BY Category_ID").fetchall()
    connection.close()
    return foods, categories


@app.route("/")
def home():
    foods, categories = menu_data()
    return render_template("index.html", foods=foods, categories=categories, images=FOOD_IMAGES)


@app.route("/cart")
def cart():
    return render_template("cart.html")


@app.route("/checkout")
def checkout():
    return render_template("checkout.html", pickup_times=PICKUP_TIMES)


@app.post("/api/orders")
def create_order():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    phone = re.sub(r"[\s-]", "", str(data.get("phone", "")))
    department = str(data.get("department", "")).strip()
    pickup_time = str(data.get("pickup_time", ""))
    items = data.get("items", [])

    errors = []
    if not name or len(name) > 80:
        errors.append("Enter your name (up to 80 characters).")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        errors.append("Enter a valid email address.")
    if not re.fullmatch(r"\+?\d{10,13}", phone):
        errors.append("Enter a phone number with 10 to 13 digits.")
    if not department or len(department) > 80:
        errors.append("Enter your department.")
    if pickup_time not in PICKUP_TIMES:
        errors.append("Choose one of the available pickup times.")
    if not isinstance(items, list) or not items or len(items) > 30:
        errors.append("Your cart is empty or contains too many different items.")
    if errors:
        return jsonify({"errors": errors}), 400

    quantities = {}
    try:
        for item in items:
            food_id = int(item["food_id"])
            quantity = int(item["quantity"])
            if food_id < 1 or quantity < 1 or quantity > 20:
                raise ValueError
            quantities[food_id] = quantities.get(food_id, 0) + quantity
            if quantities[food_id] > 20:
                raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify({"errors": ["One or more cart quantities are invalid."]}), 400

    connection = get_db()
    try:
        connection.execute("BEGIN IMMEDIATE")
        placeholders = ",".join("?" for _ in quantities)
        food_rows = connection.execute(
            f"SELECT Food_ID, Food_Name, Price, Availability FROM FOOD_ITEM WHERE Food_ID IN ({placeholders})",
            tuple(quantities),
        ).fetchall()
        foods_by_id = {row["Food_ID"]: row for row in food_rows}
        if len(foods_by_id) != len(quantities) or any(not row["Availability"] for row in food_rows):
            connection.rollback()
            return jsonify({"errors": ["A selected item is no longer available. Refresh the menu and try again."]}), 409

        total = round(sum(foods_by_id[food_id]["Price"] * quantity for food_id, quantity in quantities.items()), 2)
        connection.execute(
            """INSERT INTO STUDENT (Name, Email, Phone, Department) VALUES (?, ?, ?, ?)
               ON CONFLICT(Email) DO UPDATE SET Name=excluded.Name, Phone=excluded.Phone, Department=excluded.Department""",
            (name, email, phone, department),
        )
        student_id = connection.execute("SELECT Student_ID FROM STUDENT WHERE Email = ?", (email,)).fetchone()[0]
        cursor = connection.execute(
            "INSERT INTO ORDERS (Order_Date, Total_Amount, Order_Status, Student_ID, Pickup_Time) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), total, "Pending", student_id, pickup_time),
        )
        order_id = cursor.lastrowid
        connection.executemany(
            "INSERT INTO ORDER_ITEM (Quantity, Unit_Price, Order_ID, Food_ID) VALUES (?, ?, ?, ?)",
            [(quantity, foods_by_id[food_id]["Price"], order_id, food_id) for food_id, quantity in quantities.items()],
        )
        connection.execute(
            "INSERT INTO PAYMENT (Amount, Payment_Method, Payment_Status, Payment_Date, Order_ID) VALUES (?, ?, ?, ?, ?)",
            (total, "Pay at pickup (demo)", "Pending", datetime.now().isoformat(timespec="seconds"), order_id),
        )
        connection.commit()
        return jsonify({"order_id": order_id, "redirect": url_for("confirmation", order_id=order_id)}), 201
    except sqlite3.Error:
        connection.rollback()
        app.logger.exception("Could not save order")
        return jsonify({"errors": ["We could not place your order. Please try again."]}), 500
    finally:
        connection.close()


@app.route("/order/<int:order_id>")
def confirmation(order_id):
    connection = get_db()
    order = connection.execute(
        """SELECT o.*, s.Name, s.Email FROM ORDERS o
           JOIN STUDENT s ON s.Student_ID = o.Student_ID WHERE o.Order_ID = ?""", (order_id,)
    ).fetchone()
    items = connection.execute(
        """SELECT oi.Quantity, oi.Unit_Price, f.Food_Name FROM ORDER_ITEM oi
           JOIN FOOD_ITEM f ON f.Food_ID = oi.Food_ID WHERE oi.Order_ID = ?""", (order_id,)
    ).fetchall()
    connection.close()
    if order is None:
        return render_template("not_found.html"), 404
    return render_template("confirmation.html", order=order, items=items)


@app.route("/orders")
def order_history():
    email = request.args.get("email", "").strip().lower()
    orders = []
    if email:
        connection = get_db()
        orders = connection.execute(
            """SELECT o.Order_ID, o.Order_Date, o.Total_Amount, o.Order_Status, o.Pickup_Time
               FROM ORDERS o JOIN STUDENT s ON s.Student_ID = o.Student_ID
               WHERE lower(s.Email) = ? ORDER BY o.Order_ID DESC""", (email,)
        ).fetchall()
        connection.close()
    return render_template("history.html", email=email, orders=orders, searched=bool(email))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        flash("Use the action buttons below to update menu items or order statuses.", "info")
        return redirect(url_for("admin"))
    connection = get_db()
    foods = connection.execute(
        """SELECT f.*, c.Category_Name FROM FOOD_ITEM f JOIN CATEGORY c ON c.Category_ID = f.Category_ID
           ORDER BY f.Food_ID DESC"""
    ).fetchall()
    categories = connection.execute("SELECT * FROM CATEGORY ORDER BY Category_Name").fetchall()
    orders = connection.execute(
        """SELECT o.Order_ID, o.Order_Date, o.Total_Amount, o.Order_Status, o.Pickup_Time, s.Name, s.Email
           FROM ORDERS o JOIN STUDENT s ON s.Student_ID = o.Student_ID ORDER BY o.Order_ID DESC LIMIT 50"""
    ).fetchall()
    connection.close()
    return render_template("admin.html", foods=foods, categories=categories, orders=orders, statuses=ORDER_STATUSES)


@app.post("/admin/food")
def add_food():
    name = request.form.get("food_name", "").strip()
    try:
        price = round(float(request.form.get("price", "")), 2)
        category_id = int(request.form.get("category_id", ""))
    except ValueError:
        flash("Enter a valid price and category.", "error")
        return redirect(url_for("admin"))
    if not name or len(name) > 80 or price < 0 or price > 10000:
        flash("Enter a food name and a price between Rs. 0 and Rs. 10,000.", "error")
        return redirect(url_for("admin"))
    connection = get_db()
    category = connection.execute("SELECT Category_ID FROM CATEGORY WHERE Category_ID = ?", (category_id,)).fetchone()
    if category is None:
        connection.close()
        flash("Choose a valid category.", "error")
        return redirect(url_for("admin"))
    connection.execute("INSERT INTO FOOD_ITEM (Food_Name, Price, Availability, Category_ID) VALUES (?, ?, 1, ?)", (name, price, category_id))
    connection.commit()
    connection.close()
    flash(f"{name} was added to the menu.", "success")
    return redirect(url_for("admin"))


@app.post("/admin/food/<int:food_id>")
def update_food(food_id):
    try:
        price = round(float(request.form.get("price", "")), 2)
    except ValueError:
        flash("Enter a valid price.", "error")
        return redirect(url_for("admin"))
    availability = 1 if request.form.get("availability") == "1" else 0
    if price < 0 or price > 10000:
        flash("Price must be between Rs. 0 and Rs. 10,000.", "error")
        return redirect(url_for("admin"))
    connection = get_db()
    cursor = connection.execute("UPDATE FOOD_ITEM SET Price = ?, Availability = ? WHERE Food_ID = ?", (price, availability, food_id))
    connection.commit()
    connection.close()
    flash("Menu item updated." if cursor.rowcount else "That menu item was not found.", "success" if cursor.rowcount else "error")
    return redirect(url_for("admin"))


@app.post("/admin/order/<int:order_id>/status")
def update_order_status(order_id):
    status = request.form.get("status", "")
    if status not in ORDER_STATUSES:
        flash("Choose a valid order status.", "error")
        return redirect(url_for("admin"))
    connection = get_db()
    cursor = connection.execute("UPDATE ORDERS SET Order_Status = ? WHERE Order_ID = ?", (status, order_id))
    connection.commit()
    connection.close()
    flash("Order status updated." if cursor.rowcount else "That order was not found.", "success" if cursor.rowcount else "error")
    return redirect(url_for("admin"))


@app.cli.command("init-db")
def init_db_command():
    """Initialize the database using Flask's command line."""
    init_db()
    print("Campus Bites database is ready.")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
