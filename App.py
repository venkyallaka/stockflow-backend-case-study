"""
app.py – Flask application factory for StockFlow.

Registers all blueprints and initialises extensions.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"]        = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"]                     = os.getenv("SECRET_KEY", "dev-secret")

    db.init_app(app)

    # Register blueprints
    from part1.create_product    import products_bp
    from part3.low_stock_alerts  import alerts_bp

    app.register_blueprint(products_bp)
    app.register_blueprint(alerts_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)