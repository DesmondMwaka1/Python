from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

password="COVID-2020"
db_url=f"postgresql://user101:{password}@postgres_db:5432/fastapi_crud"


engine=create_engine(db_url)
session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    