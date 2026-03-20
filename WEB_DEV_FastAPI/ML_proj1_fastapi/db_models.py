from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base=declarative_base()

class User_data(Base):
    __tablename__="User_data"
    id=Column(Integer, primary_key=True, index=True)
    user_name=Column(String, unique=True, index=True)
    password=Column(String, nullable=False)
    height=Column(Float, nullable=False)
    age=Column(Integer, nullable=False)
    
class Employee(Base):
    __tablename__ = "Employee"
    id = Column(Integer, primary_key=True, index=True)
    salary = Column(Float, nullable=False)