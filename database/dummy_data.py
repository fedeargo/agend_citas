# app/database/dummy_data.py
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid

# Base de datos dummy en memoria
DUMMY_DB = {
    "eps": [
        {"id": "eps_1", "name": "Sura EPS", "code": "SURA"},
        {"id": "eps_2", "name": "Sanitas EPS", "code": "SANITAS"},
        {"id": "eps_3", "name": "Compensar EPS", "code": "COMPENSAR"},
        {"id": "eps_4", "name": "Nueva EPS", "code": "NUEVA"},
        {"id": "eps_5", "name": "Famisanar EPS", "code": "FAMISANAR"},
    ],
    "specialties": [
        {"id": "spec_1", "name": "Medicina General", "description": "Consulta médica general"},
        {"id": "spec_2", "name": "Cardiología", "description": "Especialista en corazón"},
        {"id": "spec_3", "name": "Dermatología", "description": "Especialista en piel"},
        {"id": "spec_4", "name": "Ginecología", "description": "Especialista en salud femenina"},
        {"id": "spec_5", "name": "Pediatría", "description": "Especialista en niños"},
        {"id": "spec_6", "name": "Oftalmología", "description": "Especialista en ojos"},
        {"id": "spec_7", "name": "Psicología", "description": "Salud mental"},
        {"id": "spec_8", "name": "Ortopedia", "description": "Especialista en huesos y articulaciones"},
        {"id": "spec_9", "name": "Neurología", "description": "Especialista en sistema nervioso"},
    ],
    "doctors": [
        {"id": "doc_1", "name": "Dr. Juan Pérez", "specialty_id": "spec_1", "available_hours": ["09:00", "10:00", "11:00", "14:00", "15:00"]},
        {"id": "doc_2", "name": "Dr. María González", "specialty_id": "spec_2", "available_hours": ["08:00", "09:00", "10:00", "16:00"]},
        {"id": "doc_3", "name": "Dr. Carlos Rodríguez", "specialty_id": "spec_3", "available_hours": ["10:00", "11:00", "14:00", "15:00", "16:00"]},
        {"id": "doc_4", "name": "Dra. Ana López", "specialty_id": "spec_4", "available_hours": ["08:00", "09:00", "14:00", "15:00"]},
        {"id": "doc_5", "name": "Dr. Luis Martínez", "specialty_id": "spec_5", "available_hours": ["09:00", "10:00", "11:00", "15:00", "16:00"]},
        {"id": "doc_6", "name": "Dra. Sofia Hernández", "specialty_id": "spec_6", "available_hours": ["08:00", "10:00", "11:00", "14:00"]},
        {"id": "doc_7", "name": "Dr. Roberto Silva", "specialty_id": "spec_7", "available_hours": ["09:00", "10:00", "15:00", "16:00", "17:00"]},
    ],
    "appointments": []
}


def get_eps_list() -> List[Dict[str, Any]]:
    """Obtener lista completa de EPS"""
    return DUMMY_DB["eps"]

def get_specialties() -> List[Dict[str, Any]]:
    """Obtener lista completa de especialidades"""
    return DUMMY_DB["specialties"]


def get_doctors_by_specialty(specialty_id: str) -> List[Dict[str, Any]]:
    """Obtener médicos por especialidad"""
    return [doc for doc in DUMMY_DB["doctors"] if doc["specialty_id"] == specialty_id]

def get_available_slots(doctor_id: str, date: str) -> List[str]:
    """Obtener horarios disponibles para un médico en una fecha específica"""
    doctor = next((doc for doc in DUMMY_DB["doctors"] if doc["id"] == doctor_id), None)
    if not doctor:
        return []
    
    # Filtrar horarios ya ocupados
    occupied_slots = [
        apt["time"] for apt in DUMMY_DB["appointments"] 
        if apt["doctor_id"] == doctor_id and apt["date"] == date and apt["status"] == "confirmed"
    ]
    
    return [slot for slot in doctor["available_hours"] if slot not in occupied_slots]

def get_available_schedule_by_specialty(specialty_id: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
    """
    Obtener horarios disponibles por especialidad.
    
    Retorna una lista con los doctores de la especialidad, cada uno con sus fechas y horas disponibles.
    """
    doctors = get_doctors_by_specialty(specialty_id)
    available_schedule = []

    for doctor in doctors:
        doctor_schedule = {
            "doctor_id": doctor["id"],
            "doctor_name": doctor["name"],
            "available_dates": []
        }

        dates = get_available_dates_for_medic(doctor["id"], days_ahead)
        for date in dates:
            slots = get_available_slots(doctor["id"], date)
            doctor_schedule["available_dates"].append({
                "date": date,
                "available_hours": slots
            })

        if doctor_schedule["available_dates"]:
            available_schedule.append(doctor_schedule)

    return available_schedule


def get_available_dates_for_medic(doctor_id: str, days_ahead: int = 7) -> List[str]:
    """Obtener fechas disponibles para un médico"""
    dates = []
    for i in range(1, days_ahead + 1):
        date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        available_slots = get_available_slots(doctor_id, date)
        if available_slots:
            dates.append(date)
    return dates

def create_appointment(user_id: str, eps_id: str, specialty_id: str, doctor_id: str, date: str, time: str) -> Dict[str, Any]:
    """Crear una nueva cita"""
    # Verificar que el horario esté disponible
    available_slots = get_available_slots(doctor_id, date)
    if time not in available_slots:
        raise ValueError(f"El horario {time} no está disponible")
    
    appointment = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "eps_id": eps_id,
        "specialty_id": specialty_id,
        "doctor_id": doctor_id,
        "date": date,
        "time": time,
        "status": "confirmed",
        "created_at": datetime.now().isoformat()
    }
    
    DUMMY_DB["appointments"].append(appointment)
    return appointment

def get_user_appointments(user_id: str) -> List[Dict[str, Any]]:
    """Obtener citas de un usuario"""
    appointments = [apt for apt in DUMMY_DB["appointments"] if apt["user_id"] == user_id]
    
    # Enriquecer con información adicional
    enriched_appointments = []
    for apt in appointments:
        eps = next((e for e in DUMMY_DB["eps"] if e["id"] == apt["eps_id"]), {})
        specialty = next((s for s in DUMMY_DB["specialties"] if s["id"] == apt["specialty_id"]), {})
        doctor = next((d for d in DUMMY_DB["doctors"] if d["id"] == apt["doctor_id"]), {})
        
        enriched_apt = {
            **apt,
            "eps_name": eps.get("name", ""),
            "specialty_name": specialty.get("name", ""),
            "doctor_name": doctor.get("name", "")
        }
        enriched_appointments.append(enriched_apt)
    
    return enriched_appointments

def get_doctor_info(doctor_id: str) -> Optional[Dict[str, Any]]:
    """Obtener información de un médico"""
    return next((doc for doc in DUMMY_DB["doctors"] if doc["id"] == doctor_id), None)

def get_eps_info(eps_id: str) -> Optional[Dict[str, Any]]:
    """Obtener información de una EPS"""
    return next((eps for eps in DUMMY_DB["eps"] if eps["id"] == eps_id), None)

def get_specialty_info(specialty_id: str) -> Optional[Dict[str, Any]]:
    """Obtener información de una especialidad"""
    return next((spec for spec in DUMMY_DB["specialties"] if spec["id"] == specialty_id), None)
