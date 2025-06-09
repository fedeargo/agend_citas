from langchain_core.tools import tool
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from rapidfuzz import fuzz

from database.dummy_data import (
    get_eps_list, get_specialties,
    get_doctors_by_specialty, get_available_slots, get_available_dates,
    create_appointment, get_user_appointments, get_doctor_info,
    get_eps_info, get_specialty_info
)

@tool
def list_eps() -> List[Dict[str, Any]]:
    """
    Obtener la lista completa de EPS disponibles.
    Útil cuando el usuario pregunta qué EPS están disponibles.
    """
    return get_eps_list()

@tool
def search_similar_eps(query: str, top_n: int = 3) -> List[Dict[str, Any]]:
    """
    Obtener la EPS más similar en la base de datos con la que propone el usuario

    Args:
        query: Mensaje proporcionado por el usuario indicando una supuesta EPS
    
    Returns:
        EPS que cumplen con la mayor similaridad respecto a la proporcionada por el user
    """
    eps_list = DUMMY_DB["eps"]
    scored = []

    for eps in eps_list:
        name_score = fuzz.ratio(query.lower(), eps["name"].lower())
        scored.append((name_score, eps))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [item[1] for item in scored[:top_n]]

@tool
def list_specialties() -> List[Dict[str, Any]]:
    """
    Obtener la lista completa de especialidades médicas disponibles.
    Útil cuando el usuario pregunta qué especialidades están disponibles.
    """
    return get_specialties()

@tool
def search_similar_specialities(query: str, top_n: int = 3) -> List[Dict[str, Any]]:
    """
    Obtener la especialidad más similar en la base de datos con la que propone el usuario

    Args:
        query: Mensaje proporcionado por el usuario indicando una supuesta especialidad
    
    Returns:
        Especialidades que cumplen con la mayor similaridad respecto a la proporcionada por el user
    """
    specialities_list = DUMMY_DB["specialities"]
    scored = []

    for specialities in specialities_list:
        name_score = fuzz.ratio(query.lower(), specialities["name"].lower())
        scored.append((name_score, eps))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [item[1] for item in scored[:top_n]]

@tool
def get_doctors_for_specialty(specialty_id: str) -> List[Dict[str, Any]]:
    """
    Obtener médicos disponibles para una especialidad específica.
    
    Args:
        specialty_id: ID de la especialidad (ej: "spec_1", "spec_2")
    
    Returns:
        Lista de médicos que trabajan en esa especialidad
    """
    return get_doctors_by_specialty(specialty_id)

@tool
def search_similar_doctors(query: str, top_n: int = 3) -> List[Dict[str, Any]]:
    """
    Obtener al doctor más similar en la base de datos con la que propone el usuario

    Args:
        query: Mensaje proporcionado por el usuario indicando un supuesto doctor
    
    Returns:
        Doctores que cumplen con la mayor similaridad respecto a la proporcionada por el user
    """
    doctors_list = DUMMY_DB["doctors"]
    scored = []

    for doctors in doctors_list:
        name_score = fuzz.ratio(query.lower(), doctors["name"].lower())
        scored.append((name_score, eps))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [item[1] for item in scored[:top_n]]

@tool
def check_doctor_availability(doctor_id: str, date: str) -> List[str]:
    """
    Verificar los horarios disponibles de un médico en una fecha específica.
    
    Args:
        doctor_id: ID del médico
        date: Fecha en formato YYYY-MM-DD
    
    Returns:
        Lista de horarios disponibles (ej: ["09:00", "10:00", "11:00"])
    """
    return get_available_slots(doctor_id, date)

@tool
def get_doctor_available_dates(doctor_id: str, days_ahead: int = 7) -> List[str]:
    """
    Obtener las fechas disponibles para un médico en los próximos días.
    
    Args:
        doctor_id: ID del médico
        days_ahead: Número de días hacia adelante a verificar (por defecto 7)
    
    Returns:
        Lista de fechas disponibles en formato YYYY-MM-DD
    """
    return get_available_dates(doctor_id, days_ahead)

@tool
def get_available_schedule_by_specialty(specialty_id: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
    """
    Obtener horarios disponibles por especialidad.
    
    Retorna una lista con los doctores de la especialidad, cada uno con sus fechas y horas disponibles.
    
    Args:
        specialty_id: ID de la especialidad
        days_ahead: Número de días hacia adelante a verificar (por defecto 7)
    
    Returns:
        Lista de doctores con sus fechas y horas disponibles
    """
    return get_available_schedule_by_specialty(specialty_id, days_ahead)

@tool
def schedule_appointment(user_id: str, eps_id: str, specialty_id: str, doctor_id: str, date: str, time: str) -> Dict[str, Any]:
    """
    Crear una nueva cita médica.
    
    Args:
        user_id: ID del usuario
        eps_id: ID de la EPS
        specialty_id: ID de la especialidad
        doctor_id: ID del médico
        date: Fecha de la cita (YYYY-MM-DD)
        time: Hora de la cita (HH:MM)
    
    Returns:
        Información de la cita creada
    """
    try:
        appointment = create_appointment(user_id, eps_id, specialty_id, doctor_id, date, time)
        
        # Enriquecer con información adicional
        eps_info = get_eps_info(eps_id)
        specialty_info = get_specialty_info(specialty_id)
        doctor_info = get_doctor_info(doctor_id)
        
        return {
            **appointment,
            "eps_name": eps_info["name"] if eps_info else "",
            "specialty_name": specialty_info["name"] if specialty_info else "",
            "doctor_name": doctor_info["name"] if doctor_info else ""
        }
    except Exception as e:
        return {"error": str(e)}

@tool
def get_user_appointments_tool(user_id: str) -> List[Dict[str, Any]]:
    """
    Obtener todas las citas de un usuario.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        Lista de citas del usuario con información completa
    """
    return get_user_appointments(user_id)

@tool
def get_current_date() -> str:
    """
    Obtener la fecha actual.
    
    Returns:
        Fecha actual en formato YYYY-MM-DD
    """
    return datetime.now().strftime("%Y-%m-%d")

@tool
def get_tomorrow_date() -> str:
    """
    Obtener la fecha de mañana.
    
    Returns:
        Fecha de mañana en formato YYYY-MM-DD
    """
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

# Lista de todas las herramientas disponibles
MEDICAL_TOOLS = [
    list_eps,
    search_similar_eps,
    list_specialties,
    search_similar_specialities,
    get_doctors_for_specialty,
    check_doctor_availability,
    get_doctor_available_dates,
    schedule_appointment,
    get_user_appointments_tool,
    get_current_date,
    get_tomorrow_date
]