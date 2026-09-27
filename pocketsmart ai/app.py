import os
import json
import re
import shutil
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

from fastapi import (
    FastAPI, HTTPException, Depends, File, UploadFile,
    Form, Request, status, Cookie, Response
)
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

from gemini_utils import (
    get_home_recommendations,
    get_party_recommendations,
    get_jewelry_recommendations,
    usd_to_inr
)

load_dotenv()

# ==========================================
# Configuration & Security
# ==========================================

SECRET_KEY = os.getenv("SECRET_KEY", "pocketsmart_super_secret_jwt_key_2025_secure_random_string_99")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

app = FastAPI(
    title="PocketSmart: AI Budget Planner",
    description="Cross-platform GenAI-powered budget allocation and recommendation assistant",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ==========================================
# In-Memory Database & State Stores
# ==========================================

class UserInDB(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    hashed_password: str
    disabled: bool = False

class RegisterUser(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserSession(BaseModel):
    username: str
    login_time: datetime
    last_activity: datetime
    token: str
    user_data: Dict[str, Any] = {}

class RecommendationItem(BaseModel):
    id: str
    timestamp: str
    recommendation_type: str  # "home", "party", "jewelry"
    input_summary: Dict[str, Any]
    full_result: Dict[str, Any]

# Seed demo users
users_db: Dict[str, UserInDB] = {
    "admin": UserInDB(
        username="admin",
        email="admin@pocketsmart.ai",
        full_name="Administrator",
        hashed_password=pwd_context.hash("admin123"),
        disabled=False
    ),
    "sai": UserInDB(
        username="sai",
        email="sai@example.com",
        full_name="Sai Kumar",
        hashed_password=pwd_context.hash("password123"),
        disabled=False
    )
}

active_sessions: Dict[str, UserSession] = {}
blacklisted_tokens = set()
user_recommendations: Dict[str, List[RecommendationItem]] = {
    "sai": [
        RecommendationItem(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().strftime("%b %d, %Y, %I:%M %p"),
            recommendation_type="home",
            input_summary={
                "budget": 50000,
                "rooms": "Living Room, Kitchen, Bedroom",
                "lights": 6,
                "fans": 3,
                "furniture": 4
            },
            full_result={
                "total_budget": 50000,
                "remaining_budget": 3500,
                "calculation_table": [
                    {"category": "Lighting", "items_count": 6, "total_cost": 11000, "percentage_of_budget": 22.0},
                    {"category": "Ceiling Fans", "items_count": 3, "total_cost": 14000, "percentage_of_budget": 28.0},
                    {"category": "Furniture", "items_count": 4, "total_cost": 17500, "percentage_of_budget": 35.0},
                    {"category": "Dining & Tables", "items_count": 1, "total_cost": 4000, "percentage_of_budget": 8.0}
                ]
            }
        ),
        RecommendationItem(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().strftime("%b %d, %Y, %I:%M %p"),
            recommendation_type="party",
            input_summary={
                "budget": 25000,
                "party_type": "Birthday Bash",
                "guests": 15,
                "needs": "Catering, Decoration, Entertainment"
            },
            full_result={
                "total_budget": 25000,
                "remaining_budget": 1200,
                "calculation_table_inr": [
                    {"category": "Catering", "items_count": 1, "total_cost": 11250, "percentage_of_budget": 45.0},
                    {"category": "Decoration", "items_count": 1, "total_cost": 5000, "percentage_of_budget": 20.0},
                    {"category": "Entertainment", "items_count": 1, "total_cost": 5000, "percentage_of_budget": 20.0},
                    {"category": "Contingency", "items_count": 1, "total_cost": 2550, "percentage_of_budget": 10.2}
                ]
            }
        ),
        RecommendationItem(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().strftime("%b %d, %Y, %I:%M %p"),
            recommendation_type="jewelry",
            input_summary={
                "budget": 15000,
                "occasion": "Wedding Reception",
                "has_image": True
            },
            full_result={
                "total_budget": 15000,
                "remaining_budget": 800,
                "outfit_analysis": {"colors": ["Emerald Green", "Gold"], "style": "Royal Ethnic", "formality": "Festive"},
                "styling_tips": ["Pair warm gold earrings with emerald studs."]
            }
        )
    ]
}

# ==========================================
# Authentication Helpers
# ==========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_token_from_request(
    request: Request,
    token_header: Optional[str] = Depends(oauth2_scheme),
    access_token: Optional[str] = Cookie(None)
) -> Optional[str]:
    if access_token:
        return access_token
    if token_header:
        return token_header
    auth_hdr = request.headers.get("Authorization")
    if auth_hdr and auth_hdr.startswith("Bearer "):
        return auth_hdr.split(" ")[1]
    return None

async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(get_token_from_request)
) -> Optional[UserInDB]:
    if not token or token in blacklisted_tokens:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    user = users_db.get(username)
    if user and username in active_sessions:
        active_sessions[username].last_activity = datetime.utcnow()
    return user

async def get_current_active_user(
    request: Request,
    current_user: Optional[UserInDB] = Depends(get_current_user)
) -> UserInDB:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def save_to_history(username: str, recommendation_type: str, input_data: dict, result: dict):
    """Save recommendation record to user history."""
    if username not in user_recommendations:
        user_recommendations[username] = []
    
    item = RecommendationItem(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now().strftime("%b %d, %Y, %I:%M %p"),
        recommendation_type=recommendation_type,
        input_summary=input_data,
        full_result=result
    )
    user_recommendations[username].insert(0, item)
    return item

def save_upload_file(upload_file: UploadFile) -> str:
    """Save uploaded image file to static/uploads and return relative path."""
    ext = os.path.splitext(upload_file.filename)[1]
    if not ext:
        ext = ".jpg"
    unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
    file_path = os.path.join("static", "uploads", unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return file_path

# ==========================================
# Input Models
# ==========================================

class HomeBudgetInput(BaseModel):
    total_budget: float
    num_lights: int = 4
    num_fans: int = 2
    num_furniture: int = 2
    num_dining_tables: int = 1
    has_living_room: bool = True
    has_kitchen: bool = False
    has_bedroom: bool = True
    additional_requirements: Optional[str] = ""

class PartyBudgetInput(BaseModel):
    total_budget: float
    num_guests: int = 10
    party_type: str = "Birthday"
    venue_type: str = "Home"
    needs_catering: bool = True
    needs_decoration: bool = True
    needs_entertainment: bool = True
    additional_requirements: Optional[str] = ""

class JewelryBudgetInput(BaseModel):
    total_budget: float
    occasion: str = "Wedding"
    preferences: Optional[str] = ""

# ==========================================
# Page Routes (HTML)
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request, user: Optional[UserInDB] = Depends(get_current_user)):
    """Main landing page"""
    return templates.TemplateResponse(request=request, name="index.html", context={"user": user})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: Optional[UserInDB] = Depends(get_current_user)):
    """Serve login page"""
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="login.html", context={"user": None})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: Optional[UserInDB] = Depends(get_current_user)):
    """Serve registration page"""
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="register.html", context={"user": None})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    """User dashboard page"""
    history = user_recommendations.get(current_user.username, [])
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": current_user,
        "recent_activity": history[:5],
        "total_plans": len(history)
    })

