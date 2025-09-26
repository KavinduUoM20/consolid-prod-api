from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from apps.dociq.config import get_dociq_settings
import ssl

# Import models so SQLAlchemy can discover them
from apps.dociq.models import Template, Document, Extraction, TargetMapping
# Import auth models
from core.auth.models import Tenant, User, UserSession

settings = get_dociq_settings()

# Create async engine with explicit dialect and SSL handling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "server_settings": {
            "application_name": "consolidator_ai"
        },
        "ssl": False
    }
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_dociq_db():
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from apps.dociq.models import Template, Document, Extraction, TargetMapping
        from core.auth.models import Tenant, User, UserSession
        
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_dociq_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
