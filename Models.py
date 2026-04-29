"""
models.py – SQLAlchemy ORM models for StockFlow.

These map directly to the tables defined in part2/schema.sql.
"""

from datetime import datetime
from . import db   # imported from app.py


class Company(db.Model):
    __tablename__ = "companies"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    warehouses = db.relationship("Warehouse", back_populates="company")
    products   = db.relationship("Product",   back_populates="company")
    suppliers  = db.relationship("Supplier",  back_populates="company")
    users      = db.relationship("User",      back_populates="company")


class Warehouse(db.Model):
    __tablename__ = "warehouses"

    id         = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name       = db.Column(db.String(255), nullable=False)
    address    = db.Column(db.Text)
    is_active  = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    company    = db.relationship("Company",   back_populates="warehouses")
    inventory  = db.relationship("Inventory", back_populates="warehouse")


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        db.UniqueConstraint("company_id", "sku", name="uq_products_company_sku"),
    )

    id                  = db.Column(db.Integer, primary_key=True)
    company_id          = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    name                = db.Column(db.String(255), nullable=False)
    sku                 = db.Column(db.String(100), nullable=False)
    description         = db.Column(db.Text, default="")
    price               = db.Column(db.Numeric(12, 4), nullable=False)
    unit_of_measure     = db.Column(db.String(50), nullable=False, default="each")
    low_stock_threshold = db.Column(db.Integer, nullable=False, default=10)
    is_bundle           = db.Column(db.Boolean, nullable=False, default=False)
    is_active           = db.Column(db.Boolean, nullable=False, default=True)
    created_at          = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at          = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    company            = db.relationship("Company",         back_populates="products")
    inventory          = db.relationship("Inventory",       back_populates="product")
    product_suppliers  = db.relationship("ProductSupplier", back_populates="product")
    bundle_items       = db.relationship("BundleItem",
                                         foreign_keys="BundleItem.bundle_id",
                                         back_populates="bundle")


class Inventory(db.Model):
    __tablename__ = "inventory"
    __table_args__ = (
        db.UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    product_id   = db.Column(db.Integer, db.ForeignKey("products.id",   ondelete="CASCADE"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    quantity     = db.Column(db.Integer, nullable=False, default=0)
    reserved_qty = db.Column(db.Integer, nullable=False, default=0)
    updated_at   = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    product      = db.relationship("Warehouse", back_populates="inventory")
    warehouse    = db.relationship("Product",   back_populates="inventory")
    transactions = db.relationship("InventoryTransaction", back_populates="inventory")


class InventoryTransaction(db.Model):
    __tablename__ = "inventory_transactions"

    id           = db.Column(db.Integer, primary_key=True)
    inventory_id = db.Column(db.Integer, db.ForeignKey("inventory.id"), nullable=False)
    change_qty   = db.Column(db.Integer, nullable=False)           # negative = stock out
    reason       = db.Column(db.String(50), nullable=False)        # 'sale','restock','adjustment','transfer'
    reference_id = db.Column(db.Integer)                           # FK to orders/POs (polymorphic)
    notes        = db.Column(db.Text)
    created_by   = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at   = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    inventory    = db.relationship("Inventory", back_populates="transactions")


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id             = db.Column(db.Integer, primary_key=True)
    company_id     = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    name           = db.Column(db.String(255), nullable=False)
    contact_email  = db.Column(db.String(255))
    contact_phone  = db.Column(db.String(50))
    lead_time_days = db.Column(db.Integer)
    is_active      = db.Column(db.Boolean, nullable=False, default=True)
    created_at     = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    company           = db.relationship("Company",         back_populates="suppliers")
    product_suppliers = db.relationship("ProductSupplier", back_populates="supplier")


class ProductSupplier(db.Model):
    __tablename__ = "product_suppliers"
    __table_args__ = (
        db.UniqueConstraint("product_id", "supplier_id", name="uq_product_supplier"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    product_id   = db.Column(db.Integer, db.ForeignKey("products.id",  ondelete="CASCADE"), nullable=False)
    supplier_id  = db.Column(db.Integer, db.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    supplier_sku = db.Column(db.String(100))
    unit_cost    = db.Column(db.Numeric(12, 4))
    is_preferred = db.Column(db.Boolean, nullable=False, default=False)

    product  = db.relationship("Product",  back_populates="product_suppliers")
    supplier = db.relationship("Supplier", back_populates="product_suppliers")


class BundleItem(db.Model):
    __tablename__ = "bundle_items"
    __table_args__ = (
        db.UniqueConstraint("bundle_id", "component_id", name="uq_bundle_component"),
        db.CheckConstraint("bundle_id <> component_id", name="ck_no_self_bundle"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    bundle_id    = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    component_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity     = db.Column(db.Integer, nullable=False, default=1)

    bundle    = db.relationship("Product", foreign_keys=[bundle_id],    back_populates="bundle_items")
    component = db.relationship("Product", foreign_keys=[component_id])


class User(db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    email      = db.Column(db.String(255), nullable=False, unique=True)
    role       = db.Column(db.String(50), nullable=False, default="staff")
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    company = db.relationship("Company", back_populates="users")