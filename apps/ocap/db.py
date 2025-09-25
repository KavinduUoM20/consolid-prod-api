from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from apps.ocap.config import get_ocap_settings

# Import models so SQLAlchemy can discover them
from apps.ocap.models.technical_data import OCAPTechnicalData

settings = get_ocap_settings()

# Create async engine with same configuration as dociq
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "server_settings": {
            "application_name": "ocap_assistant"
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

async def get_ocap_session() -> AsyncSession:
    """Get OCAP database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_ocap_db():
    """Initialize OCAP database (create tables if needed)."""
    async with engine.begin() as conn:
        # Note: We don't create tables since 'ocap' table already exists
        # This is just for potential future use
        pass
