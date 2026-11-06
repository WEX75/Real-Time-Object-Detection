#leaga baza de date de rute si expune endpoint urile.

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from . import database, schemas

# Generam tabelele in SQLite la pornire
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Vigilo API")

# Dependency pentru a deschide/inchide sesiunea DB la fiecare request
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "Vigilo API is running"}

@app.post("/zones/", response_model=schemas.ZoneResponse)
def create_zone(zone: schemas.ZoneCreate, db: Session = Depends(get_db)):
    db_zone = database.ZoneDB(name=zone.name, coordinates=zone.coordinates)
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)
    return db_zone

@app.post("/rules/", response_model=schemas.RuleResponse)
def create_rule(rule: schemas.RuleCreate, db: Session = Depends(get_db)):
    db_rule = database.RuleDB(
        zone_name=rule.zone_name, 
        target_object=rule.target_object, 
        condition=rule.condition
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@app.post("/ingest/")
def ingest_detections(detections: list[schemas.DetectionEvent]):
    # Aici vom integra logica din detector.py pentru a evalua regulile
    return {"status": "success", "objects_detected": len(detections)}