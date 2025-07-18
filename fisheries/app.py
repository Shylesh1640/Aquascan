from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
import shutil, os, time

# --- DATABASE SETUP ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./data.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

# --- USER MODEL ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    is_active = Column(Boolean, default=True)

Base.metadata.create_all(bind=engine)

# --- AUTH SETUP ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_current_user(token: str = Depends(oauth2_scheme)):
    if token != "admin_token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"username": "admin"}

# --- FASTAPI APP ---
app = FastAPI(
    title="🔥 Complex FastAPI in One File",
    description="A single massive file with auth, DB, background, file, caching, and more",
    version="1.0.0",
)

# --- MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    print(f"{request.method} {request.url.path} - {duration:.2f}s")
    return response

# --- SCHEMAS ---
class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    is_active: bool
    class Config:
        orm_mode = True

# --- EXCEPTION HANDLER ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": str(exc)})

# --- AUTH ROUTE ---
@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == "admin" and form_data.password == "admin123":
        return {"access_token": "admin_token", "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Invalid credentials")

# --- USERS ---
@app.post("/users/", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username exists")
    hashed_pw = get_password_hash(user.password)
    new_user = User(username=user.username, password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/me", response_model=UserOut)
def read_user(current_user: dict = Depends(get_current_user)):
    return {"id": 0, "username": current_user["username"], "is_active": True}

# --- BACKGROUND TASK ---
def log_action(action: str):
    with open("actions.log", "a") as log:
        log.write(f"{action}\n")

@app.post("/task/")
def run_task(action: str, bg: BackgroundTasks):
    bg.add_task(log_action, action)
    return {"status": "Scheduled"}

# --- FILE UPLOAD/DOWNLOAD ---
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    path = os.path.join(UPLOAD_DIR, file.filename)
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename}

@app.get("/download/{filename}")
def download_file(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="application/octet-stream", filename=filename)

# --- CACHE SIMULATION ---
cache = {}

@app.get("/cache/set")
def set_cache(key: str, value: str):
    cache[key] = value
    return {"message": "Stored"}

@app.get("/cache/get")
def get_cache(key: str):
    return {"value": cache.get(key, "Key not found")}

# --- CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROOT ---
@app.get("/")
def home():
    return {"message": "Welcome to the most complex single FastAPI file!"}
