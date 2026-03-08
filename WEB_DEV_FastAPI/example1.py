from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import uuid

app = FastAPI()

# CRITICAL: This allows your browser to talk to your local server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, DELETE, etc.)
    allow_headers=["*"],
)

class Task(BaseModel):
    id: Optional[str] = None
    title: str
    completed: bool = False

# In-memory database for testing
tasks_db = []

@app.get("/tasks", response_model=List[Task])
async def get_tasks():
    return tasks_db

@app.post("/tasks", response_model=Task)
async def create_task(task: Task):
    task.id = str(uuid.uuid4())
    tasks_db.append(task)
    return task

@app.patch("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: Task):
    for task in tasks_db:
        if task.id == task_id:
            task.completed = task_update.completed
            return task
    return None

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    global tasks_db
    tasks_db = [t for t in tasks_db if t.id != task_id]
    return {"message": "Deleted successfully"}