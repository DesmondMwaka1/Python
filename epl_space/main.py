from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, field_validator
import models
import os
import logging
import threading
import time
from collections import defaultdict, deque
from functools import wraps
from threading import Lock
from typing import Generic, TypeVar

# --- PAGINATION ---
T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int
    
    class Config:
        arbitrary_types_allowed = True


# --- CONFIGURATION ---
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

# Security Settings
ALLOWED_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "hotmail.com"]
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# --- IN-MEMORY SECURITY TRACKING ---
failed_attempts = defaultdict(list)
blacklisted_tokens = {}

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# app = FastAPI(title="EPL Prediction API")

app = FastAPI(
    title="EPL Prediction API",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# --- CUSTOM ERROR HANDLING ---
class AppException(HTTPException):
    def __init__(self, status_code: int, error_code: str, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.error_code = error_code

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.detail}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # For standard HTTPExceptions, use a generic error_code
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": "HTTP_ERROR", "message": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    log_system_event("ERROR", "EXCEPTION", f"Unhandled exception: {str(exc)}", None)
    return JSONResponse(
        status_code=500,
        content={"error_code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred. Please try again later."}
    )

# --- RATE LIMITING ---
class SimpleRateLimiter:
    def __init__(self):
        self.storage: dict[str, deque[float]] = defaultdict(deque)
        self.lock = Lock()

    def is_allowed(self, key: str, limit: int, period: int) -> bool:
        now = time.monotonic()
        window = now - period
        with self.lock:
            timestamps = self.storage[key]
            while timestamps and timestamps[0] <= window:
                timestamps.popleft()
            if len(timestamps) >= limit:
                return False
            timestamps.append(now)
            return True

rate_limiter = SimpleRateLimiter()
RATE_LIMIT_RULES = {
    "/register": (10, 60),
    "/login": (5, 60),
    "/run-inference": (5, 60),
    "/logout": (30, 60),
    "/predictions": (30, 60),
    "/users": (20, 60),
    "/audit-logs": (20, 60),
    "/system-logs": (20, 60),
}
DEFAULT_RATE_LIMIT = (100, 60)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
            return await call_next(request)

        client_ip = request.headers.get("x-forwarded-for")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "anonymous"

        limit, period = RATE_LIMIT_RULES.get(request.url.path, DEFAULT_RATE_LIMIT)
        route_key = f"{client_ip}:{request.method}:{request.url.path}"
        if not rate_limiter.is_allowed(route_key, limit, period):
            raise AppException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                error_code="RATE_LIMIT_EXCEEDED",
                message="Rate limit exceeded. Please try again later."
            )
        return await call_next(request)

app.add_middleware(RateLimitMiddleware)

# --- CORS CONFIGURATION ---
# Add your allowed frontend origins here
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:5500"
    # Add more origins as needed:
]

# Use environment variable if set, otherwise use defaults
cors_origins_env = os.getenv("CORS_ORIGINS")
if cors_origins_env:
    ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
else:
    ALLOWED_ORIGINS = DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHEDULER SETUP (Standard Library Replacement) ---
stop_event = threading.Event()

def scheduled_prediction_update():
    """
    Background loop using threading.sleep instead of apscheduler.
    Runs every 6 hours.
    """
    interval = 6 * 3600  # 6 hours in seconds
    logger.info("SYSTEM | Background heartbeat thread initialized.")
    
    # Log initialization to system logs
    db_init = models.SessionLocal()
    try:
        log_system_event("INFO", "SCHEDULER", "Background heartbeat thread initialized", db_init)
    finally:
        db_init.close()
    
    while not stop_event.is_set():
        db = models.SessionLocal()
        try:
            from prediction_engine import run_prediction_pipeline

            log_system_event("INFO", "HEARTBEAT", "Starting scheduled prediction update", db)
            run_prediction_pipeline(db)
            log_system_event("INFO", "HEARTBEAT", "Scheduled prediction update completed successfully", db)
        except Exception as e:
            # Standard library replacement for Sentry: Detailed local logging
            log_system_event("ERROR", "HEARTBEAT", f"Scheduled update failed: {str(e)}", db)
        finally:
            db.close()
        
        # Sleep in short increments to allow for faster shutdown
        for _ in range(interval):
            if stop_event.is_set():
                break
            time.sleep(1)

