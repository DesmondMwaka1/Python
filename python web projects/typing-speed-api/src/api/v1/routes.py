from fastapi import APIRouter, HTTPException
from src.api.v1.schemas import TypingTestResult
from src.services.typing_test import start_typing_test

router = APIRouter()

@router.post("/start_typing_test", response_model=TypingTestResult)
async def start_typing_test_endpoint():
    try:
        result = start_typing_test()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))