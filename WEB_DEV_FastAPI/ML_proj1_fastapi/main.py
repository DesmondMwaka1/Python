from fastapi import FastAPI, Depends
from models import User_data_model, Employee_model
from config import session, engine
import db_models
from db_models import User_data, Employee
from sqlalchemy.orm import Session
from utils import hash_password

app= FastAPI()

#creates the database tables if they do not exist
db_models.Base.metadata.create_all(bind=engine)

def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()
        
@app.get('/')
def home():
    return "Welcome to the ML Project 1 API"

@app.post("/register")
def create_user(user1: User_data_model, db: Session = Depends(get_db)): #pydantic class
    # 1. Hash the password
    hashed_pwd = hash_password(user1.password)
    
    # 2. Create the database model instance with the HASHED password
    new_user = User_data(
        user_name=user1.user_name,
        password=hashed_pwd, # Store the hash, not the plain text!
        height=user1.height,
        age=user1.age
    )
    
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User_data).all()
    return users


@app.get("/user/{id}")
def get_user(id:int, db: Session = Depends(get_db)):
    db_user=db.query(User_data).filter(User_data.id==id).first()
    if db_user:
        return db_user
    return "User not found"

@app.get("/employees")
def get_employees_data(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    return employees

@app.get("/employee/{id}")
def get_employee_data(id:int, db: Session = Depends(get_db)):
    db_emp=db.query(Employee).filter(Employee.id==id).first()
    if db_emp:
        return db_emp
    return "Employee not found"