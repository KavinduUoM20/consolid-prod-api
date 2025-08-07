from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from apps.ragchat.config import get_ragchat_settings
import ssl

# Import models so SQLAlchemy can discover them
from apps.ragchat.models import ChatSession, Message, Document

settings = get_ragchat_settings()

# Create async engine with explicit dialect and SSL handling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "server_settings": {
            "application_name": "ragchat_ai"
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

async def init_ragchat_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_ragchat_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 