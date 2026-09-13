import os
import sqlite3
import uuid
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

DATABASE = "database.db"
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT DEFAULT '',
            quantity INTEGER NOT NULL DEFAULT 1,
            image TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            message TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    try:
        conn.execute(
            "ALTER TABLE products ADD COLUMN category TEXT NOT NULL DEFAULT 'Other'"
        )
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    category = request.args.get("category", "All")

    conn = get_db()

    if category == "All":
        products = conn.execute(
            "SELECT * FROM products ORDER BY id DESC"
        ).fetchall()
    else:
        products = conn.execute(
            "SELECT * FROM products WHERE category = ? ORDER BY id DESC",
            (category,)
        ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        products=products,
        selected_category=category
    )

@app.route("/product/<int:product_id>")
def product(product_id):
    conn = get_db()
    item = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    if item is None:
        return "Product not found", 404
    return render_template("product.html", product=item)


@app.route("/order/<int:product_id>", methods=["GET", "POST"])
def order(product_id):
    conn = get_db()
    item = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if item is None:
        conn.close()
        return "Product not found", 404

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        message = request.form.get("message", "").strip()

        try:
            quantity = int(request.form.get("quantity", "1"))
        except ValueError:
            quantity = 0

        if not customer_name or not phone or not address or quantity < 1:
            conn.close()
            flash("Please fill all required fields correctly.")
            return redirect(url_for("order", product_id=product_id))

        if quantity > item["quantity"]:
            conn.close()
            flash("Requested quantity is not available.")
            return redirect(url_for("order", product_id=product_id))

        conn.execute("""
            INSERT INTO orders
            (product_id, customer_name, phone, address, quantity, message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (product_id, customer_name, phone, address, quantity, message))
        conn.execute(
            "UPDATE products SET quantity = quantity - ? WHERE id = ?",
            (quantity, product_id)
        )
        conn.commit()
        conn.close()
        return render_template("success.html")

    conn.close()
    return render_template("order.html", product=item)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/admin")
@admin_required
def dashboard():
    conn = get_db()
    products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    orders = conn.execute("""
        SELECT orders.*, products.name AS product_name
        FROM orders
        LEFT JOIN products ON orders.product_id = products.id
        ORDER BY orders.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin/dashboard.html", products=products, orders=orders)


@app.route("/admin/add", methods=["GET", "POST"])
@admin_required
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "Other").strip()

        try:
            price = float(request.form.get("price", "0"))
            quantity = int(request.form.get("quantity", "0"))
        except ValueError:
            flash("Price and quantity must be valid numbers.")
            return redirect(url_for("add_product"))

        if not name or price < 0 or quantity < 0:
            flash("Please enter valid product details.")
            return redirect(url_for("add_product"))

        image = request.files.get("image")
        filename = ""

        if image and image.filename:
            if not allowed_file(image.filename):
                flash("Allowed image formats: JPG, JPEG, PNG, WEBP.")
                return redirect(url_for("add_product"))
            ext = image.filename.rsplit(".", 1)[1].lower()
            filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db()
        conn.execute("""
    INSERT INTO products
    (name, price, description, quantity, image, category)
    VALUES (?, ?, ?, ?, ?, ?)
""", (name, price, description, quantity, filename, category))
        conn.commit()
        conn.close()
        flash("Product added successfully.")
        return redirect(url_for("dashboard"))

    return render_template("admin/add_product.html")


@app.route("/admin/edit/<int:product_id>", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    conn = get_db()
    item = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    if item is None:
        conn.close()
        return "Product not found", 404

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        try:
            price = float(request.form.get("price", "0"))
            quantity = int(request.form.get("quantity", "0"))
        except ValueError:
            conn.close()
            flash("Price and quantity must be valid numbers.")
            return redirect(url_for("edit_product", product_id=product_id))

        filename = item["image"]
        image = request.files.get("image")

        if image and image.filename:
            if not allowed_file(image.filename):
                conn.close()
                flash("Allowed image formats: JPG, JPEG, PNG, WEBP.")
                return redirect(url_for("edit_product", product_id=product_id))

            if filename:
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                if os.path.exists(old_path):
                    os.remove(old_path)

            ext = image.filename.rsplit(".", 1)[1].lower()
            filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn.execute("""
            UPDATE products
            SET name = ?, price = ?, description = ?, quantity = ?, image = ?
            WHERE id = ?
        """, (name, price, description, quantity, filename, product_id))
        conn.commit()
        conn.close()
        flash("Product updated successfully.")
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("admin/edit_product.html", product=item)


@app.route("/admin/delete/<int:product_id>", methods=["POST"])
@admin_required
def delete_product(product_id):
    conn = get_db()
    item = conn.execute("SELECT image FROM products WHERE id = ?", (product_id,)).fetchone()
    if item:
        if item["image"]:
            path = os.path.join(app.config["UPLOAD_FOLDER"], item["image"])
            if os.path.exists(path):
                os.remove(path)
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
    conn.close()
    flash("Product deleted.")
    return redirect(url_for("dashboard"))


@app.route("/admin/order/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order(order_id):
    status = request.form.get("status", "")
    allowed = {"Pending", "Processing", "Completed", "Cancelled"}
    if status not in allowed:
        return "Invalid status", 400

    conn = get_db()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    init_db()
    import os
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
