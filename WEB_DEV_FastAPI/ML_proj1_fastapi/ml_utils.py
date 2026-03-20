import torch
import torch.nn as nn
import joblib
import numpy as np
from fastapi import HTTPException

# Re-define the class structure (PyTorch needs this to map the weights)
class Salary_NN(nn.Module):
    def __init__(self):
        super(Salary_NN, self).__init__()
        self.hidden = nn.Linear(1, 4)
        self.output = nn.Linear(4, 1)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.relu(self.hidden(x))
        x = self.output(x)
        return x

# Global variables to hold the loaded model/scalers
model = Salary_NN()
model.load_state_dict(torch.load("salary_model.pth"))
model.eval()

scaler_x = joblib.load("scaler_x.pkl")
scaler_y = joblib.load("scaler_y.pkl")

def predict_salary(years_experience: float):
    # 1. Validation: Experience can't be negative
    if years_experience < 0:
        raise HTTPException(status_code=400, detail="Experience cannot be negative")
    
    # 2. Logic for extreme outliers (Optional)
    if years_experience > 50:
         raise HTTPException(status_code=400, detail="Experience exceeds realistic parameters for this model")

    try:
        # Scale input
        scaled_input = scaler_x.transform([[years_experience]])
        input_tensor = torch.tensor(scaled_input, dtype=torch.float32)
        
        # Predict
        with torch.no_grad():
            prediction_scaled = model(input_tensor)
            
        # Inverse scale back to dollars
        actual_salary = scaler_y.inverse_transform(prediction_scaled.numpy())
        
        # Ensure the AI doesn't return a negative salary (ReLU safety)
        result = float(actual_salary[0][0])
        return max(0, result) 

    except Exception as e:
        # If the file is missing or tensor math fails, don't crash the whole app
        print(f"ML Prediction Error: {e}")
        raise HTTPException(status_code=500, detail="Internal ML Model Error")
        