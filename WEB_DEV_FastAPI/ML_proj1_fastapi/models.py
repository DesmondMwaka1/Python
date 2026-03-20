from pydantic import BaseModel, ConfigDict, field_serializer

class User_data_model(BaseModel):
    user_name: str
    password: str 
    height: float
    age: int

# This is what the API sends BACK (NO password)
class UserResponse(BaseModel):
    id: int
    user_name: str
    height: float
    age: int

    # This allows Pydantic to read SQLAlchemy objects automatically
    model_config = ConfigDict(from_attributes=True)
class Employee_model(BaseModel):
    years_experience: float
    salary: float
    
class EmployeeResponse(BaseModel):
    id: int
    years_experience: float
    salary: float
    
    # This function formats the number into a currency string
    # : , . 2 f  means: Add commas, 2 decimal places, and make it a float string
    @field_serializer('salary')
    def serialize_salary(self, salary: float, _info):
        return f"${salary:,.2f}"

    model_config = ConfigDict(from_attributes=True)
    
