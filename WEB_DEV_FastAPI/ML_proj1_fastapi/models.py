from pydantic import BaseModel

class User_data_model(BaseModel):
    user_name: str
    password: str 
    height: float
    age: int

class Employee_model(BaseModel):
    salary: float