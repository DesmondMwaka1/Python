from pydantic import BaseModel
import uuid

class TypingTestResult(BaseModel):
    id: str = str(uuid.uuid4())
    wpm: float