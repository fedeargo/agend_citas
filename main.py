from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os

from agent.agent import AppointmentAgent
from models.schemas import AppointmentRequest, AppointmentResponse, ChatMessage

app = FastAPI(
    title="Sistema de Agendamiento Médico para Assignement de Seguros Bolívar",
    description="Agente inteligente conversacional para agendamiento de citas médicas",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Inicializar el agente
appointment_agent = AppointmentAgent()


# Redirección a documentación interactiva de FastAPI
@app.get("/", response_class=RedirectResponse)
async def redirect_to_docs():
    return "/docs"


#Endpoint de apificación del agente
@app.post("/chat", response_model=AppointmentResponse)
async def chat_with_agent(request: AppointmentRequest):
    """
    Endpoint principal para chatear con el agente de agendamiento
    """
    try:
        result = await appointment_agent.chat(
            message=request.user_message,
            user_id=request.user_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Para obtener listado de EPS disponibles en DB
@app.get("/eps")
async def get_eps_list():
    """Obtener lista de EPS disponibles"""
    from database.dummy_data import get_eps_list
    return {"eps_list": get_eps_list()}


# Para obtener listado de especialidades disponibles en DB
@app.get("/specialties")
async def get_specialties():
    """Obtener lista de especialidades disponibles"""
    from database.dummy_data import get_specialties
    return {"specialties": get_specialties()}


# Para obtener listado de citas por user_id
@app.get("/appointments/{user_id}")
async def get_user_appointments(user_id: str):
    """Obtener citas de un usuario"""
    from database.dummy_data import get_user_appointments
    return {"appointments": get_user_appointments(user_id)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)