from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_admin = Column(Boolean, default=False)

    # Relationship to track which user triggered which predictions (optional)
    predictions = relationship("Prediction", back_populates="owner")

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    match_date = Column(DateTime)
    home_team = Column(String)
    away_team = Column(String)
    home_team_id = Column(Integer)
    away_team_id = Column(Integer)
    
    # Odds
    avg_h = Column(Float)
    avg_d = Column(Float)
    avg_a = Column(Float)
    
    # Tactical Insights
    h_attacking = Column(Float)
    h_defending = Column(Float)
    h_volatility = Column(Float)
    h_efficiency = Column(Float)
    
    a_attacking = Column(Float)
    a_defending = Column(Float)
    a_volatility = Column(Float)
    a_efficiency = Column(Float)
    
    # Outcomes
    prob_home = Column(Float)
    prob_draw = Column(Float)
    prob_away = Column(Float)
    outcome = Column(String)
    confidence = Column(Float)

    # Link prediction to the user who ran it
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="predictions")

class PredictionHistory(Base):
    __tablename__ = "prediction_history"

    id = Column(Integer, primary_key=True, index=True)
    match_date = Column(DateTime)
    home_team = Column(String)
    away_team = Column(String)
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
    outcome = Column(String)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    action = Column(String, index=True)
    ip_address = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String, index=True)  # INFO, WARNING, ERROR, DEBUG
    source = Column(String, index=True)  # e.g., "HEARTBEAT", "STARTUP", "SCHEDULER"
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

# DB Connection Setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

    # Handle incremental schema updates for existing databases.
    # This avoids startup failure when the database was created before schema changes.
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS user_id INTEGER"))
        conn.commit()