# --- SECURITY SETUP ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- SCHEMAS ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str = None

    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        domain = v.split('@')[-1].lower()
        if domain not in ALLOWED_DOMAINS:
            allowed_str = ", ".join(ALLOWED_DOMAINS)
            raise ValueError(f"Registration restricted to following domains: {allowed_str}")
        return v

class Token(BaseModel):
    access_token: str
    token_type: str

class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    is_admin: bool = False

    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    full_name: str | None = None
    is_admin: bool | None = None

    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v: EmailStr | None) -> EmailStr | None:
        if v is None:
            return v
        domain = v.split('@')[-1].lower()
        if domain not in ALLOWED_DOMAINS:
            allowed_str = ", ".join(ALLOWED_DOMAINS)
            raise ValueError(f"Registration restricted to following domains: {allowed_str}")
        return v

class PredictionRead(BaseModel):
    id: int
    match_date: datetime | None = None
    home_team: str | None = None
    away_team: str | None = None
    home_team_id: int | None = None
    away_team_id: int | None = None
    avg_h: float | None = None
    avg_d: float | None = None
    avg_a: float | None = None
    h_attacking: float | None = None
    h_defending: float | None = None
    h_volatility: float | None = None
    h_efficiency: float | None = None
    a_attacking: float | None = None
    a_defending: float | None = None
    a_volatility: float | None = None
    a_efficiency: float | None = None
    prob_home: float | None = None
    prob_draw: float | None = None
    prob_away: float | None = None
    outcome: str | None = None
    confidence: float | None = None
    user_id: int | None = None

    model_config = {"from_attributes": True}

class AuditLogRead(BaseModel):
    id: int
    user_email: str
    action: str
    ip_address: str
    timestamp: datetime

    model_config = {"from_attributes": True}

class SystemLogRead(BaseModel):
    id: int
    level: str
    source: str
    message: str
    timestamp: datetime

    model_config = {"from_attributes": True}

# --- UTILS ---
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def log_audit_entry(email: str, ip_address: str, action: str, db: Session = None):
    """Log audit entry to both logger and database."""
    logger.info(f"AUDIT | User: {email} | Action: {action} | IP: {ip_address}")
    
    if db:
        try:
            audit_log = models.AuditLog(
                user_email=email,
                action=action,
                ip_address=ip_address
            )
            db.add(audit_log)
            db.commit()
        except Exception as e:
            logger.error(f"AUDIT ERROR | Failed to save audit log: {str(e)}", exc_info=True)

MAX_SYSTEM_LOGS = 10000

def prune_system_logs(db: Session):
    """Trim oldest system log entries when the table exceeds the configured maximum."""
    try:
        count = db.query(models.SystemLog).count()
        if count <= MAX_SYSTEM_LOGS:
            return
        overflow = count - MAX_SYSTEM_LOGS
        db.execute(text(
            """
            DELETE FROM system_logs WHERE id IN (
                SELECT id FROM system_logs
                ORDER BY timestamp ASC, id ASC
                LIMIT :overflow
            )
            """
        ), {"overflow": overflow})
        db.commit()
        logger.info(f"SYSTEM | Pruned {overflow} old system log(s) to enforce max {MAX_SYSTEM_LOGS} entries.")
    except Exception as e:
        db.rollback()
        logger.error(f"SYSTEM LOG ERROR | Failed to prune system logs: {str(e)}", exc_info=True)


