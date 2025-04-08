import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create database base class
class Base(DeclarativeBase):
    pass

# Initialize Flask-SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure PostgreSQL database
database_url = os.environ.get("DATABASE_URL")
if database_url:
    logger.info("Using PostgreSQL database")
else:
    logger.warning("DATABASE_URL not found, falling back to SQLite")
    database_url = "sqlite:///hotel.db"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# Import routes after app is created to avoid circular imports
with app.app_context():
    # Import models
    import models
    
    # Create database tables
    logger.info("Creating database tables...")
    db.create_all()
    logger.info("Database tables created successfully")
    
    # Import routes after models to avoid circular imports
    from routes import *
    
    try:
        # Check if sample data needs to be created (if tables are empty)
        from models import Room
        if Room.query.count() == 0:
            # Add sample room data
            logger.info("Adding sample room data...")
            sample_rooms = [
                Room(room_number="101", room_type="Standard", price_per_night=500, is_available=True),
                Room(room_number="102", room_type="Standard", price_per_night=500, is_available=True),
                Room(room_number="201", room_type="Deluxe", price_per_night=1200, is_available=True),
                Room(room_number="301", room_type="Suite", price_per_night=1800, is_available=True)
            ]
            db.session.add_all(sample_rooms)
            db.session.commit()
            logger.info("Sample room data added successfully")
    except Exception as e:
        logger.error(f"Error adding sample data: {str(e)}")
        db.session.rollback()
