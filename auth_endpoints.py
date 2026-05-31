class UserSignup(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# Add these endpoints to your main_api_with_queue.py:

# User storage (in production, use MongoDB)
users_db = {}

@app.post("/auth/signup")
async def signup(user: UserSignup):
    # Check if user exists
    if user.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
    
    # Store user
    users_db[user.email] = {
        "name": user.name,
        "email": user.email,
        "password": hashed.decode('utf-8'),
        "created_at": datetime.utcnow()
    }
    
    # Create token
    token = jwt.encode(
        {"email": user.email, "name": user.name, "exp": datetime.utcnow() + timedelta(days=7)},
        SECRET_KEY,
        algorithm="HS256"
    )
    
    return {"token": token, "user": {"name": user.name, "email": user.email}}

@app.post("/auth/login")
async def login(user: UserLogin):
    # Check if user exists
    if user.email not in users_db:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    stored_user = users_db[user.email]
    if not bcrypt.checkpw(user.password.encode('utf-8'), stored_user["password"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = jwt.encode(
        {"email": user.email, "name": stored_user["name"], "exp": datetime.utcnow() + timedelta(days=7)},
        SECRET_KEY,
        algorithm="HS256"
    )
    
    return {"token": token, "user": {"name": stored_user["name"], "email": user.email}}

@app.get("/auth/verify")
async def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return {"valid": True, "user": payload}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
