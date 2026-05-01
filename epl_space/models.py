from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
import logging

# Configure logging to see DB issues in logs
logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_admin = Column(Boolean, default=False)
    predictions = relationship("Prediction", back_populates="owner")

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    match_date = Column(DateTime)
    home_team = Column(String(100))
    away_team = Column(String(100))
    home_team_id = Column(Integer)
    away_team_id = Column(Integer)
    avg_h = Column(Float)
    avg_d = Column(Float)
    avg_a = Column(Float)
    h_attacking = Column(Float)
    h_defending = Column(Float)
    h_volatility = Column(Float)
    h_efficiency = Column(Float)
    a_attacking = Column(Float)
    a_defending = Column(Float)
    a_volatility = Column(Float)
    a_efficiency = Column(Float)
    prob_home = Column(Float)
    prob_draw = Column(Float)
    prob_away = Column(Float)
    outcome = Column(String(50))
    confidence = Column(Float)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="predictions")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), index=True)
    action = Column(String(100), index=True)
    ip_address = Column(String(45))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class SystemLog(Base):
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), index=True)
    source = Column(String(100), index=True)
    message = Column(String(1000))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

# --- DB Connection Setup ---
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback for local development if environment variable is missing
if not DATABASE_URL:
    logger.warning("DATABASE_URL not found. Falling back to SQLite.")
    DATABASE_URL = "sqlite:///./sql_app.db"

# Fix for platforms that still provide 'postgres://' instead of 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine logic
engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes the database schema and performs incremental updates."""
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        # Incremental schema updates (only if using Postgres)
        if not DATABASE_URL.startswith("sqlite"):
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE"))
                conn.execute(text("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS user_id INTEGER"))
                conn.commit()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # In production, you might want to re-raise this, 
        # but during debugging we let the app start so we can check logs.
        if os.getenv("STRICT_DB_INIT", "false").lower() == "true":
            raise e