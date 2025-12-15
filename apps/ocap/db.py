from sqlalchemy.ext.asyncio import AsyncSession
from apps.dociq.db import AsyncSessionLocal as DociqSessionLocal

# Import models so SQLAlchemy can discover them
from apps.ocap.models.technical_data import OCAPTechnicalData

# Reuse dociq's database connection - same database, different tables
AsyncSessionLocal = DociqSessionLocal

async def get_ocap_session() -> AsyncSession:
    """Get OCAP database session - reuses dociq's database connection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_ocap_db():
    """Initialize OCAP database (create tables if needed)."""
    # Note: We don't create tables since 'ocap' table already exists
    # OCAP uses the same database as dociq, just different tables
    pass