def log_system_event(level: str, source: str, message: str, db: Session = None):
    """Log system event to both logger and database."""
    logger.log({"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}.get(level, 20), f"SYSTEM [{source}] {message}")
    
    if db:
        try:
            system_log = models.SystemLog(
                level=level,
                source=source,
                message=message
            )
            db.add(system_log)
            db.commit()
            prune_system_logs(db)
        except Exception as e:
            db.rollback()
            logger.error(f"SYSTEM LOG ERROR | Failed to save system log: {str(e)}", exc_info=True)


def check_ip_lockout(ip_address: str):
    now = datetime.utcnow()
    recent_failures = [t for t in failed_attempts[ip_address] if now - t < timedelta(minutes=LOCKOUT_DURATION_MINUTES)]
    failed_attempts[ip_address] = recent_failures
    if len(recent_failures) >= MAX_FAILED_ATTEMPTS:
        return True
    return False

def _cleanup_blacklisted_tokens():
    now = datetime.utcnow()
    expired = [token for token, expiry in blacklisted_tokens.items() if expiry <= now]
    for token in expired:
        del blacklisted_tokens[token]

def is_token_blacklisted(token: str):
    _cleanup_blacklisted_tokens()
    return token in blacklisted_tokens

def blacklist_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        exp_timestamp = payload.get("exp")
        if exp_timestamp is not None:
            blacklisted_tokens[token] = datetime.utcfromtimestamp(exp_timestamp)
            return
    except JWTError:
        pass
    # fallback: keep the token blacklisted for the next day
    blacklisted_tokens[token] = datetime.utcnow() + timedelta(days=1)

# --- DEPENDENCIES ---
def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = AppException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        error_code="INVALID_TOKEN",
        message="Could not validate credentials"
    )
    try:
        if is_token_blacklisted(token):
            raise credentials_exception
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

async def get_admin_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise AppException(status_code=403, error_code="ADMIN_REQUIRED", message="Admin access required")
    return current_user

def assert_user_access(target_user_id: int, current_user: models.User):
    if current_user.id != target_user_id and not current_user.is_admin:
        raise AppException(status_code=403, error_code="PERMISSION_DENIED", message="Permission denied")

# --- LIFECYCLE EVENTS ---

@app.on_event("startup")
def startup_event():
    models.init_db()
    # Create default admin user if not exists when configured
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    logger.info(f"SYSTEM | Startup: ADMIN_EMAIL={admin_email}, has_password={bool(admin_password)}")
    
    if admin_email and admin_password:
        db = models.SessionLocal()
        try:
            existing_admin = db.query(models.User).filter(models.User.email == admin_email).first()
            if not existing_admin:
                admin = models.User(
                    email=admin_email,
                    hashed_password=hash_password(admin_password),
                    full_name="Administrator",
                    is_admin=True
                )
                db.add(admin) 
                db.commit()
                log_system_event("INFO", "STARTUP", f"Default admin user created: {admin_email}", db)
            else:
                log_system_event("INFO", "STARTUP", f"Admin user already exists: {admin_email}", db)
        except Exception as e:
            log_system_event("ERROR", "STARTUP", f"Error creating admin user: {str(e)}", db)
            db.rollback()
        finally:
            db.close()
    else:
        logger.warning(f"SYSTEM | ADMIN_EMAIL or ADMIN_PASSWORD missing - not creating admin")
    
    # Start the automated heartbeat in a background thread
    daemon_thread = threading.Thread(target=scheduled_prediction_update, daemon=True)
    daemon_thread.start()
    logger.info("SYSTEM | Native background thread started (6-hour intervals).")

@app.on_event("shutdown")
def shutdown_event():
    stop_event.set()
    logger.info("SYSTEM | Signal sent to stop background thread.")

# --- ROUTES ---

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Monitoring endpoint for uptime and service connectivity."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "services": {
            "database": "connected",
            "scheduler": "active",
            "model_files": "missing"
        }
    }
    
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        health_status["services"]["database"] = "unreachable"
        health_status["status"] = "unhealthy"

    if os.path.exists("models/final_model_GRU_5.pkl"):
        health_status["services"]["model_files"] = "ready"
    else:
        health_status["status"] = "degraded"

    if health_status["status"] == "unhealthy":
        raise AppException(status_code=503, error_code="SERVICE_UNHEALTHY", message="Service is currently unhealthy")
    
    return health_status

