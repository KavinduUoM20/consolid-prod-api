import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey, Index
import sqlalchemy.dialects.postgresql as pg


class Tenant(SQLModel, table=True):
    """Tenant model for multi-tenancy support."""
    __tablename__ = "tenants"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False)
    )
    name: str = Field(sa_column=Column(pg.VARCHAR(255), nullable=False))
    slug: str = Field(sa_column=Column(pg.VARCHAR(100), unique=True, nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(pg.TEXT, nullable=True))
    is_active: bool = Field(default=True, sa_column=Column(pg.BOOLEAN, nullable=False, default=True))
    settings: dict = Field(default_factory=dict, sa_column=Column(pg.JSONB, nullable=False, default={}))
    
    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    
    # Relationships
    users: List["User"] = Relationship(back_populates="tenant")
    
    def __repr__(self):
        return f"<Tenant {self.name} ({self.slug})>"


class User(SQLModel, table=True):
    """User model with role-based access and tenant association."""
    __tablename__ = "users"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False)
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    )
    username: str = Field(sa_column=Column(pg.VARCHAR(100), nullable=False))
    email: str = Field(sa_column=Column(pg.VARCHAR(255), unique=True, nullable=False))
    password_hash: str = Field(sa_column=Column(pg.VARCHAR(255), nullable=False))
    role: str = Field(default="user", sa_column=Column(pg.VARCHAR(50), nullable=False, default="user"))
    is_active: bool = Field(default=True, sa_column=Column(pg.BOOLEAN, nullable=False, default=True))
    is_verified: bool = Field(default=False, sa_column=Column(pg.BOOLEAN, nullable=False, default=False))
    last_login: Optional[datetime] = Field(default=None, sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=True))
    
    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    
    # Relationships
    tenant: Tenant = Relationship(back_populates="users")
    sessions: List["UserSession"] = Relationship(back_populates="user", cascade_delete=True)
    
    def __repr__(self):
        return f"<User {self.username} ({self.email})>"
    
    # Table constraints and indexes
    __table_args__ = (
        Index('idx_users_tenant_username', 'tenant_id', 'username', unique=True),
        Index('idx_users_email', 'email'),
        Index('idx_users_tenant_id', 'tenant_id'),
        Index('idx_users_role', 'role'),
    )


class UserSession(SQLModel, table=True):
    """User session model for JWT token management and blacklisting."""
    __tablename__ = "user_sessions"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    )
    token_jti: str = Field(sa_column=Column(pg.VARCHAR(255), unique=True, nullable=False))  # JWT ID
    expires_at: datetime = Field(sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False))
    is_revoked: bool = Field(default=False, sa_column=Column(pg.BOOLEAN, nullable=False, default=False))
    
    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    )
    
    # Relationships
    user: User = Relationship(back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession {self.token_jti} (user: {self.user_id})>"
    
    # Table constraints and indexes
    __table_args__ = (
        Index('idx_user_sessions_user_id', 'user_id'),
        Index('idx_user_sessions_token_jti', 'token_jti'),
        Index('idx_user_sessions_expires_at', 'expires_at'),
        Index('idx_user_sessions_revoked', 'is_revoked'),
    )


# Define user roles as constants
class UserRole:
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    USER = "user"
    VIEWER = "viewer"
    
    @classmethod
    def all_roles(cls) -> List[str]:
        return [cls.SUPER_ADMIN, cls.TENANT_ADMIN, cls.USER, cls.VIEWER]
    
    @classmethod
    def is_valid_role(cls, role: str) -> bool:
        return role in cls.all_roles()
