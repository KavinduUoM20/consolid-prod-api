from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.security import HTTPAuthorizationCredentials

from core.auth.models import User, Tenant, UserRole
from core.auth.schemas import (
    UserRegisterSchema,
    UserLoginSchema,
    TenantCreateSchema,
    TenantUpdateSchema,
    UserUpdateSchema,
    PasswordChangeSchema,
    TokenResponseSchema,
    UserResponseSchema,
    TenantResponseSchema,
    ErrorResponseSchema
)
from core.auth.services import AuthService
from core.auth.dependencies import (
    get_auth_service,
    get_current_user,
    get_current_active_user,
    get_current_user_optional,
    require_role,
    require_tenant_admin,
    require_super_admin,
    security
)


router = APIRouter()


@router.post("/register", 
             response_model=UserResponseSchema,
             status_code=status.HTTP_201_CREATED,
             summary="Register a new user",
             description="Register a new user account with username, email, and password")
async def register(
    user_data: UserRegisterSchema,
    tenant_slug: str = Query(default="default", description="Tenant slug"),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user."""
    try:
        user = await auth_service.register_user(user_data, tenant_slug)
        return UserResponseSchema.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login",
             response_model=TokenResponseSchema,
             summary="User login",
             description="Authenticate user and return access token")
async def login(
    credentials: UserLoginSchema,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate user and return access token."""
    user = await auth_service.authenticate_user(
        credentials.username,
        credentials.password,
        credentials.tenant_slug or "default"
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token, jti, expires_in = await auth_service.create_access_token(user)
    
    return TokenResponseSchema(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponseSchema.from_orm(user)
    )


@router.post("/logout",
             status_code=status.HTTP_200_OK,
             summary="User logout",
             description="Logout user and revoke current token")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout user and revoke current token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Extract JTI from token
    from core.auth.utils import JWTUtils
    token_data = JWTUtils.verify_token(credentials.credentials)
    
    if token_data:
        await auth_service.revoke_token(token_data.jti)
    
    return {"message": "Successfully logged out"}


@router.get("/me",
            response_model=UserResponseSchema,
            summary="Get current user",
            description="Get current authenticated user information")
async def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    return UserResponseSchema.from_orm(current_user)


@router.put("/me",
            response_model=UserResponseSchema,
            summary="Update current user",
            description="Update current user information")
async def update_me(
    user_update: UserUpdateSchema,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update current user information."""
    # Users can only update their own basic info, not role/status
    restricted_update = UserUpdateSchema(
        username=user_update.username,
        email=user_update.email
    )
    
    updated_user = await auth_service.update_user(current_user.id, restricted_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponseSchema.from_orm(updated_user)


@router.post("/change-password",
             status_code=status.HTTP_200_OK,
             summary="Change password",
             description="Change current user password")
async def change_password(
    password_data: PasswordChangeSchema,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Change current user password."""
    success = await auth_service.change_password(
        current_user.id,
        password_data.current_password,
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    return {"message": "Password changed successfully"}


# Tenant Management Routes
@router.post("/tenants",
             response_model=TenantResponseSchema,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_super_admin())],
             summary="Create tenant",
             description="Create a new tenant (Super admin only)")
async def create_tenant(
    tenant_data: TenantCreateSchema,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Create a new tenant."""
    try:
        tenant = await auth_service.create_tenant(tenant_data)
        return TenantResponseSchema.from_orm(tenant)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant creation failed"
        )


@router.get("/tenants",
            response_model=List[TenantResponseSchema],
            dependencies=[Depends(require_super_admin())],
            summary="List tenants",
            description="List all tenants (Super admin only)")
async def list_tenants(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    auth_service: AuthService = Depends(get_auth_service)
):
    """List all tenants."""
    tenants = await auth_service.list_tenants(skip=skip, limit=limit)
    return [TenantResponseSchema.from_orm(tenant) for tenant in tenants]


@router.get("/tenants/{tenant_slug}",
            response_model=TenantResponseSchema,
            summary="Get tenant",
            description="Get tenant information")
async def get_tenant(
    tenant_slug: str = Path(..., description="Tenant slug"),
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get tenant information."""
    # Users can only see their own tenant unless they're super admin
    if current_user.role != UserRole.SUPER_ADMIN:
        if current_user.tenant.slug != tenant_slug:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    tenant = await auth_service.get_tenant_by_slug(tenant_slug)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return TenantResponseSchema.from_orm(tenant)


@router.put("/tenants/{tenant_slug}",
            response_model=TenantResponseSchema,
            dependencies=[Depends(require_super_admin())],
            summary="Update tenant",
            description="Update tenant information (Super admin only)")
async def update_tenant(
    tenant_update: TenantUpdateSchema,
    tenant_slug: str = Path(..., description="Tenant slug"),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update tenant information."""
    tenant = await auth_service.get_tenant_by_slug(tenant_slug)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    updated_tenant = await auth_service.update_tenant(tenant.id, tenant_update)
    if not updated_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return TenantResponseSchema.from_orm(updated_tenant)


# User Management Routes
@router.get("/tenants/{tenant_slug}/users",
            response_model=List[UserResponseSchema],
            dependencies=[Depends(require_tenant_admin())],
            summary="List tenant users",
            description="List users in a tenant (Tenant admin or Super admin only)")
async def list_tenant_users(
    tenant_slug: str = Path(..., description="Tenant slug"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """List users in a tenant."""
    # Tenant admins can only see users in their own tenant
    if current_user.role == UserRole.TENANT_ADMIN:
        if current_user.tenant.slug != tenant_slug:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    tenant = await auth_service.get_tenant_by_slug(tenant_slug)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    users = await auth_service.list_tenant_users(tenant.id, skip=skip, limit=limit)
    return [UserResponseSchema.from_orm(user) for user in users]


@router.get("/users/{user_id}",
            response_model=UserResponseSchema,
            summary="Get user",
            description="Get user information")
async def get_user(
    user_id: str = Path(..., description="User ID"),
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get user information."""
    import uuid
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Users can only see themselves unless they're admin
    if current_user.role not in [UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN]:
        if current_user.id != user_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    user = await auth_service.get_user_by_id(user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Tenant admins can only see users in their tenant
    if current_user.role == UserRole.TENANT_ADMIN:
        if user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return UserResponseSchema.from_orm(user)


@router.put("/users/{user_id}",
            response_model=UserResponseSchema,
            dependencies=[Depends(require_tenant_admin())],
            summary="Update user",
            description="Update user information (Tenant admin or Super admin only)")
async def update_user(
    user_update: UserUpdateSchema,
    user_id: str = Path(..., description="User ID"),
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update user information."""
    import uuid
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    user = await auth_service.get_user_by_id(user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Tenant admins can only update users in their tenant
    if current_user.role == UserRole.TENANT_ADMIN:
        if user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Tenant admins cannot promote users to super admin
        if user_update.role == UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot assign super admin role"
            )
    
    updated_user = await auth_service.update_user(user_uuid, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponseSchema.from_orm(updated_user)


# Admin utility routes
@router.post("/admin/cleanup-sessions",
             dependencies=[Depends(require_super_admin())],
             summary="Cleanup expired sessions",
             description="Remove expired user sessions (Super admin only)")
async def cleanup_expired_sessions(
    auth_service: AuthService = Depends(get_auth_service)
):
    """Cleanup expired user sessions."""
    count = await auth_service.cleanup_expired_sessions()
    return {"message": f"Cleaned up {count} expired sessions"}


@router.post("/admin/revoke-user-tokens/{user_id}",
             dependencies=[Depends(require_super_admin())],
             summary="Revoke user tokens",
             description="Revoke all tokens for a specific user (Super admin only)")
async def revoke_user_tokens(
    user_id: str = Path(..., description="User ID"),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Revoke all tokens for a specific user."""
    import uuid
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    user = await auth_service.get_user_by_id(user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    count = await auth_service.revoke_all_user_tokens(user_uuid)
    return {"message": f"Revoked {count} tokens for user {user.username}"}
