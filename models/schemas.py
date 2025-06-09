from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None

class AppointmentRequest(BaseModel):
    user_message: str
    user_id: str

class AppointmentResponse(BaseModel):
    success: bool
    message: str
    thread_id: str

class EPSInfo(BaseModel):
    id: str
    name: str
    code: str

class Specialty(BaseModel):
    id: str
    name: str
    description: str

class Doctor(BaseModel):
    id: str
    name: str
    specialty_id: str
    available_hours: List[str]

class Appointment(BaseModel):
    id: str
    user_id: str
    eps_id: str
    specialty_id: str
    doctor_id: str
    date: str
    time: str
    status: str
    created_at: datetime
