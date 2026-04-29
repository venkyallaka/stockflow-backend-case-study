"""
part1/create_product.py – Corrected product creation endpoint.

═══════════════════════════════════════════════════════════════════
BUGS IN THE ORIGINAL CODE (and their production impact)
═══════════════════════════════════════════════════════════════════

1. NO INPUT VALIDATION
   - `data['name']` raises KeyError if the field is missing.
   - `request.json` returns None for non-JSON bodies → TypeError on
     the first dict access.
   - Impact: unhandled 500s with raw tracebacks exposed to clients.

2. NO SKU UNIQUENESS HANDLING AT APPLICATION LAYER
   - Even if the DB has a UNIQUE constraint, IntegrityError is never
     caught, producing a raw 500 instead of a meaningful 409 Conflict.
   - Impact: clients can't distinguish "SKU taken" from a server crash.

3. TWO SEPARATE db.session.commit() CALLS — NO ATOMICITY
   - If the Inventory insert fails after Product is committed, the DB
     has an orphaned product with no inventory record.
   - Impact: silent data corruption; very hard to detect/repair later.

4. PRICE NOT VALIDATED
   - Price could be a string, negative, or zero with no rejection.
   - Impact: bad data silently stored; downstream billing/reporting
     calculations produce wrong results.

5. initial_quantity NOT VALIDATED (and mandatory despite being optional)
   - No default, no type check, no negativity guard.
   - Impact: KeyError crash or negative stock recorded.

6. NO AUTHENTICATION / AUTHORIZATION
   - Any unauthenticated caller can create products under any warehouse_id.
   - Impact: cross-tenant data pollution; security vulnerability.

7. WRONG HTTP STATUS CODE ON SUCCESS
   - Returns 200 OK instead of 201 Created.
   - Impact: API clients and monitoring tooling that check for 201 will
     treat successful creations as failures.
═══════════════════════════════════════════════════════════════════
"""

from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify, g
from sqlalchemy.exc import IntegrityError
from app import db
from models import Product, Inventory, Warehouse
from auth import require_auth

products_bp = Blueprint("products", __name__)


@products_bp.route("/api/products", methods=["POST"])
@require_auth
def create_product():
    """
    Create a new product and its initial inventory record in a single
    atomic transaction.

    Required body fields : name, sku, price, warehouse_id
    Optional body fields : description, initial_quantity (default 0)

    Returns 201 on success, appropriate 4xx on bad input.
    """

    # ── 1. Parse JSON body ──────────────────────────────────────────
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    # ── 2. Required field presence check ───────────────────────────
    required = ["name", "sku", "price", "warehouse_id"]
    missing  = [f for f in required if f not in data or data[f] is None]
    if missing:
        return jsonify({"error": "Missing required fields", "fields": missing}), 400

    # ── 3. Validate & normalise name / SKU ─────────────────────────
    name = str(data["name"]).strip()
    sku  = str(data["sku"]).strip().upper()   # normalise SKU to uppercase

    if not name:
        return jsonify({"error": "name cannot be blank"}), 400
    if not sku:
        return jsonify({"error": "sku cannot be blank"}), 400

    # ── 4. Validate price (must be a non-negative decimal) ─────────
    try:
        price = Decimal(str(data["price"]))
        if price < 0:
            raise ValueError("Price cannot be negative")
    except (InvalidOperation, ValueError) as exc:
        return jsonify({"error": f"Invalid price: {exc}"}), 400

    # ── 5. Validate initial_quantity (optional, defaults to 0) ─────
    raw_qty = data.get("initial_quantity", 0)
    try:
        initial_quantity = int(raw_qty)
        if initial_quantity < 0:
            raise ValueError("Quantity cannot be negative")
    except (ValueError, TypeError):
        return jsonify({"error": "initial_quantity must be a non-negative integer"}), 400

    # ── 6. Validate warehouse exists (and belongs to this company) ──
    warehouse = Warehouse.query.get(data["warehouse_id"])
    if not warehouse:
        return jsonify({"error": "Warehouse not found"}), 404

    if warehouse.company_id != g.current_user.company_id:
        # Prevent cross-tenant writes
        return jsonify({"error": "Forbidden – warehouse does not belong to your company"}), 403

    # ── 7. Atomic create: Product + Inventory in one transaction ────
    try:
        product = Product(
            company_id  = g.current_user.company_id,
            name        = name,
            sku         = sku,
            price       = price,
            description = str(data.get("description", "")).strip(),
        )
        db.session.add(product)
        db.session.flush()   # assigns product.id WITHOUT committing;
                             # lets us reference it in Inventory below

        inventory = Inventory(
            product_id   = product.id,
            warehouse_id = data["warehouse_id"],
            quantity     = initial_quantity,
            reserved_qty = 0,
        )
        db.session.add(inventory)

        # Single commit – both rows land together or neither does
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "A product with this SKU already exists in your account",
            "sku"  : sku,
        }), 409

    except Exception:
        db.session.rollback()
        # Log full traceback internally; never expose it to the client
        import logging
        logging.getLogger(__name__).exception(
            "Unexpected error creating product sku=%s company=%s", sku, g.current_user.company_id
        )
        return jsonify({"error": "Internal server error"}), 500

    # ── 8. Return 201 Created (not 200) ────────────────────────────
    return jsonify({
        "message"    : "Product created successfully",
        "product_id" : product.id,
        "sku"        : product.sku,
    }), 201