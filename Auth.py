"""
auth.py – Authentication middleware for StockFlow.

In production this would validate a signed JWT. For this case study,
the decorator pattern is shown so reviewers can see the security model clearly.
"""

from functools import wraps
from flask import request, jsonify, g


def require_auth(f):
    """
    Validates the Bearer token on each request and populates flask.g.current_user.

    In production: decode + verify JWT, look up user in DB, attach to g.
    Here we stub it so the rest of the code can be reviewed as-is.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized – missing or malformed token"}), 401

        token = auth_header.split(" ", 1)[1]

        # --- Stub: replace with real JWT decode in production ---
        # e.g. payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        # g.current_user = User.query.get(payload["sub"])

        if token == "invalid":
            return jsonify({"error": "Unauthorized – invalid token"}), 401

        # For review purposes, attach a mock user
        class _MockUser:
            id         = 1
            company_id = 1
            role       = "admin"

        g.current_user = _MockUser()
        return f(*args, **kwargs)

    return decorated