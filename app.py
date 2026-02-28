from dataclasses import fields
import datetime
import os
from wsgiref import validate 
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, create_engine, flask_sqlalchemy
from marshmallow_sqlalchemy import Marshmallow

load_dotenv()
DB_PASSWORD = os.getenv("DB_PASSWORD")

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://root:{DB_PASSWORD}@localhost/ecommerce_api'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)


# Create the following tables in SQLAlchemy:


# Creating User Table
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    address = db.Column(db.String)
    email = db.Column(unique=True)
    

# Creating Order table

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_date: db.Column(db.DateTime, default=datetime.utcnow)



# Creating Product table

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.String)
    price = db.Column(db.Float)


# Creating Order_Product Association Table

class OrderProduct(db.Model):
    __tablename__ = "order_product"
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), primary_key=True)
    
    __table_args__ = (
        UniqueConstraint("order_id", "product_id", name="unique_order_product")
    )
    
    
# Marshmallow Schemas

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
        include_fk = True
        
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

# User CRUD

@app.get("/user")