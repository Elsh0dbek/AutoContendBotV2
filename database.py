from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()

Base.metadata.create_all(engine)