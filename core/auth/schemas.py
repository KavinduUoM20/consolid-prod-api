import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
from core.auth.models import UserRole


# Request Schemas
class TenantCreateSchema(BaseModel):
    """Schema for creating a new tenant."""
    name: str = Field(..., min_length=1, max_length=255, description="Tenant name")
    slug: str = Field(..., min_length=1, max_length=100, description="URL-friendly tenant identifier")
    description: Optional[str] = Field(None, max_length=1000, description="Tenant description")
    settings: Optional[dict] = Field(default_factory=dict, description="Tenant-specific settings")
    
    @validator('slug')
    def validate_slug(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug must contain only alphanumeric characters, hyphens, and underscores')
        return v.lower()


class UserRegisterSchema(BaseModel):
    """Schema for user registration."""
    username: str = Field(..., min_length=3, max_length=100, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    role: Optional[str] = Field(default=UserRole.USER, description="User role")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').replace('.', '').isalnum():
            raise ValueError('Username must contain only alphanumeric characters, underscores, hyphens, and dots')
        return v.lower()
    
    @validator('role')
    def validate_role(cls, v):
        if v and not UserRole.is_valid_role(v):
            raise ValueError(f'Invalid role. Must be one of: {", ".join(UserRole.all_roles())}')
        return v or UserRole.USER
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLoginSchema(BaseModel):
    """Schema for user login."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class PasswordChangeSchema(BaseModel):
    """Schema for password change."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


# Response Schemas
class TenantResponseSchema(BaseModel):
    """Schema for tenant response."""
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    settings: dict
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserResponseSchema(BaseModel):
    """Schema for user response (without sensitive data)."""
    id: uuid.UUID
    username: str
    email: str
    role: str
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    tenant: TenantResponseSchema
    
    class Config:
        from_attributes = True


class UserLoginResponseSchema(BaseModel):
    """Minimal user info for login response (security-focused)."""
    id: uuid.UUID
    username: str
    role: str
    tenant_slug: str
    
    class Config:
        from_attributes = True


class TokenResponseSchema(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserLoginResponseSchema


class TokenDataSchema(BaseModel):
    """Schema for JWT token data."""
    sub: str  # user_id
    username: str
    email: str
    role: str
    tenant_id: str
    tenant_slug: str
    exp: int
    iat: int
    jti: str


class UserUpdateSchema(BaseModel):
    """Schema for updating user information."""
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = Field(None)
    role: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)
    is_verified: Optional[bool] = Field(None)
    
    @validator('username')
    def validate_username(cls, v):
        if v and not v.replace('_', '').replace('-', '').replace('.', '').isalnum():
            raise ValueError('Username must contain only alphanumeric characters, underscores, hyphens, and dots')
        return v.lower() if v else v
    
    @validator('role')
    def validate_role(cls, v):
        if v and not UserRole.is_valid_role(v):
            raise ValueError(f'Invalid role. Must be one of: {", ".join(UserRole.all_roles())}')
        return v


class TenantUpdateSchema(BaseModel):
    """Schema for updating tenant information."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = Field(None)
    settings: Optional[dict] = Field(None)


# Error Response Schemas
class ErrorResponseSchema(BaseModel):
    """Schema for error responses."""
    detail: str
    error_code: Optional[str] = None


class ValidationErrorResponseSchema(BaseModel):
    """Schema for validation error responses."""
    detail: str
    errors: list
