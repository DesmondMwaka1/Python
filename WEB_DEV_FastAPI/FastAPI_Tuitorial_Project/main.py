from fastapi import FastAPI, Depends
from models import Product
from config import session, engine
import database_model
from sqlalchemy.orm import Session

app= FastAPI()

#inmemory data
products=[
    Product(id=1,name="Apples",description="Juicy ones",price=45,quantity=200),
    Product(id=2,name="Mangoes",description="Ripe ones",price=95,quantity=500),
    Product(id=3,name="Oranges",description="Mediterranean ones",price=35,quantity=2100)
]

#creates the database tables if they don't exist
database_model.Base.metadata.create_all(bind=engine)

#saving infile data to db
def init_db():
    db=session()
    count=db.query(database_model.Product).count()
    
    if count==0:
        for product in products:
            db.add(database_model.Product(**product.model_dump()))
        db.commit()
init_db()

#dependency
def get_db():
    db=session()
    try:
        yield db
    finally:
        db.close()
        
@app.get('/')
def greet():
    return "Holla, Estas bien?"

@app.get('/products')
def get_products(db: Session = Depends(get_db)): #dependency injection
    db_prods=db.query(database_model.Product).all()
    return db_prods

@app.get("/product/{id}")
def get_product(id:int, db: Session = Depends(get_db)):
    db_prod=db.query(database_model.Product).filter(database_model.Product.id==id).first()
    if db_prod:
        return db_prod
    return "Product not found"
    
@app.post("/product")
def add_product(product: Product, db: Session = Depends(get_db)):
    db.add(database_model.Product(**product.model_dump()))
    db.commit()
    return product
    
@app.put("/product")
def update_product(id:int, product:Product, db: Session = Depends(get_db)):
    db_prod=db.query(database_model.Product).filter(database_model.Product.id==id).first()
    if db_prod:
        db_prod.name=product.name
        db_prod.description=product.description
        db_prod.price=product.price
        db_prod.quantity=product.quantity
        db.commit()
        return "Product updated successfully"
    return "Product not found!"

@app.delete("/product")
def delete_product(id:int, db: Session = Depends(get_db)):
    db_prod=db.query(database_model.Product).filter(database_model.Product.id==id).first()
    if db_prod:
        db.delete(db_prod)
        db.commit()
        return "Product deleted successfully"
    else:
        return "Product not found!"


