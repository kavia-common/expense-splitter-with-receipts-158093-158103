import os
from flask import Flask
from flask_cors import CORS
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy

# Initialize extensions at module level to avoid circular imports
db = SQLAlchemy()

# Create the Flask app
app = Flask(__name__)
app.url_map.strict_slashes = False

# CORS configuration - allow all origins for simplicity; tighten in production as needed
CORS(app, resources={r"/*": {"origins": "*"}})

# API and Swagger/OpenAPI configuration
app.config["API_TITLE"] = "Expense Splitter API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config["OPENAPI_URL_PREFIX"] = "/docs"
app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

# Base directory for this backend project
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Database configuration
# Use DATABASE_URL if provided; otherwise default to a local SQLite file
default_sqlite_path = os.path.join(BASE_DIR, "expense_splitter.db")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", f"sqlite:///{default_sqlite_path}")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# File storage configuration for receipts
# Use UPLOAD_FOLDER if provided; otherwise default to a "receipts" folder under backend root
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", os.path.join(BASE_DIR, "receipts"))
# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize API
api = Api(app)

# Initialize SQLAlchemy
db.init_app(app)

# Import routes after api is created to ensure registration works
from .routes.health import blp as health_blp  # noqa: E402

api.register_blueprint(health_blp)

# Import models and create tables on startup
with app.app_context():
    # Import models to register them with SQLAlchemy's metadata
    from . import models  # noqa: F401
    # Create database tables if they do not already exist
    db.create_all()
