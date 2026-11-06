#configurez conexiunea la SQL si definesc tabelele pentru Zone si Reguli.

from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Creeaza fisierul vigilo.db in folderul backend
SQLALCHEMY_DATABASE_URL = "sqlite:///./vigilo.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ZoneDB(Base):
    __tablename__ = "zones"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    coordinates = Column(JSON)  # Salvam lista [x1, y1, x2, y2] ca JSON

class RuleDB(Base):
    __tablename__ = "rules"
    
    id = Column(Integer, primary_key=True, index=True)
    zone_name = Column(String, index=True)
    target_object = Column(String)
    condition = Column(String)  # Ex: "present", "missing", "count>0"