import time
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TypingTestResult(BaseModel):
    id: str
    wpm: float

@app.post("/start_typing_test", response_model=TypingTestResult)
def start_typing_test():
    input("Press Enter to start the typing test...\n")
    start= time.time()
    text= input("Type the following text as fast as you can:\n\n")
    end= time.time()
    duration= end- start

    word_count = len(text.split())
    print(f"{word_count} words typed in {duration:.2f} seconds.")
    wpm= (word_count/ duration) 
    print(f"Your typing speed is {wpm} words per second.")

if __name__ == "__main__":
    start_typing_test() 