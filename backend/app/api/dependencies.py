from app.db.session import SessionLocal # Asumiendo que configuraste sessionmaker aquí

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()