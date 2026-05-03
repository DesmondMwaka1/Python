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
    profile_photo_url = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)

    # Relationship to track which user triggered which predictions (optional)
    predictions = relationship("Prediction", back_populates="owner")

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    match_date = Column(DateTime)
    home_team = Column(String)
    away_team = Column(String)
    home_team_logo = Column(String, nullable=True)
    away_team_logo = Column(String, nullable=True)
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
    home_team_logo = Column(String, nullable=True)
    away_team_logo = Column(String, nullable=True)
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
    actual_result = Column(String, nullable=True)  # H, D, A or None if not yet played
    model_was_correct = Column(Boolean, nullable=True)  # True/False if match played, None if pending
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class HistoricalMatch(Base):
    __tablename__ = "historical_matches"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    home_team = Column(String)
    away_team = Column(String)
    home_team_logo = Column(String, nullable=True)
    away_team_logo = Column(String, nullable=True)
    fthg = Column(Integer)  # Full Time Home Goals
    ftag = Column(Integer)  # Full Time Away Goals
    ftr = Column(String)    # Full Time Result: H, D, A
    hthg = Column(Integer)  # Half Time Home Goals
    htag = Column(Integer)  # Half Time Away Goals
    htr = Column(String)    # Half Time Result
    hs = Column(Integer)    # Home Shots
    as_ = Column(Integer)   # Away Shots (renamed to avoid keyword)
    hst = Column(Integer)   # Home Shots on Target
    ast = Column(Integer)   # Away Shots on Target
    hc = Column(Integer)    # Home Corners
    ac = Column(Integer)    # Away Corners
    hf = Column(Integer)    # Home Fouls
    af = Column(Integer)    # Away Fouls
    hy = Column(Integer)    # Home Yellow Cards
    ay = Column(Integer)    # Away Yellow Cards
    hr = Column(Integer)    # Home Red Cards
    ar = Column(Integer)    # Away Red Cards 

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

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    type = Column(String, nullable=False)  # e.g., "prediction", "match", "system", "accuracy"
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    data = Column(String)  # JSON string for additional data like match_id, prediction_id, etc.

    # Relationship
    user = relationship("User", back_populates="notifications")

# Add notifications relationship to User
User.notifications = relationship("Notification", back_populates="user")

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
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_photo_url VARCHAR"))
        conn.execute(text("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS user_id INTEGER"))
        conn.execute(text("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS home_team_logo VARCHAR"))
        conn.execute(text("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS away_team_logo VARCHAR"))
        conn.execute(text("ALTER TABLE prediction_history ADD COLUMN IF NOT EXISTS actual_result VARCHAR"))
        conn.execute(text("ALTER TABLE prediction_history ADD COLUMN IF NOT EXISTS model_was_correct BOOLEAN"))
        conn.execute(text("ALTER TABLE prediction_history ADD COLUMN IF NOT EXISTS home_team_logo VARCHAR"))
        conn.execute(text("ALTER TABLE prediction_history ADD COLUMN IF NOT EXISTS away_team_logo VARCHAR"))
        conn.execute(text("ALTER TABLE historical_matches ADD COLUMN IF NOT EXISTS home_team_logo VARCHAR"))
        conn.execute(text("ALTER TABLE historical_matches ADD COLUMN IF NOT EXISTS away_team_logo VARCHAR"))
        conn.commit()