from time import time
import uuid

def start_typing_test(text: str) -> dict:
    start = time()
    # Simulate user typing input
    # In a real application, this would be replaced with actual input handling
    end = time()
    
    duration = end - start
    word_count = len(text.split())
    wpm = word_count / (duration / 60)  # Convert to words per minute

    result = {
        "id": str(uuid.uuid4()),
        "wpm": wpm
    }
    
    return result