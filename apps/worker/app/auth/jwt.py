"""
JWT authentication and authorization
"""
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from pydantic import BaseModel

from ..config import settings
from ..logging_config import setup_logging

logger = setup_logging(__name__)

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []


class User(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    roles: List[str] = []
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    roles: List[str] = ["user"]


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthService:
    """Authentication and authorization service"""
    
    def __init__(self):
        # In production, this would be a database
        # For now, we'll use in-memory storage with default admin user
        self.users_db: Dict[str, Dict] = {
            "admin": {
                "id": "admin",
                "username": "admin",
                "email": "admin@scrapesavee.com",
                "full_name": "Administrator",
                "hashed_password": self.get_password_hash("admin123"),
                "roles": ["admin", "user"],
                "is_active": True,
                "is_superuser": True,
                "created_at": datetime.utcnow(),
                "last_login": None
            }
        }
        
        # Role-based permissions
        self.role_permissions = {
            "admin": [
                "read:all",
                "write:all", 
                "delete:all",
                "manage:users",
                "manage:sources",
                "manage:jobs",
                "manage:system"
            ],
            "operator": [
                "read:sources",
                "read:jobs", 
                "read:blocks",
                "write:sources",
                "write:jobs",
                "manage:sources",
                "manage:jobs"
            ],
            "viewer": [
                "read:sources",
                "read:jobs",
                "read:blocks",
                "read:stats"
            ],
            "user": [
                "read:stats"
            ]
        }
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        return pwd_context.verify(plain_password, hashed_password)
        
    def get_password_hash(self, password: str) -> str:
        """Hash password"""
        return pwd_context.hash(password)
        
    def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        return self.users_db.get(username)
        
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user"""
        user = self.get_user(username)
        if not user:
            return None
        if not self.verify_password(password, user["hashed_password"]):
            return None
        return user
        
    def create_user(self, user_data: UserCreate) -> User:
        """Create new user"""
        if user_data.username in self.users_db:
            raise ValueError("Username already exists")
            
        user_id = secrets.token_urlsafe(16)
        
        user_dict = {
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": self.get_password_hash(user_data.password),
            "roles": user_data.roles,
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.utcnow(),
            "last_login": None
        }
        
        self.users_db[user_data.username] = user_dict
        
        return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})
        
    def get_user_permissions(self, roles: List[str]) -> List[str]:
        """Get permissions for user roles"""
        permissions = set()
        for role in roles:
            permissions.update(self.role_permissions.get(role, []))
        return list(permissions)
        
    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
        return encoded_jwt
        
    def create_refresh_token(self, data: Dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
        return encoded_jwt
        
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
            return payload
        except jwt.PyJWTError:
            return None
            
    def login(self, login_data: UserLogin) -> Token:
        """Login user and return tokens"""
        user = self.authenticate_user(login_data.username, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
            
        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
            
        # Update last login
        user["last_login"] = datetime.utcnow()
        
        # Get user permissions
        permissions = self.get_user_permissions(user["roles"])
        
        # Create token data
        token_data = {
            "sub": user["username"],
            "user_id": user["id"],
            "roles": user["roles"],
            "permissions": permissions
        }
        
        # Create tokens
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token({"sub": user["username"]})
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    def refresh_access_token(self, refresh_token: str) -> Token:
        """Refresh access token"""
        payload = self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
            
        username = payload.get("sub")
        user = self.get_user(username)
        if not user or not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
            
        # Get user permissions
        permissions = self.get_user_permissions(user["roles"])
        
        # Create new access token
        token_data = {
            "sub": user["username"],
            "user_id": user["id"],
            "roles": user["roles"],
            "permissions": permissions
        }
        
        access_token = self.create_access_token(token_data)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,  # Keep same refresh token
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )


# Global auth service
auth_service = AuthService()


# Dependencies
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = auth_service.verify_token(credentials.credentials)
        if payload is None or payload.get("type") != "access":
            raise credentials_exception
            
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        user_dict = auth_service.get_user(username)
        if user_dict is None:
            raise credentials_exception
            
        return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})
        
    except jwt.PyJWTError:
        raise credentials_exception


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_permission(permission: str):
    """Dependency factory for permission-based access control"""
    async def permission_checker(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> User:
        user = await get_current_user(credentials)
        
        payload = auth_service.verify_token(credentials.credentials)
        user_permissions = payload.get("permissions", [])
        
        # Check if user has required permission or is superuser
        if user.is_superuser or permission in user_permissions or "write:all" in user_permissions:
            return user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission} required"
        )
        
    return permission_checker


def require_role(role: str):
    """Dependency factory for role-based access control"""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.is_superuser or role in current_user.roles:
            return current_user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role required: {role}"
        )
        
    return role_checker


# Convenience dependencies
require_admin = require_role("admin")
require_operator = require_role("operator")
require_viewer = require_role("viewer")

