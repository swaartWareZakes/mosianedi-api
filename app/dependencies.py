import os
from typing import Optional
from fastapi import Header, HTTPException, Depends
from jose import jwt, JWTError
import psycopg2
from contextlib import contextmanager

# --- CONFIG ---
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
ALGORITHM = "HS256"
DB_URL = os.getenv("DATABASE_URL")

if not JWT_SECRET:
    raise ValueError("SUPABASE_JWT_SECRET is missing from .env")

# --- DB CONTEXT ---
@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        yield conn
    finally:
        if conn:
            conn.close()

# --- AUTH DEPENDENCIES ---
def get_current_user_token(authorization: str = Header(None)) -> str:
    if not authorization:
        raise HTTPException(401, "Authorization header missing")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(401, "Invalid auth scheme")
        return token
    except Exception:
        raise HTTPException(401, "Invalid authorization header")

def get_current_user_id(token: str = Depends(get_current_user_token)) -> str:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Token missing user ID")
        return user_id
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

# --- CONTEXT OBJECT ---
class UserContext:
    def __init__(self, user_id: str, role: str, department: str, email: str = ""):
        self.user_id = user_id
        self.role = role
        self.department = department
        self.email = email

def get_user_context(user_id: str = Depends(get_current_user_id)) -> UserContext:
    """
    Fetches user profile to determine if they are 'engineer' or 'treasury'.
    """
    sql = "SELECT department, email, first_name, last_name FROM public.profiles WHERE user_id = %s"
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
            
            department = row[0] if row else "Engineering"
            email = row[1] if row else ""
            
            # --- ROLE LOGIC ---
            # If department contains 'Treasury' or 'Finance', they are REVIEWERS.
            role = "engineer"
            if department and any(x in department.lower() for x in ['treasury', 'finance', 'budget']):
                role = "treasury"
            
            return UserContext(user_id=user_id, role=role, department=department, email=email)