from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# very basic Pydantic model (request / response schema)
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float

# in-memory store for demo
_items = {}
_next_id = 1

@app.get("/")
def read_root():
    return {"message": "hello — FastAPI basics"}

@app.get("/items/{item_id}", response_model=Item)
def read_item(item_id: int):
    item = _items.get(item_id)
    if not item:
        return {"error": "not found"}
    return item

@app.post("/items/", response_model=Item)
def create_item(item: Item):
    global _next_id
    item.id = _next_id
    _items[_next_id] = item
    _next_id += 1
    return item