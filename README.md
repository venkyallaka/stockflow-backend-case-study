# stockflow-backend-case-study
# StockFlow – Inventory Management API (B2B SaaS)

A backend case study solution for **StockFlow**, a multi-warehouse inventory management platform for small businesses.

---

## Project Structure

```
stockflow/
├── part1/              # Code Review & Bug Fix
│   └── create_product.py
├── part2/              # Database Schema Design
│   └── schema.sql
├── part3/              # Low-Stock Alerts API
│   └── low_stock_alerts.py
├── app.py              # Flask app entry point (wires all blueprints)
├── models.py           # SQLAlchemy models
├── auth.py             # Auth decorator
├── requirements.txt
└── README.md
```

---

## Setup & Run

### 1. Clone & install dependencies

```bash
git clone <your-repo-url>
cd stockflow
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 3. Initialise the database

```bash
flask db upgrade          # runs migrations from schema.sql
# or directly:
psql -U postgres -d stockflow -f part2/schema.sql
```

### 4. Run the development server

```bash
flask run
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/products` | Create a product + initial inventory |
| `GET`  | `/api/companies/<id>/alerts/low-stock` | Get low-stock alerts for a company |

---

## Key Design Decisions

- **Atomic transactions** – Product + Inventory creation uses a single `db.session.commit()` via `flush()` to prevent orphan records.
- **CTE-based low-stock query** – One SQL round-trip regardless of product/warehouse count; avoids N+1.
- **`reserved_qty` tracking** – Available stock = `quantity − reserved_qty`, so pending orders don't cause false restock triggers.
- **Bundles excluded from alerts** – Bundles have no physical stock; component products are what need reordering.
- **Preferred supplier fallback** – Uses `DISTINCT ON` to select the preferred supplier, falling back to the earliest-added one.

---

## Assumptions Made

1. "Recent sales activity" = at least one `sale` transaction within the last **30 days**.
2. SKUs are unique **per company** (not globally across all companies).
3. Low-stock threshold is a single value stored on each product (not per-warehouse). *(Flagged as a question for the product team.)*
4. Inventory cannot go negative — backorders are out of scope for v1.
5. Authentication uses a JWT bearer token; `g.current_user` is populated by middleware.
6. PostgreSQL is the target database (uses `DISTINCT ON`, `NUMERIC`, `TIMESTAMPTZ`).