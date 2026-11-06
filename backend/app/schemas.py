#definirea datelor. Acestea controleaza strict de json uri 
# intra dispre interfata lui Carol si dinspre modelul Ml al lui Darius.

from pydantic import BaseModel
from typing import List

# --- Structuri pentru Zone ---
class ZoneCreate(BaseModel):
    name: str
    coordinates: List[float]  # [x_min, y_min, x_max, y_max]

class ZoneResponse(ZoneCreate):
    id: int
    class Config:
        from_attributes = True

# --- Structuri pentru Reguli ---
class RuleCreate(BaseModel):
    zone_name: str
    target_object: str
    condition: str

class RuleResponse(RuleCreate):
    id: int
    class Config:
        from_attributes = True

# --- Structura pentru ML (Darius) ---
class DetectionEvent(BaseModel):
    label: str
    confidence: float
    bbox: List[float]  # [x_min, y_min, x_max, y_max]