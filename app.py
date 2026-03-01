import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import fields, validate
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import IntegrityError

load_dotenv()
DB_PASSWORD = os.getenv("DB_PASSWORD")

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+mysqlconnector://root:{DB_PASSWORD}@localhost/ecommerce_api"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)

# -------------------------
# MODELS + RELATIONSHIPS
# -------------------------

# Association table (prevents duplicates via composite PK + UniqueConstraint)
class OrderProduct(db.Model):
    __tablename__ = "order_product"

    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), primary_key=True)

    __table_args__ = (
        UniqueConstraint("order_id", "product_id", name="unique_order_product"),
    )


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)

    # One user -> many orders
    orders = db.relationship("Order", back_populates="user", cascade="all, delete-orphan")


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # FK: many orders belong to one user
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", back_populates="orders")

    # Many orders <-> many products
    products = db.relationship(
        "Product",
        secondary="order_product",
        back_populates="orders",
    )


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)

    orders = db.relationship(
        "Order",
        secondary="order_product",
        back_populates="products",
    )


# -------------------------
# SCHEMAS (Marshmallow)
# -------------------------

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True

    name = fields.String(required=True, validate=validate.Length(min=1))
    address = fields.String(required=True, validate=validate.Length(min=1))
    email = fields.Email(required=True)


class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        load_instance = True
        include_fk = True  # exposes user_id

    # optional: validate user_id on create
    user_id = fields.Integer(required=True)


class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        load_instance = True

    product_name = fields.String(required=True, validate=validate.Length(min=1))
    price = fields.Float(required=True, validate=validate.Range(min=0))


user_schema = UserSchema()
users_schema = UserSchema(many=True)

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)


with app.app_context():
    db.create_all()


# -------------------------
# HELPERS
# -------------------------

def not_found(resource_name):
    return jsonify({"error": f"{resource_name} not found"}), 404


# -------------------------
# USER CRUD
# -------------------------

@app.get("/users")
def get_users():
    users = User.query.all()
    return jsonify(users_schema.dump(users)), 200


@app.get("/users/<int:user_id>")
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return not_found("User")
    return jsonify(user_schema.dump(user)), 200


@app.post("/users")
def create_user():
    data = request.get_json() or {}
    user = user_schema.load(data)

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Email must be unique"}), 409

    return jsonify(user_schema.dump(user)), 201


@app.put("/users/<int:user_id>")
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return not_found("User")

    data = request.get_json() or {}
    updated = user_schema.load(data, instance=user, partial=True)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Email must be unique"}), 409

    return jsonify(user_schema.dump(updated)), 200


@app.delete("/users/<int:user_id>")
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return not_found("User")

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"}), 200


# -------------------------
# PRODUCT CRUD
# -------------------------

@app.get("/products")
def get_products():
    products = Product.query.all()
    return jsonify(products_schema.dump(products)), 200


@app.get("/products/<int:product_id>")
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return not_found("Product")
    return jsonify(product_schema.dump(product)), 200


@app.post("/products")
def create_product():
    data = request.get_json() or {}
    product = product_schema.load(data)
    db.session.add(product)
    db.session.commit()
    return jsonify(product_schema.dump(product)), 201


@app.put("/products/<int:product_id>")
def update_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return not_found("Product")

    data = request.get_json() or {}
    updated = product_schema.load(data, instance=product, partial=True)
    db.session.commit()
    return jsonify(product_schema.dump(updated)), 200


@app.delete("/products/<int:product_id>")
def delete_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return not_found("Product")

    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"}), 200


# -------------------------
# ORDER ENDPOINTS
# -------------------------

@app.post("/orders")
def create_order():
    data = request.get_json() or {}

    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    user = User.query.get(user_id)
    if not user:
        return not_found("User")

    order_date = data.get("order_date")
    if order_date:
        # Expect ISO format e.g. "2026-02-28T15:30:00"
        try:
            parsed_date = datetime.fromisoformat(order_date)
        except ValueError:
            return jsonify({"error": "order_date must be ISO format"}), 400
        order = Order(user_id=user_id, order_date=parsed_date)
    else:
        order = Order(user_id=user_id)

    db.session.add(order)
    db.session.commit()
    return jsonify(order_schema.dump(order)), 201


@app.put("/orders/<int:order_id>/add_product/<int:product_id>")
def add_product_to_order(order_id, product_id):
    order = Order.query.get(order_id)
    if not order:
        return not_found("Order")

    product = Product.query.get(product_id)
    if not product:
        return not_found("Product")

    if product in order.products:
        return jsonify({"message": "Product already in order"}), 200

    order.products.append(product)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Duplicate product in order"}), 409

    return jsonify({"message": "Product added to order"}), 200


@app.delete("/orders/<int:order_id>/remove_product/<int:product_id>")
def remove_product_from_order(order_id, product_id):
    order = Order.query.get(order_id)
    if not order:
        return not_found("Order")

    product = Product.query.get(product_id)
    if not product:
        return not_found("Product")

    if product not in order.products:
        return jsonify({"message": "Product not in order"}), 200

    order.products.remove(product)
    db.session.commit()
    return jsonify({"message": "Product removed from order"}), 200


@app.get("/orders/user/<int:user_id>")
def get_orders_for_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return not_found("User")

    orders = Order.query.filter_by(user_id=user_id).all()
    return jsonify(orders_schema.dump(orders)), 200


@app.get("/orders/<int:order_id>/products")
def get_products_for_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return not_found("Order")
    return jsonify(products_schema.dump(order.products)), 200


if __name__ == "__main__":
    app.run(debug=True)