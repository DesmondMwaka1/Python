from fastapi import FastAPI
from models import Product
from config import session, engine
import database_model

app= FastAPI()

products=[
    Product(id=1,name="Apples",description="Juicy ones",price=45,quantity=200),
    Product(id=2,name="Mangoes",description="Ripe ones",price=95,quantity=500),
    Product(id=3,name="Oranges",description="Mediterranean ones",price=35,quantity=2100)
]

database_model.Base.metadata.create_all(bind=engine)

def init_db():
    db=session()
    count=db.query(database_model.Product).count
    
    if count==0:
        for product in products:
            db.add(database_model.Product(**product.model_dump))
        db.commit()
init_db()

@app.get('/')
def greet():
    return "Holla, Estas bien?"

@app.get('/products')
def get_products():
    # db=session()
    # db.query()
    return products

@app.get("/product/{id}")
def get_product(id:int):
    for product in products:
        if product.id == id:
            return product
    return "Product not found"
    
@app.post("/product")
def add_product(product: Product):
    products.append(product)
    
@app.put("/product")
def update_product(id:int, product:Product):
    for i in range(len(products)):
        if products[i].id==id:
            products[i]=product
            return "Product updated successfully"
    return "Product not found!"

@app.delete("/product")
def delete_product(id:int):
    for i in range(len(products)):
        if products[i].id==id:
            del products[i]
            return "Product deleted successfully"
    return "Product not found!"

