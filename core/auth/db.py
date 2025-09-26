from sqlalchemy.ext.asyncio import AsyncSession
from apps.dociq.db import AsyncSessionLocal, engine
from sqlmodel import SQLModel

# Import all auth models so SQLAlchemy can discover them
from core.auth.models import Tenant, User, UserSession


async def get_auth_session() -> AsyncSession:
    """Get auth database session - reuses dociq's database connection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_auth_db():
    """Initialize auth database (create tables if needed)."""
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from core.auth.models import Tenant, User, UserSession
        
        # Create all auth tables
        await conn.run_sync(SQLModel.metadata.create_all)


async def create_default_tenant():
    """Create default tenant if it doesn't exist."""
    from core.auth.services import AuthService
    from core.auth.schemas import TenantCreateSchema
    
    async with AsyncSessionLocal() as session:
        auth_service = AuthService(session)
        
        # Check if default tenant exists
        default_tenant = await auth_service.get_tenant_by_slug("default")
        
        if not default_tenant:
            tenant_data = TenantCreateSchema(
                name="Default Tenant",
                slug="default",
                description="Default tenant for the application",
                settings={}
            )
            
            default_tenant = await auth_service.create_tenant(tenant_data)
            print(f"Created default tenant: {default_tenant.name}")
            
            return default_tenant
        
        return default_tenant


async def create_super_admin(
    username: str = None,
    email: str = None,
    password: str = None,
    tenant_slug: str = None
):
    """Create a super admin user if it doesn't exist."""
    from core.auth.services import AuthService
    from core.auth.schemas import UserRegisterSchema
    from core.auth.models import UserRole
    from core.auth.config import get_auth_settings
    
    # Get settings with defaults
    auth_settings = get_auth_settings()
    username = username or auth_settings.DEFAULT_ADMIN_USERNAME
    email = email or auth_settings.DEFAULT_ADMIN_EMAIL
    password = password or auth_settings.DEFAULT_ADMIN_PASSWORD
    tenant_slug = tenant_slug or auth_settings.DEFAULT_TENANT_SLUG
    
    async with AsyncSessionLocal() as session:
        auth_service = AuthService(session)
        
        # Check if super admin exists
        existing_admin = await auth_service.get_user_by_email(email)
        
        if not existing_admin:
            user_data = UserRegisterSchema(
                username=username,
                email=email,
                password=password,
                role=UserRole.SUPER_ADMIN
            )
            
            admin_user = await auth_service.register_user(user_data, tenant_slug)
            
            # Mark as verified
            admin_user.is_verified = True
            await session.commit()
            
            print(f"Created super admin user: {admin_user.username} ({admin_user.email})")
            return admin_user
        
        return existing_admin


async def setup_initial_data():
    """Setup initial data including default tenant and super admin."""
    try:
        print("Setting up initial auth data...")
        
        # Create default tenant
        default_tenant = await create_default_tenant()
        
        # Create super admin
        admin_user = await create_super_admin()
        
        print("Initial auth data setup completed!")
        return default_tenant, admin_user
    except Exception as e:
        print(f"Error setting up initial auth data: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise
