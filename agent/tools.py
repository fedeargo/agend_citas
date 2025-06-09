from langchain_core.tools import tool
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from rapidfuzz import fuzz

from database.dummy_data import (
    get_eps_list, get_specialties,
    get_doctors_by_specialty, get_available_slots, get_available_dates_for_medic,
    create_appointment, get_user_appointments, get_doctor_info,
    get_eps_info, get_specialty_info
)

@tool
def list_eps() -> List[Dict[str, Any]]:
    """
    Obtener la lista completa de EPS disponibles.
    Útil cuando el usuario pregunta qué EPS están disponibles.
    """
    try:
        return get_eps_list()
    except Exception as e:
        print(f"Error in list_eps: {e}")
        return {"error": str(e)}

@tool
def search_similar_eps(query: str, top_n: int = 3) -> List[Dict[str, Any]]:
    """
    Obtener la EPS más similar en la base de datos con la que propone el usuario

    Args:
        query: Mensaje proporcionado por el usuario indicando una supuesta EPS
    
    Returns:
        EPS que cumplen con la mayor similaridad respecto a la proporcionada por el user
    """
    try:
        eps_list = DUMMY_DB["eps"]
        scored = []

        for eps in eps_list:
            name_score = fuzz.ratio(query.lower(), eps["name"].lower())
            scored.append((name_score, eps))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [item[1] for item in scored[:top_n]]
    except Exception as e:
        print(f"Error in search_similar_eps: {e}")
        return {"error": str(e)}

@tool
def list_specialties() -> List[Dict[str, Any]]:
    """
    Obtener la lista completa de especialidades médicas disponibles.
    Útil cuando el usuario pregunta qué especialidades están disponibles.
    """
    try:
        return get_specialties()
    except Exception as e:
        print(f"Error in list_specialties: {e}")
        return {"error": str(e)}

@tool
def search_similar_specialties(query: str, top_n: int = 3) -> List[Dict[str, Any]]:
    """
    Obtener la especialidad más similar en la base de datos con la que propone el usuario

    Args:
        query: Mensaje proporcionado por el usuario indicando una supuesta especialidad
    
    Returns:
        Especialidades que cumplen con la mayor similaridad respecto a la proporcionada por el user
    """
    try:
        specialties_list = DUMMY_DB["specialties"]
        scored = []

        for specialties in specialties_list:
            name_score = fuzz.ratio(query.lower(), specialties["name"].lower())
            scored.append((name_score, specialties))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [item[1] for item in scored[:top_n]]
    except Exception as e:
        print(f"Error in search_similar_specialties: {e}")
        return {"error": str(e)}

@tool
def get_doctors_for_specialty(specialty_id: str) -> List[Dict[str, Any]]:
    """
    Obtener médicos disponibles para una especialidad específica.
    
    Args:
        specialty_id: ID de la especialidad (ej: "spec_1", "spec_2")
    
    Returns:
        Lista de médicos que trabajan en esa especialidad
    """
    try:
        return get_doctors_by_specialty(specialty_id)
    except Exception as e:
        print(f"Error in get_doctors_for_specialty: {e}")
        return {"error": str(e)}

@tool
def search_similar_doctors(query: str, top_n: int = 3) -> List[Dict[str, Any]]:
    """
    Obtener al doctor más similar en la base de datos con la que propone el usuario

    Args:
        query: Mensaje proporcionado por el usuario indicando un supuesto doctor
    
    Returns:
        Doctores que cumplen con la mayor similaridad respecto a la proporcionada por el user
    """
    try:
        doctors_list = DUMMY_DB["doctors"]
        scored = []

        for doctors in doctors_list:
            name_score = fuzz.ratio(query.lower(), doctors["name"].lower())
            scored.append((name_score, doctors))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [item[1] for item in scored[:top_n]]
    except Exception as e:
        print(f"Error in search_similar_doctors: {e}")
        return {"error": str(e)}

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
    try:
        return get_available_slots(doctor_id, date)
    except Exception as e:
        print(f"Error in check_doctor_availability: {e}")
        return {"error": str(e)}

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
    try:
        return get_available_dates_for_medic(doctor_id, days_ahead)
    except Exception as e:
        print(f"Error in get_doctor_available_dates: {e}")
        return {"error": str(e)}

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
    try:
        return get_available_schedule_by_specialty(specialty_id, days_ahead)
    except Exception as e:
        print(f"Error in get_available_schedule_by_specialty: {e}")
        return {"error": str(e)}

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
        print(f"Error in schedule_appointment: {e}")
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
    try:
        return get_user_appointments(user_id)
    except Exception as e:
        print(f"Error in get_user_appointments_tool: {e}")
        return {"error": str(e)}

@tool
def get_current_date() -> str:
    """
    Obtener la fecha actual.
    
    Returns:
        Fecha actual en formato YYYY-MM-DD
    """
    try:
        return datetime.now().strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error in get_current_date: {e}")
        return {"error": str(e)}

@tool
def get_tomorrow_date() -> str:
    """
    Obtener la fecha de mañana.
    
    Returns:
        Fecha de mañana en formato YYYY-MM-DD
    """
    try:
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error in get_tomorrow_date: {e}")
        return {"error": str(e)}

# Lista de todas las herramientas disponibles
MEDICAL_TOOLS = [
    list_eps,
    search_similar_eps,
    list_specialties,
    search_similar_specialties,
    get_doctors_for_specialty,
    check_doctor_availability,
    get_doctor_available_dates,
    schedule_appointment,
    get_user_appointments_tool,
    get_current_date,
    get_tomorrow_date
]