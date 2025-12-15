from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.models import User, Tenant, UserRole
from core.auth.services import AuthService
from apps.dociq.db import AsyncSessionLocal


# OAuth2 scheme for JWT tokens
security = HTTPBearer(auto_error=False)


async def get_auth_db_session() -> AsyncSession:
    """Get database session for auth operations."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_auth_service(
    db: AsyncSession = Depends(get_auth_db_session)
) -> AuthService:
    """Get auth service instance."""
    return AuthService(db)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[User]:
    """
    Get current user from JWT token (optional).
    Returns None if no token or invalid token.
    """
    if not credentials:
        return None
    
    try:
        user = await auth_service.verify_token(credentials.credentials)
        return user
    except Exception:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """
    Get current user from JWT token (required).
    Raises HTTPException if no token or invalid token.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await auth_service.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    Raises HTTPException if user is not active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current verified user.
    Raises HTTPException if user is not verified.
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not verified"
        )
    
    return current_user


def require_role(required_roles: List[str]):
    """
    Dependency factory to require specific user roles.
    
    Args:
        required_roles: List of roles that are allowed
    
    Returns:
        Dependency function that checks user role
    """
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(required_roles)}"
            )
        return current_user
    
    return role_checker


def require_tenant_admin():
    """Dependency to require tenant admin role or higher."""
    return require_role([UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN])


def require_super_admin():
    """Dependency to require super admin role."""
    return require_role([UserRole.SUPER_ADMIN])


async def get_current_tenant(
    current_user: User = Depends(get_current_active_user)
) -> Tenant:
    """Get current user's tenant."""
    return current_user.tenant


async def get_tenant_from_slug(
    tenant_slug: str,
    auth_service: AuthService = Depends(get_auth_service)
) -> Tenant:
    """
    Get tenant by slug.
    Raises HTTPException if tenant not found.
    """
    tenant = await auth_service.get_tenant_by_slug(tenant_slug)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_slug}' not found"
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not active"
        )
    
    return tenant


def require_same_tenant():
    """
    Dependency to ensure user belongs to the requested tenant.
    Used for tenant-specific operations.
    """
    def tenant_checker(
        tenant_slug: str,
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.tenant.slug != tenant_slug:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: User does not belong to this tenant"
            )
        return current_user
    
    return tenant_checker


def require_same_tenant_or_super_admin():
    """
    Dependency to ensure user belongs to the requested tenant OR is super admin.
    Used for cross-tenant operations by super admins.
    """
    def tenant_or_admin_checker(
        tenant_slug: str,
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role == UserRole.SUPER_ADMIN:
            return current_user
        
        if current_user.tenant.slug != tenant_slug:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: User does not belong to this tenant"
            )
        return current_user
    
    return tenant_or_admin_checker


async def get_tenant_from_request(request: Request) -> Optional[str]:
    """
    Extract tenant slug from request.
    Can be from subdomain, header, or path parameter.
    """
    # Try to get from header first
    tenant_slug = request.headers.get("X-Tenant-Slug")
    if tenant_slug:
        return tenant_slug
    
    # Try to get from subdomain
    host = request.headers.get("host", "")
    if "." in host:
        subdomain = host.split(".")[0]
        if subdomain and subdomain != "www" and subdomain != "api":
            return subdomain
    
    # Try to get from path parameter (this would be set by the route)
    path_params = request.path_params
    if "tenant_slug" in path_params:
        return path_params["tenant_slug"]
    
    # Default tenant
    return "default"


class RoleChecker:
    """Class-based role checker for more complex role requirements."""
    
    def __init__(self, allowed_roles: List[str], require_same_tenant: bool = True):
        self.allowed_roles = allowed_roles
        self.require_same_tenant = require_same_tenant
    
    def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        tenant_slug: Optional[str] = None
    ) -> User:
        # Check role
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(self.allowed_roles)}"
            )
        
        # Check tenant if required
        if self.require_same_tenant and tenant_slug:
            if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant.slug != tenant_slug:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: User does not belong to this tenant"
                )
        
        return current_user


# Pre-configured role checkers
require_user_or_admin = RoleChecker([UserRole.USER, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN])
require_admin = RoleChecker([UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN])
require_super_admin_only = RoleChecker([UserRole.SUPER_ADMIN], require_same_tenant=False)
