#!/usr/bin/env python3
"""
Database migration script to add new columns to prediction_history table.
Run this once to update the schema.
"""
import os
from sqlalchemy import create_engine, text
from database import Base
import models

DATABASE_URL = os.getenv("DATABASE_URL")

def migrate_db():
    """Add missing columns to prediction_history table."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Add actual_result column if it doesn't exist
            conn.execute(text("""
                ALTER TABLE prediction_history 
                ADD COLUMN IF NOT EXISTS actual_result VARCHAR;
            """))
            print("✓ Added actual_result column")
        except Exception as e:
            print(f"✗ Error adding actual_result: {e}")
        
        try:
            # Add model_was_correct column if it doesn't exist
            conn.execute(text("""
                ALTER TABLE prediction_history 
                ADD COLUMN IF NOT EXISTS model_was_correct BOOLEAN;
            """))
            print("✓ Added model_was_correct column")
        except Exception as e:
            print(f"✗ Error adding model_was_correct: {e}")
        
        conn.commit()
    
    print("\n✓ Database migration complete!")

if __name__ == "__main__":
    migrate_db()
