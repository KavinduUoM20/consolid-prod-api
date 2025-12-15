import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from core.auth.models import User, Tenant, UserSession, UserRole
from core.auth.schemas import (
    UserRegisterSchema, 
    TenantCreateSchema, 
    UserUpdateSchema, 
    TenantUpdateSchema,
    TokenDataSchema
)
from core.auth.utils import PasswordUtils, JWTUtils, TenantUtils


class AuthService:
    """Service class for authentication operations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def register_user(
        self, 
        user_data: UserRegisterSchema, 
        tenant_slug: str = "default"
    ) -> User:
        """Register a new user."""
        # Get or create tenant
        tenant = await self.get_tenant_by_slug(tenant_slug)
        if not tenant:
            # Create default tenant if it doesn't exist
            if tenant_slug == "default":
                tenant_create = TenantCreateSchema(
                    name="Default Tenant",
                    slug="default",
                    description="Default tenant for the application"
                )
                tenant = await self.create_tenant(tenant_create)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant '{tenant_slug}' not found"
                )
        
        if not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant is not active"
            )
        
        # Check if username already exists in this tenant
        existing_user = await self.get_user_by_username_and_tenant(
            user_data.username, tenant.id
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists in this tenant"
            )
        
        # Check if email already exists globally
        existing_email = await self.get_user_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Hash password
        password_hash = PasswordUtils.hash_password(user_data.password)
        
        # Create user
        user = User(
            tenant_id=tenant.id,
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            role=user_data.role
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        # Load tenant relationship
        await self.db.refresh(user, ["tenant"])
        
        return user
    
    async def authenticate_user(
        self, 
        username: str, 
        password: str
    ) -> Optional[User]:
        """Authenticate a user by username/email and password."""
        # Find user by username or email across all active tenants
        stmt = select(User).options(selectinload(User.tenant)).where(
            and_(
                or_(
                    User.username == username.lower(),
                    User.email == username.lower()
                ),
                User.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Check if user's tenant is active
        if not user.tenant or not user.tenant.is_active:
            return None
        
        # Verify password
        if not PasswordUtils.verify_password(password, user.password_hash):
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        await self.db.commit()
        
        return user
    
    async def create_access_token(self, user: User) -> Tuple[str, str, int]:
        """Create an access token for a user."""
        token, jti, expires_in = JWTUtils.create_access_token(user)
        
        # Store session
        session = UserSession(
            user_id=user.id,
            token_jti=jti,
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in)
        )
        
        self.db.add(session)
        await self.db.commit()
        
        return token, jti, expires_in
    
    async def verify_token(self, token: str) -> Optional[User]:
        """Verify a JWT token and return the user."""
        token_data = JWTUtils.verify_token(token)
        if not token_data:
            return None
        
        # Check if token is expired
        if JWTUtils.is_token_expired(token_data):
            return None
        
        # Check if session exists and is not revoked
        stmt = select(UserSession).where(
            and_(
                UserSession.token_jti == token_data.jti,
                UserSession.is_revoked == False,
                UserSession.expires_at > datetime.utcnow()
            )
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            return None
        
        # Get user with tenant
        user = await self.get_user_by_id(uuid.UUID(token_data.sub))
        return user
    
    async def revoke_token(self, jti: str) -> bool:
        """Revoke a token by marking its session as revoked."""
        stmt = select(UserSession).where(UserSession.token_jti == jti)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session:
            session.is_revoked = True
            await self.db.commit()
            return True
        
        return False
    
    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> int:
        """Revoke all tokens for a user."""
        stmt = select(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_revoked == False
            )
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        
        count = 0
        for session in sessions:
            session.is_revoked = True
            count += 1
        
        await self.db.commit()
        return count
    
    async def create_tenant(self, tenant_data: TenantCreateSchema) -> Tenant:
        """Create a new tenant."""
        # Check if slug already exists
        existing_tenant = await self.get_tenant_by_slug(tenant_data.slug)
        if existing_tenant:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tenant slug already exists"
            )
        
        tenant = Tenant(**tenant_data.dict())
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        
        return tenant
    
    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        stmt = select(Tenant).where(Tenant.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_tenant_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID with tenant loaded."""
        stmt = select(User).options(selectinload(User.tenant)).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        stmt = select(User).options(selectinload(User.tenant)).where(User.email == email.lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_username_and_tenant(
        self, 
        username: str, 
        tenant_id: uuid.UUID
    ) -> Optional[User]:
        """Get user by username within a specific tenant."""
        stmt = select(User).options(selectinload(User.tenant)).where(
            and_(
                User.username == username.lower(),
                User.tenant_id == tenant_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_user(self, user_id: uuid.UUID, user_data: UserUpdateSchema) -> Optional[User]:
        """Update user information."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        update_data = user_data.dict(exclude_unset=True)
        
        # Check for username conflicts within tenant
        if "username" in update_data:
            existing_user = await self.get_user_by_username_and_tenant(
                update_data["username"], user.tenant_id
            )
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already exists in this tenant"
                )
        
        # Check for email conflicts globally
        if "email" in update_data:
            existing_user = await self.get_user_by_email(update_data["email"])
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered"
                )
        
        # Update user
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def update_tenant(
        self, 
        tenant_id: uuid.UUID, 
        tenant_data: TenantUpdateSchema
    ) -> Optional[Tenant]:
        """Update tenant information."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        
        update_data = tenant_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(tenant, field, value)
        
        tenant.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(tenant)
        
        return tenant
    
    async def change_password(
        self, 
        user_id: uuid.UUID, 
        current_password: str, 
        new_password: str
    ) -> bool:
        """Change user password."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Verify current password
        if not PasswordUtils.verify_password(current_password, user.password_hash):
            return False
        
        # Hash new password
        user.password_hash = PasswordUtils.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        # Revoke all existing tokens for security
        await self.revoke_all_user_tokens(user_id)
        
        return True
    
    async def list_tenant_users(
        self, 
        tenant_id: uuid.UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """List users in a tenant."""
        stmt = (
            select(User)
            .options(selectinload(User.tenant))
            .where(User.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .order_by(User.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def list_tenants(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        """List all tenants."""
        stmt = (
            select(Tenant)
            .offset(skip)
            .limit(limit)
            .order_by(Tenant.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        stmt = select(UserSession).where(
            UserSession.expires_at < datetime.utcnow()
        )
        result = await self.db.execute(stmt)
        expired_sessions = result.scalars().all()
        
        count = 0
        for session in expired_sessions:
            await self.db.delete(session)
            count += 1
        
        await self.db.commit()
        return count
