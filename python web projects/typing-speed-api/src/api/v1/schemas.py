from pydantic import BaseModel

class TypingTestResult(BaseModel):
    id: str
    wpm: float