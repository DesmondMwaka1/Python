from fastapi import FastAPI, Depends, HTTPException
from models import User_data_model, UserResponse, Employee_model, EmployeeResponse
from config import session, engine
import db_models
from db_models import User_data, Employee
from sqlalchemy.orm import Session
from utils import hash_password
from ml_utils import predict_salary

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

@app.get("/users", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User_data).all()
    if not users:
        raise HTTPException(status_code=404, detail="Users not found")
    return users


@app.get("/user/{id}", response_model=UserResponse)
def get_user(id:int, db: Session = Depends(get_db)):
    db_user = db.query(User_data).filter(User_data.id == id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.post("/employee_years")
def send_years_exp(employee: Employee_model, db: Session = Depends(get_db)):
    # 1. Use your AI model to get the prediction
    pred_salary = predict_salary(employee.years_experience)

    pred_salary = round(pred_salary, 2)

    # 2. Save to Database
    new_employee = Employee(
        years_experience=employee.years_experience,
        salary=pred_salary # Saving the AI result
    )
    
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return {"message": "Employee created successfully"}

@app.get("/employees_salary", response_model=list[EmployeeResponse])
def get_employees_data(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    if not employees:
        raise HTTPException(status_code=404, detail="Employees not found")
    return employees

@app.get("/employee_salary/{id}", response_model=EmployeeResponse)
def get_employee_data(id:int, db: Session = Depends(get_db)):
    db_emp = db.query(Employee).filter(Employee.id == id).first()
    if not db_emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return db_emp