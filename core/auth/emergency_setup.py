"""
Emergency setup routes for when initial auth setup fails.
These routes can be used to manually create the initial admin user.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.auth.services import AuthService
from core.auth.schemas import UserRegisterSchema, TenantCreateSchema
from core.auth.models import UserRole
from core.auth.dependencies import get_auth_db_session
from core.auth.config import get_auth_settings

router = APIRouter()


@router.post("/emergency-setup-tenant", 
             summary="Emergency: Create default tenant",
             description="Creates the default tenant if it doesn't exist. Use only if initial setup failed.")
async def emergency_create_tenant(
    auth_service: AuthService = Depends(lambda db=Depends(get_auth_db_session): AuthService(db))
):
    """Emergency route to create default tenant."""
    try:
        # Check if default tenant already exists
        existing_tenant = await auth_service.get_tenant_by_slug("default")
        if existing_tenant:
            return {"message": "Default tenant already exists", "tenant": existing_tenant.name}
        
        # Create default tenant
        tenant_data = TenantCreateSchema(
            name="Default Tenant",
            slug="default",
            description="Default tenant for the application",
            settings={}
        )
        
        tenant = await auth_service.create_tenant(tenant_data)
        return {
            "message": "Default tenant created successfully",
            "tenant_id": str(tenant.id),
            "tenant_slug": tenant.slug
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}"
        )


@router.post("/emergency-setup-admin",
             summary="Emergency: Create super admin user", 
             description="Creates the super admin user if it doesn't exist. Use only if initial setup failed.")
async def emergency_create_admin(
    auth_service: AuthService = Depends(lambda db=Depends(get_auth_db_session): AuthService(db))
):
    """Emergency route to create super admin user."""
    try:
        auth_settings = get_auth_settings()
        
        # Check if admin user already exists
        existing_admin = await auth_service.get_user_by_email(auth_settings.DEFAULT_ADMIN_EMAIL)
        if existing_admin:
            return {"message": "Admin user already exists", "username": existing_admin.username}
        
        # Ensure default tenant exists
        tenant = await auth_service.get_tenant_by_slug("default")
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Default tenant not found. Create tenant first using /emergency-setup-tenant"
            )
        
        # Create admin user with a simple password that definitely works
        user_data = UserRegisterSchema(
            username=auth_settings.DEFAULT_ADMIN_USERNAME,
            email=auth_settings.DEFAULT_ADMIN_EMAIL,
            password="TempAdmin123!",  # Simple password that will definitely work
            role=UserRole.SUPER_ADMIN
        )
        
        admin_user = await auth_service.register_user(user_data, tenant.slug)
        
        # Mark as verified
        admin_user.is_verified = True
        # We need to commit this change
        await auth_service.db.commit()
        
        return {
            "message": "Super admin created successfully",
            "username": admin_user.username,
            "email": admin_user.email,
            "temporary_password": "TempAdmin123!",
            "warning": "CHANGE THIS PASSWORD IMMEDIATELY using /auth/change-password"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create admin user: {str(e)}"
        )


@router.get("/emergency-status",
            summary="Check emergency setup status",
            description="Check if tenant and admin user exist")
async def emergency_status(
    auth_service: AuthService = Depends(lambda db=Depends(get_auth_db_session): AuthService(db))
):
    """Check the status of tenant and admin user."""
    try:
        auth_settings = get_auth_settings()
        
        # Check tenant
        tenant = await auth_service.get_tenant_by_slug("default")
        tenant_exists = tenant is not None
        
        # Check admin user
        admin_user = await auth_service.get_user_by_email(auth_settings.DEFAULT_ADMIN_EMAIL)
        admin_exists = admin_user is not None
        
        return {
            "default_tenant_exists": tenant_exists,
            "admin_user_exists": admin_exists,
            "setup_complete": tenant_exists and admin_exists,
            "next_steps": [
                "Create tenant: POST /emergency-setup-tenant" if not tenant_exists else "✅ Tenant exists",
                "Create admin: POST /emergency-setup-admin" if not admin_exists else "✅ Admin exists",
                "Change admin password: POST /auth/change-password" if admin_exists else "⏳ Create admin first"
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check status: {str(e)}"
        )
