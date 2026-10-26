from sqlmodel import Session, SQLModel, create_engine

from . import settings

if settings.DB_URL.startswith("sqlite"):
    engine = create_engine(settings.DB_URL, connect_args={"check_same_thread": False})
else:
    # Serverless: don't hold connections between invocations
    from sqlalchemy.pool import NullPool

    engine = create_engine(settings.DB_URL, poolclass=NullPool, pool_pre_ping=True)


def init_db(drop: bool = False) -> None:
    from . import models  # noqa: F401  registers tables

    if drop:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