@app.get("/home-planner", response_class=HTMLResponse)
@app.get("/home-budget", response_class=HTMLResponse)
async def home_planner_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    """Home budget planner page"""
    return templates.TemplateResponse(request=request, name="home_planner.html", context={"user": current_user})

@app.get("/party-planner", response_class=HTMLResponse)
@app.get("/party-budget", response_class=HTMLResponse)
async def party_planner_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    """Party budget planner page"""
    return templates.TemplateResponse(request=request, name="party_planner.html", context={"user": current_user})

@app.get("/jewelry-planner", response_class=HTMLResponse)
@app.get("/jewelry-budget", response_class=HTMLResponse)
async def jewelry_planner_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    """Jewelry budget planner page"""
    return templates.TemplateResponse(request=request, name="jewelry_planner.html", context={"user": current_user})

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    """History page to view past recommendations"""
    history = user_recommendations.get(current_user.username, [])
    return templates.TemplateResponse(request=request, name="history.html", context={
        "user": current_user,
        "history": history
    })

# ==========================================
# Authentication & Session Endpoints
# ==========================================

@app.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: Optional[str] = Form(None),
    full_name: Optional[str] = Form(None)
):
    """Handle new user registration"""
    username = username.strip().lower()
    email = email.strip()

    if confirm_password and password != confirm_password:
        return templates.TemplateResponse(request=request, name="register.html", context={
            "error": "Passwords do not match."
        }, status_code=400)

    if username in users_db:
        return templates.TemplateResponse(request=request, name="register.html", context={
            "error": "Username is already registered."
        }, status_code=400)

    hashed = get_password_hash(password)
    user = UserInDB(
        username=username,
        email=email,
        full_name=full_name or username.title(),
        hashed_password=hashed
    )
    users_db[username] = user
    user_recommendations[username] = []

    # Auto login upon registration
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": username}, expires_delta=access_token_expires)

    active_sessions[username] = UserSession(
        username=username,
        login_time=datetime.utcnow(),
        last_activity=datetime.utcnow(),
        token=token,
        user_data={"registered": True}
    )

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response


