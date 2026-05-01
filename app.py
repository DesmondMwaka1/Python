import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

# 1. Initialize FastAPI
# We set docs_url to '/' so that the Swagger UI is the first thing you see
app = FastAPI(
    title="Hugging Face API",
    description="Accessing Swagger UI on HF Spaces",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 2. CORS is CRITICAL for HF Spaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Redirect root to /docs to avoid 404
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

# 4. A sample endpoint so Swagger has something to show
@app.get("/hello")
def say_hello(name: str = "World"):
    return {"message": f"Hello {name} from Hugging Face!"}

if __name__ == "__main__":
    # 5. PORT 7860 is MANDATORY. Hugging Face only listens on 7860.
    # 0.0.0.0 is also mandatory to be accessible outside the container.
    uvicorn.run(app, host="0.0.0.0", port=7860)