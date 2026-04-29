-- =============================================================================
-- StockFlow – Database Schema
-- Part 2: Database Design
--
-- Target: PostgreSQL 14+
-- Notation: SQL DDL (runnable directly via psql or Flask-Migrate)
--
-- DESIGN DECISIONS
-- ─────────────────────────────────────────────────────────────────────────────
-- 1. NUMERIC(12,4) for all money columns – avoids IEEE-754 float rounding
--    errors that would corrupt financial calculations.
-- 2. TIMESTAMPTZ everywhere – stores UTC; converts on read per client timezone.
-- 3. Soft deletes via is_active flag – preserves history / audit trails.
-- 4. inventory(product_id, warehouse_id) UNIQUE – enforces one row per
--    product-warehouse pair at the DB level, not just the app layer.
-- 5. inventory_transactions – append-only ledger; never updated or deleted.
--    This gives a full audit trail and enables time-series stockout analysis.
-- 6. product_suppliers many-to-many – a product can have multiple suppliers
--    and a supplier can supply many products.
-- 7. bundle_items self-referencing FK + CHECK(bundle_id <> component_id) –
--    prevents a bundle containing itself (one level; deep cycle detection
--    lives in application logic).
-- 8. SKU unique per company (not globally) – B2B SaaS companies run their
--    own SKU namespaces; global uniqueness would be too restrictive.
--
-- OPEN QUESTIONS FOR PRODUCT TEAM
-- ─────────────────────────────────────────────────────────────────────────────
-- Q1: Is SKU unique globally or per company? (Assumed: per company)
-- Q2: Can inventory go negative (backorders)? (Assumed: no, CHECK qty >= 0)
-- Q3: How is "recent sales activity" defined — last 7 / 30 / 90 days?
-- Q4: Does low_stock_threshold vary per warehouse or just per product?
-- Q5: Multi-currency support needed? (Assumed: no for v1)
-- Q6: Are warehouse-to-warehouse transfers a first-class operation?
-- Q7: How deep can bundle nesting go? (Assumed: 1 level for v1)
-- Q8: Do products have variants (size, colour)? (Out of scope for v1)
-- Q9: Is there a Purchase Order / receiving workflow?
-- Q10: What are data retention requirements for transaction history?
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Core tenant entity
-- -----------------------------------------------------------------------------
CREATE TABLE companies (
    id         SERIAL       PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Users (employees of a company)
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id         SERIAL       PRIMARY KEY,
    company_id INT          NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    email      VARCHAR(255) NOT NULL UNIQUE,
    role       VARCHAR(50)  NOT NULL DEFAULT 'staff',   -- 'admin' | 'manager' | 'staff'
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_users_company ON users(company_id);

-- -----------------------------------------------------------------------------
-- Warehouses owned by a company
-- -----------------------------------------------------------------------------
CREATE TABLE warehouses (
    id         SERIAL       PRIMARY KEY,
    company_id INT          NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name       VARCHAR(255) NOT NULL,
    address    TEXT,
    is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_warehouses_company ON warehouses(company_id);

-- -----------------------------------------------------------------------------
-- Product catalogue  (one row per unique product per company)
-- -----------------------------------------------------------------------------
CREATE TABLE products (
    id                  SERIAL         PRIMARY KEY,
    company_id          INT            NOT NULL REFERENCES companies(id),
    name                VARCHAR(255)   NOT NULL,
    sku                 VARCHAR(100)   NOT NULL,
    description         TEXT           NOT NULL DEFAULT '',
    price               NUMERIC(12, 4) NOT NULL CHECK (price >= 0),
    unit_of_measure     VARCHAR(50)    NOT NULL DEFAULT 'each',
    -- Low-stock threshold: qty below which an alert is raised.
    -- If this should vary per warehouse, move to inventory table (Q4 above).
    low_stock_threshold INT            NOT NULL DEFAULT 10 CHECK (low_stock_threshold >= 0),
    is_bundle           BOOLEAN        NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN        NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, sku)           -- SKU unique within each company tenant
);
CREATE INDEX idx_products_company ON products(company_id);
CREATE INDEX idx_products_sku     ON products(company_id, sku);   -- fast SKU lookups

-- -----------------------------------------------------------------------------
-- Inventory  (current stock levels per product per warehouse)
-- -----------------------------------------------------------------------------
CREATE TABLE inventory (
    id           SERIAL      PRIMARY KEY,
    product_id   INT         NOT NULL REFERENCES products(id)   ON DELETE CASCADE,
    warehouse_id INT         NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    quantity     INT         NOT NULL DEFAULT 0 CHECK (quantity     >= 0),
    -- reserved_qty: stock earmarked for pending orders; not yet shipped.
    -- available stock = quantity − reserved_qty
    reserved_qty INT         NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (product_id, warehouse_id)   -- one row per product-warehouse pair
);
CREATE INDEX idx_inventory_product   ON inventory(product_id);
CREATE INDEX idx_inventory_warehouse ON inventory(warehouse_id);

-- -----------------------------------------------------------------------------
-- Inventory transactions  (append-only audit ledger – never update/delete)
-- -----------------------------------------------------------------------------
CREATE TABLE inventory_transactions (
    id           SERIAL      PRIMARY KEY,
    inventory_id INT         NOT NULL REFERENCES inventory(id),
    -- Positive = stock in (restock, return).  Negative = stock out (sale, loss).
    change_qty   INT         NOT NULL,
    reason       VARCHAR(50) NOT NULL
                             CHECK (reason IN ('sale','restock','adjustment','transfer','return')),
    reference_id INT,        -- optional FK to orders / purchase orders (polymorphic)
    notes        TEXT,
    created_by   INT         REFERENCES users(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_inv_tx_inventory   ON inventory_transactions(inventory_id);
CREATE INDEX idx_inv_tx_created     ON inventory_transactions(created_at);   -- range queries
CREATE INDEX idx_inv_tx_reason_date ON inventory_transactions(reason, created_at);

-- -----------------------------------------------------------------------------
-- Suppliers
-- -----------------------------------------------------------------------------
CREATE TABLE suppliers (
    id             SERIAL       PRIMARY KEY,
    company_id     INT          NOT NULL REFERENCES companies(id),
    name           VARCHAR(255) NOT NULL,
    contact_email  VARCHAR(255),
    contact_phone  VARCHAR(50),
    lead_time_days INT          CHECK (lead_time_days > 0),   -- avg days PO→delivery
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_suppliers_company ON suppliers(company_id);

-- -----------------------------------------------------------------------------
-- Product ↔ Supplier  (many-to-many with extra data)
-- -----------------------------------------------------------------------------
CREATE TABLE product_suppliers (
    id           SERIAL         PRIMARY KEY,
    product_id   INT            NOT NULL REFERENCES products(id)  ON DELETE CASCADE,
    supplier_id  INT            NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    supplier_sku VARCHAR(100),              -- supplier's own part number
    unit_cost    NUMERIC(12, 4) CHECK (unit_cost >= 0),
    is_preferred BOOLEAN        NOT NULL DEFAULT FALSE,
    UNIQUE (product_id, supplier_id)
);
CREATE INDEX idx_ps_product  ON product_suppliers(product_id);
CREATE INDEX idx_ps_supplier ON product_suppliers(supplier_id);

-- Partial index: fast lookup of the preferred supplier per product
CREATE INDEX idx_ps_preferred ON product_suppliers(product_id)
    WHERE is_preferred = TRUE;

-- -----------------------------------------------------------------------------
-- Bundle composition  (which products make up a bundle)
-- -----------------------------------------------------------------------------
CREATE TABLE bundle_items (
    id           SERIAL  PRIMARY KEY,
    bundle_id    INT     NOT NULL REFERENCES products(id),
    component_id INT     NOT NULL REFERENCES products(id),
    quantity     INT     NOT NULL DEFAULT 1 CHECK (quantity > 0),
    UNIQUE (bundle_id, component_id),
    CHECK  (bundle_id <> component_id)   -- a bundle cannot contain itself
);
CREATE INDEX idx_bundle_items_bundle    ON bundle_items(bundle_id);
CREATE INDEX idx_bundle_items_component ON bundle_items(component_id);