@app.post("/login")
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Form-based login for web browser"""
    username = username.strip().lower()
    user = users_db.get(username)
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(request=request, name="login.html", context={
            "error": "Invalid username or password."
        }, status_code=400)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": username}, expires_delta=access_token_expires)

    # Invalidate existing token if any
    if username in active_sessions:
        blacklisted_tokens.add(active_sessions[username].token)

    active_sessions[username] = UserSession(
        username=username,
        login_time=datetime.utcnow(),
        last_activity=datetime.utcnow(),
        token=token,
        user_data={}
    )

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 standard token endpoint"""
    user = users_db.get(form_data.username.lower())
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    if user.username in active_sessions:
        blacklisted_tokens.add(active_sessions[user.username].token)

    active_sessions[user.username] = UserSession(
        username=user.username,
        login_time=datetime.utcnow(),
        last_activity=datetime.utcnow(),
        token=token,
        user_data={}
    )

    response = JSONResponse(content={"access_token": token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response


@app.get("/logout")
@app.post("/logout")
async def logout(request: Request, token: Optional[str] = Depends(get_token_from_request)):
    """Logout user and clear session"""
    if token:
        blacklisted_tokens.add(token)
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username and username in active_sessions:
                del active_sessions[username]
        except JWTError:
            pass

    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response


@app.get("/session-info")
async def get_session_info(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    """Get current user's session information"""
    if current_user.username in active_sessions:
        session = active_sessions[current_user.username]
        duration = int((datetime.utcnow() - session.login_time).total_seconds() // 60)
        return {
            "username": session.username,
            "login_time": session.login_time.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "session_duration_minutes": duration,
            "user_data": session.user_data
        }
    raise HTTPException(status_code=404, detail="No active session found")


@app.post("/session-data")
async def update_session_data(
    data: Dict[str, Any],
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Update user's session data"""
    if current_user.username in active_sessions:
        active_sessions[current_user.username].user_data.update(data)
        active_sessions[current_user.username].last_activity = datetime.utcnow()
        return {"message": "Session data updated", "data": active_sessions[current_user.username].user_data}
    raise HTTPException(status_code=404, detail="No active session found")

# ==========================================
# Core AI Planner Endpoints
# ==========================================

@app.post("/home-budget")
@app.post("/generate-home")
async def plan_home_budget(
    budget_input: HomeBudgetInput,
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Generate home budget recommendations"""
    rooms = []
    if budget_input.has_living_room:
        rooms.append("Living Room")
    if budget_input.has_kitchen:
        rooms.append("Kitchen")
    if budget_input.has_bedroom:
        rooms.append("Bedroom")

    # Store last query in session
    if current_user.username in active_sessions:
        active_sessions[current_user.username].user_data["last_home_budget"] = {
            "timestamp": datetime.utcnow().isoformat(),
            "budget": budget_input.total_budget,
            "requirements": {
                "lights": budget_input.num_lights,
                "fans": budget_input.num_fans,
                "furniture": budget_input.num_furniture,
                "dining_tables": budget_input.num_dining_tables,
                "rooms": ", ".join(rooms)
            }
        }

    result = get_home_recommendations(budget_input)

    # Save to history
    save_to_history(
        username=current_user.username,
        recommendation_type="home",
        input_data={
            "budget": budget_input.total_budget,
            "rooms": ", ".join(rooms) if rooms else "All",
            "lights": budget_input.num_lights,
            "fans": budget_input.num_fans,
            "furniture": budget_input.num_furniture,
            "dining_tables": budget_input.num_dining_tables,
            "additional": budget_input.additional_requirements
        },
        result=result
    )

    return result


@app.post("/party-budget")
@app.post("/generate-party")
async def plan_party_budget(
    budget_input: PartyBudgetInput,
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Generate party budget recommendations"""
    needs = []
    if budget_input.needs_catering:
        needs.append("Catering")
    if budget_input.needs_decoration:
        needs.append("Decoration")
    if budget_input.needs_entertainment:
        needs.append("Entertainment")

    if current_user.username in active_sessions:
        active_sessions[current_user.username].user_data["last_party_budget"] = {
            "timestamp": datetime.utcnow().isoformat(),
            "budget": budget_input.total_budget,
            "party_type": budget_input.party_type,
            "guests": budget_input.num_guests
        }

    result = get_party_recommendations(budget_input)

    save_to_history(
        username=current_user.username,
        recommendation_type="party",
        input_data={
            "budget": budget_input.total_budget,
            "party_type": budget_input.party_type,
            "guests": budget_input.num_guests,
            "venue_type": budget_input.venue_type,
            "needs": ", ".join(needs),
            "additional": budget_input.additional_requirements
        },
        result=result
    )

    return result


@app.post("/jewelry-budget")
@app.post("/generate-jewelry")
async def plan_jewelry_budget(
    total_budget: float = Form(...),
    occasion: str = Form(...),
    preferences: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    request: Request = None,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Generate jewelry recommendations with optional outfit image analysis"""
    budget_input = JewelryBudgetInput(
        total_budget=total_budget,
        occasion=occasion,
        preferences=preferences or ""
    )

    image_path = None
    saved_filename = None
    if image and image.filename:
        image_path = save_upload_file(image)
        saved_filename = os.path.basename(image_path)

    if current_user.username in active_sessions:
        active_sessions[current_user.username].user_data["last_jewelry_budget"] = {
            "timestamp": datetime.utcnow().isoformat(),
            "budget": budget_input.total_budget,
            "occasion": budget_input.occasion,
            "has_image": image_path is not None
        }

    result = get_jewelry_recommendations(budget_input, image_path)

    input_data = {
        "budget": budget_input.total_budget,
        "occasion": budget_input.occasion,
        "preferences": budget_input.preferences,
        "has_image": image_path is not None,
        "image_file": f"/static/uploads/{saved_filename}" if saved_filename else None
    }

    save_to_history(
        username=current_user.username,
        recommendation_type="jewelry",
        input_data=input_data,
        result=result
    )

    return result


# ==========================================
# History & Reporting Endpoints
# ==========================================

@app.get("/recommendation-history")
async def get_recommendation_history(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Get the user's recommendation history list"""
    history = user_recommendations.get(current_user.username, [])
    history_data = []
    for item in history:
        history_data.append({
            "id": item.id,
            "timestamp": item.timestamp,
            "type": item.recommendation_type,
            "input": item.input_summary,
            "summary": item.full_result
        })
    return {"history": history_data}


@app.get("/recommendation-details/{recommendation_id}")
async def get_recommendation_details(
    recommendation_id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Get the full details of a specific past recommendation"""
    history = user_recommendations.get(current_user.username, [])
    for item in history:
        if item.id == recommendation_id:
            return {
                "id": item.id,
                "timestamp": item.timestamp,
                "type": item.recommendation_type,
                "input": item.input_summary,
                "full_result": item.full_result
            }
    raise HTTPException(status_code=404, detail="Recommendation not found")

# ==========================================
# Startup & Background Tasks
# ==========================================

@app.on_event("startup")
async def setup_session_cleanup():
    """Background task to clean up expired sessions periodically"""
    async def cleanup_expired_sessions():
        while True:
            current_time = datetime.utcnow()
            expired_users = []
            for uname, sess in list(active_sessions.items()):
                inactive_secs = (current_time - sess.last_activity).total_seconds()
                if inactive_secs > (ACCESS_TOKEN_EXPIRE_MINUTES * 60):
                    expired_users.append(uname)
            
            for uname in expired_users:
                print(f"[Session Worker] Removing expired session for {uname}")
                if uname in active_sessions:
                    blacklisted_tokens.add(active_sessions[uname].token)
                    del active_sessions[uname]

            await asyncio.sleep(300)

    asyncio.create_task(cleanup_expired_sessions())

# ==========================================
# Entrypoint
# ==========================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting PocketSmart: AI Budget Planner on {host}:{port} ...")
    uvicorn.run("app:app", host=host, port=port, reload=True)
