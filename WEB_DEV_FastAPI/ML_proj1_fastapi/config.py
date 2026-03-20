from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

password=12345678
#url=postgresql://user:password@db_host:port/db_name
db_url=f"postgresql://root:{password}@postgres_db_ml1:5432/ml_fastapi"

engine=create_engine(db_url)
session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
