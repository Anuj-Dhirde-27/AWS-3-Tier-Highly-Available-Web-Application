from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from decimal import Decimal
import os

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    orders = db.relationship("Order", backref="user", lazy=True)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="PLACED")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    items = db.relationship(
        "OrderItem",
        backref="order",
        lazy=True,
        cascade="all, delete-orphan",
    )


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    product = db.relationship("Product")


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def cart_items():
    cart = session.get("cart", {})
    result = []
    total = Decimal("0.00")

    for product_id, quantity in cart.items():
        product = db.session.get(Product, int(product_id))
        if product:
            subtotal = product.price * quantity
            result.append(
                {
                    "product": product,
                    "quantity": quantity,
                    "subtotal": subtotal,
                }
            )
            total += subtotal

    return result, total


@app.route("/")
def index():
    products = Product.query.order_by(Product.id).all()
    return render_template("index.html", products=products, user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = User.query.filter(db.func.lower(User.email) == email).first()

        if user and user.password_hash == password:
            session["user_id"] = user.id
            flash("Login successful.", "success")
            return redirect(url_for("index"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html", user=current_user())


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/product/<int:product_id>")
def product(product_id):
    item = db.session.get(Product, product_id)
    if not item:
        return "Product not found", 404
    return render_template("product.html", product=item, user=current_user())


@app.route("/cart")
def cart():
    items, total = cart_items()
    return render_template("cart.html", items=items, total=total, user=current_user())


@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return "Product not found", 404

    try:
        quantity = int(request.form.get("quantity", 1))
    except ValueError:
        quantity = 1

    if quantity < 1:
        quantity = 1

    cart = session.get("cart", {})
    key = str(product_id)
    current_quantity = cart.get(key, 0)

    if current_quantity + quantity > product.stock:
        flash("Not enough stock available.", "danger")
        return redirect(url_for("product", product_id=product_id))

    cart[key] = current_quantity + quantity
    session["cart"] = cart
    flash(f"{product.name} added to cart.", "success")
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    cart.pop(str(product_id), None)
    session["cart"] = cart
    flash("Item removed from cart.", "success")
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["POST"])
def checkout():
    user = current_user()
    if not user:
        flash("Please login before checkout.", "danger")
        return redirect(url_for("login"))

    items, total = cart_items()
    if not items:
        flash("Your cart is empty.", "danger")
        return redirect(url_for("cart"))

    try:
        products_to_update = []

        for item in items:
            product = db.session.get(Product, item["product"].id)
            if not product:
                raise ValueError(f"Product {item['product'].id} no longer exists.")

            if item["quantity"] > product.stock:
                flash(f"Insufficient stock for {product.name}.", "danger")
                return redirect(url_for("cart"))

            products_to_update.append((product, item["quantity"]))

        order = Order(user_id=user.id, total=total, status="PLACED")
        db.session.add(order)
        db.session.flush()

        for product, quantity in products_to_update:
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
            )
            db.session.add(order_item)
            product.stock -= quantity

        db.session.commit()
        session["cart"] = {}

        flash(f"Order #{order.id} placed successfully.", "success")
        return redirect(url_for("orders_page"))

    except Exception:
        db.session.rollback()
        app.logger.exception("Checkout failed")
        flash("Checkout failed. Please try again.", "danger")
        return redirect(url_for("cart"))


@app.route("/orders")
def orders_page():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    user_orders = (
        Order.query
        .filter_by(user_id=user.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return render_template("orders.html", orders=user_orders, user=user)


@app.route("/admin")
def admin():
    user = current_user()
    if not user or user.role != "admin":
        return "Forbidden", 403

    products = Product.query.order_by(Product.id).all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin.html", products=products, orders=orders, user=user)


@app.route("/admin/product/<int:product_id>/stock", methods=["POST"])
def update_stock(product_id):
    user = current_user()
    if not user or user.role != "admin":
        return "Forbidden", 403

    product = db.session.get(Product, product_id)
    if not product:
        return "Product not found", 404

    try:
        stock = int(request.form["stock"])
        product.stock = max(0, stock)
        db.session.commit()
        flash("Inventory updated.", "success")
    except ValueError:
        db.session.rollback()
        flash("Invalid stock value.", "danger")

    return redirect(url_for("admin"))


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