@app.post("/register", response_model=Token)
def register(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if db_user:
        raise AppException(status_code=400, error_code="EMAIL_ALREADY_REGISTERED", message="Email already registered")
    
    new_user = models.User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    log_audit_entry(new_user.email, request.client.host, "ACCOUNT_REGISTRATION", db)
    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login", response_model=Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    client_ip = request.client.host
    if check_ip_lockout(client_ip):
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="ACCOUNT_LOCKED",
            message=f"Too many failed attempts. Please try again in {LOCKOUT_DURATION_MINUTES} minutes."
        )

    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        failed_attempts[client_ip].append(datetime.utcnow())
        raise AppException(status_code=401, error_code="INVALID_CREDENTIALS", message="Incorrect email or password")
    
    failed_attempts[client_ip] = []
    log_audit_entry(user.email, client_ip, "LOGIN_SUCCESS", db)
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/user", response_model=UserRead)
def get_current_user_profile(current_user: models.User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user

@app.get("/user/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    assert_user_access(user_id, current_user)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise AppException(status_code=404, error_code="USER_NOT_FOUND", message="User not found")
    return user

@app.put("/user/{user_id}", response_model=UserRead)
def update_user(user_id: int, user_update: UserUpdate, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    assert_user_access(user_id, current_user)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise AppException(status_code=404, error_code="USER_NOT_FOUND", message="User not found")

    if user_update.email is not None and user_update.email != user.email:
        if db.query(models.User).filter(models.User.email == user_update.email).first():
            raise AppException(status_code=400, error_code="EMAIL_ALREADY_REGISTERED", message="Email already registered")
        user.email = user_update.email

    if user_update.password is not None:
        user.hashed_password = hash_password(user_update.password)

    if user_update.full_name is not None:
        user.full_name = user_update.full_name

    if user_update.is_admin is not None:
        if not current_user.is_admin:
            raise AppException(status_code=403, error_code="ADMIN_REQUIRED", message="Admin access required to change admin status")
        user.is_admin = user_update.is_admin

    db.commit()
    db.refresh(user)
    log_audit_entry(current_user.email, request.client.host, f"UPDATE_USER_{user_id}", db)
    return user

@app.delete("/user/{user_id}")
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    assert_user_access(user_id, current_user)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise AppException(status_code=404, error_code="USER_NOT_FOUND", message="User not found")
    db.delete(user)
    db.commit()
    log_audit_entry(current_user.email, request.client.host, f"DELETE_USER_{user_id}", db)
    return {"message": "User deleted"}

@app.get("/prediction/{prediction_id}", response_model=PredictionRead)
def get_prediction(prediction_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    prediction = db.query(models.Prediction).filter(models.Prediction.id == prediction_id).first()
    if prediction is None:
        raise AppException(status_code=404, error_code="PREDICTION_NOT_FOUND", message="Prediction not found")
    if prediction.user_id != current_user.id and not current_user.is_admin:
        raise AppException(status_code=403, error_code="PERMISSION_DENIED", message="Permission denied")
    return prediction

@app.get("/predictions")
def get_predictions(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get predictions with pagination. Default limit 20, max 100."""
    if limit > 100:
        limit = 100
    if skip < 0:
        skip = 0
    
    query = db.query(models.Prediction)
    if not current_user.is_admin:
        query = query.filter(models.Prediction.user_id == current_user.id)
    
    total = query.count()
    results = query.offset(skip).limit(limit).all()
    
    return {
        "items": results,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@app.post("/run-inference")
def trigger_inference(
    request: Request,
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not os.path.exists("models/final_model_GRU_5.pkl"):
        raise AppException(status_code=500, error_code="MODELS_MISSING", message="Models missing")
    
    from prediction_engine import run_prediction_pipeline

    log_audit_entry(current_user.email, request.client.host, "MANUAL_INFERENCE_TRIGGER", db)
    background_tasks.add_task(run_prediction_pipeline, db)
    return {"message": f"Inference started manually by {current_user.email}"}

@app.post("/logout")
def logout(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    blacklist_token(token)
    log_audit_entry(current_user.email, request.client.host, "LOGOUT", db)
    return {"message": "Successfully logged out"}

@app.get("/users")
def get_users(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    """Get all users with pagination. Default limit 20, max 100 (admin only)."""
    if limit > 100:
        limit = 100
    if skip < 0:
        skip = 0
    
    total = db.query(models.User).count()
    users = db.query(models.User).offset(skip).limit(limit).all()
    
    return {
        "items": [{"id": u.id, "email": u.email, "full_name": u.full_name, "is_admin": u.is_admin} for u in users],
        "total": total,
        "skip": skip,
        "limit": limit
    }

@app.get("/audit-logs")
def get_audit_logs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    """Retrieve audit logs with pagination (admin only). Shows user activity and actions."""
    if limit > 100:
        limit = 100
    if skip < 0:
        skip = 0
    
    total = db.query(models.AuditLog).count()
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    return {
        "items": logs,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@app.get("/system-logs")
def get_system_logs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    """Retrieve system logs with pagination (admin only). Shows system events, errors, and scheduler activity."""
    if limit > 100:
        limit = 100
    if skip < 0:
        skip = 0
    
    total = db.query(models.SystemLog).count()
    logs = db.query(models.SystemLog).order_by(models.SystemLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    return {
        "items": logs,
        "total": total,
        "skip": skip,
        "limit": limit
    }
    return logs