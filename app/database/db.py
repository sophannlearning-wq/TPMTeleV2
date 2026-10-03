from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.models import Base
engine=None;SessionLocal=None
def configure(url):
    global engine,SessionLocal
    engine=create_engine(url,pool_pre_ping=True)
    SessionLocal=sessionmaker(bind=engine,expire_on_commit=False)
    Base.metadata.create_all(engine)
