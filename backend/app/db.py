import boto3
from botocore.client import Config as BotoConfig
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=20)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with SessionLocal() as session:
        yield session


_s3_client = None


def get_s3():
    """Client for the immutable raw-evidence object store (S3-compatible)."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=BotoConfig(signature_version="s3v4"),
            region_name="us-east-1",
        )
    return _s3_client


def ensure_bucket(retries: int = 20, delay: float = 3.0) -> None:
    """Create the raw-evidence bucket, waiting for the object store to come
    up. Called from API and worker startup — whoever boots first creates it."""
    import time

    for attempt in range(retries):
        try:
            s3 = get_s3()
            s3.head_bucket(Bucket=settings.s3_bucket)
            return
        except Exception:
            try:
                get_s3().create_bucket(Bucket=settings.s3_bucket)
                return
            except Exception:
                if attempt == retries - 1:
                    raise
                time.sleep(delay)
