from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# engine es el puente de comunicación con Supabase
engine = create_engine(
    make_url(settings.DATABASE_URL).set(drivername="postgresql+psycopg2"),
    pool_pre_ping=True,  # Verifica que la conexión esté viva antes de usarla
    pool_size=5,  # Límite de conexiones concurrentes para no saturar Supabase
    max_overflow=10,
)

# SessionLocal es la clase que generará las sesiones individuales por cada request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
