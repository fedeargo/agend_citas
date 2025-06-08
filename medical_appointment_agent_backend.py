from typing import TypedDict, Annotated, List
import operator
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import re
from enum import Enum
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os

# Estados del agente
class ConversationState(str, Enum):
    GREETING = "greeting"
    IDENTIFY_INTENTION = "identify_intention"
    REQUEST_DOCUMENT = "request_document"
    REQUEST_EPS_SPECIALTY = "request_eps_specialty"
    FAREWELL = "farewell"
    OFF_TOPIC = "off_topic"

# Estado del grafo
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    current_state: str
    patient_data: dict
    conversation_complete: bool

# Modelos Pydantic
class ChatMessage(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    state: str
    patient_data: dict
    conversation_complete: bool

# Clase principal del agente
class MedicalAppointmentAgent:
    def __init__(self, openai_api_key: str = None):
        self.llm = ChatOpenAI(
            api_key=openai_api_key or os.getenv("OPENAI_API_KEY"),
            model="gpt-3.5-turbo",
            temperature=0.3
        )
        self.graph = self._create_graph()
        
    def _create_graph(self):
        workflow = StateGraph(AgentState)
        
        # Agregar nodos
        workflow.add_node("greeting", self.greeting_node)
        workflow.add_node("identify_intention", self.identify_intention_node)
        workflow.add_node("request_document", self.request_document_node)
        workflow.add_node("request_eps_specialty", self.request_eps_specialty_node)
        workflow.add_node("farewell", self.farewell_node)
        workflow.add_node("off_topic", self.off_topic_node)
        
        # Definir punto de entrada
        workflow.set_entry_point("greeting")
        
        # Agregar aristas condicionales
        workflow.add_conditional_edges(
            "greeting",
            self.route_after_greeting,
            {
                "identify_intention": "identify_intention",
                "off_topic": "off_topic"
            }
        )
        
        workflow.add_conditional_edges(
            "identify_intention",
            self.route_after_intention,
            {
                "request_document": "request_document",
                "off_topic": "off_topic"
            }
        )
        
        workflow.add_conditional_edges(
            "request_document",
            self.route_after_document,
            {
                "request_eps_specialty": "request_eps_specialty",
                "request_document": "request_document"
            }
        )
        
        workflow.add_conditional_edges(
            "request_eps_specialty",
            self.route_after_eps_specialty,
            {
                "farewell": "farewell",
                "request_eps_specialty": "request_eps_specialty"
            }
        )
        
        workflow.add_edge("farewell", END)
        workflow.add_edge("off_topic", END)
        
        return workflow.compile()
    
    def greeting_node(self, state: AgentState):
        """Nodo de saludo inicial"""
        if state["current_state"] == "":
            greeting_prompt = ChatPromptTemplate.from_template(
                """Eres un asistente virtual de una entidad de salud. 
                Saluda cordialmente al usuario y pregunta en qué puedes ayudarle.
                Mantén el saludo breve y profesional."""
            )
            
            response = self.llm.invoke(greeting_prompt.format())
            
            return {
                "messages": [AIMessage(content=response.content)],
                "current_state": ConversationState.GREETING.value,
                "patient_data": state.get("patient_data", {}),
                "conversation_complete": False
            }
        
        return state
    
    def identify_intention_node(self, state: AgentState):
        """Identifica si el usuario quiere agendar una cita"""
        last_message = state["messages"][-1].content
        
        intention_prompt = ChatPromptTemplate.from_template(
            """Analiza si el usuario quiere agendar una cita médica.
            
            Mensaje del usuario: {message}
            
            Si el usuario expresa intención de agendar una cita médica, responde:
            "Perfecto, te ayudo a agendar tu cita médica. Para continuar necesito algunos datos."
            
            Si no es sobre citas médicas, responde:
            "Lo siento, solo puedo ayudarte con el agendamiento de citas médicas. ¿Deseas agendar una cita?"
            
            Responde solo con el mensaje correspondiente."""
        )
        
        response = self.llm.invoke(intention_prompt.format(message=last_message))
        
        return {
            "messages": [AIMessage(content=response.content)],
            "current_state": ConversationState.IDENTIFY_INTENTION.value,
            "patient_data": state.get("patient_data", {}),
            "conversation_complete": False
        }
    
    def request_document_node(self, state: AgentState):
        """Solicita tipo y número de documento"""
        last_message = state["messages"][-1].content
        patient_data = state.get("patient_data", {})
        
        # Verificar si ya tenemos los datos del documento
        if not patient_data.get("document_type") or not patient_data.get("document_number"):
            # Intentar extraer información del mensaje
            doc_info = self._extract_document_info(last_message)
            
            if doc_info["document_type"] and doc_info["document_number"]:
                patient_data.update(doc_info)
                response_text = f"Perfecto, he registrado tu {doc_info['document_type']} número {doc_info['document_number']}."
            else:
                response_text = "Por favor, proporciona tu tipo de documento (Cédula, Tarjeta de Identidad, Pasaporte, etc.) y número de documento."
        else:
            response_text = "Ya tengo registrado tu documento."
        
        return {
            "messages": [AIMessage(content=response_text)],
            "current_state": ConversationState.REQUEST_DOCUMENT.value,
            "patient_data": patient_data,
            "conversation_complete": False
        }
    
    def request_eps_specialty_node(self, state: AgentState):
        """Solicita EPS y especialidad médica"""
        last_message = state["messages"][-1].content
        patient_data = state.get("patient_data", {})
        
        # Extraer EPS y especialidad del mensaje
        extracted_info = self._extract_eps_specialty(last_message)
        
        missing_fields = []
        if not patient_data.get("eps") and not extracted_info.get("eps"):
            missing_fields.append("EPS")
        elif extracted_info.get("eps"):
            patient_data["eps"] = extracted_info["eps"]
            
        if not patient_data.get("specialty") and not extracted_info.get("specialty"):
            missing_fields.append("especialidad médica")
        elif extracted_info.get("specialty"):
            patient_data["specialty"] = extracted_info["specialty"]
        
        if missing_fields:
            response_text = f"Por favor, proporciona tu {' y '.join(missing_fields)}. Las especialidades disponibles son: Medicina General, Dermatología, Cardiología, Pediatría, Ginecología, Ortopedia."
        else:
            response_text = f"Excelente, he registrado tu EPS {patient_data.get('eps')} y la especialidad {patient_data.get('specialty')}."
        
        return {
            "messages": [AIMessage(content=response_text)],
            "current_state": ConversationState.REQUEST_EPS_SPECIALTY.value,
            "patient_data": patient_data,
            "conversation_complete": False
        }
    
    def farewell_node(self, state: AgentState):
        """Despedida y finalización"""
        patient_data = state.get("patient_data", {})
        
        farewell_text = f"""¡Perfecto! He registrado toda tu información:
        
📋 Datos del paciente:
• Documento: {patient_data.get('document_type', 'N/A')} {patient_data.get('document_number', 'N/A')}
• EPS: {patient_data.get('eps', 'N/A')}
• Especialidad: {patient_data.get('specialty', 'N/A')}

Tu solicitud de cita ha sido registrada exitosamente. En breve te contactaremos para confirmar la fecha y hora disponible.

¡Gracias por confiar en nosotros para tu atención médica! 🏥"""
        
        return {
            "messages": [AIMessage(content=farewell_text)],
            "current_state": ConversationState.FAREWELL.value,
            "patient_data": patient_data,
            "conversation_complete": True
        }
    
    def off_topic_node(self, state: AgentState):
        """Maneja consultas fuera del tema"""
        response_text = "Lo siento, solo puedo ayudarte con el agendamiento de citas médicas. ¿Te gustaría agendar una cita?"
        
        return {
            "messages": [AIMessage(content=response_text)],
            "current_state": ConversationState.OFF_TOPIC.value,
            "patient_data": state.get("patient_data", {}),
            "conversation_complete": False
        }
    
    # Funciones de enrutamiento
    def route_after_greeting(self, state: AgentState):
        last_message = state["messages"][-1].content
        if self._is_medical_appointment_request(last_message):
            return "identify_intention"
        return "off_topic"
    
    def route_after_intention(self, state: AgentState):
        last_message = state["messages"][-1].content
        if self._is_medical_appointment_request(last_message):
            return "request_document"
        return "off_topic"
    
    def route_after_document(self, state: AgentState):
        patient_data = state.get("patient_data", {})
        if patient_data.get("document_type") and patient_data.get("document_number"):
            return "request_eps_specialty"
        return "request_document"
    
    def route_after_eps_specialty(self, state: AgentState):
        patient_data = state.get("patient_data", {})
        if patient_data.get("eps") and patient_data.get("specialty"):
            return "farewell"
        return "request_eps_specialty"
    
    # Funciones auxiliares
    def _is_medical_appointment_request(self, message: str):
        """Detecta intención de agendar cita médica"""
        keywords = ["cita", "consulta", "médico", "doctor", "agendar", "reservar", "turno", "especialista"]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in keywords)
    
    def _extract_document_info(self, message: str):
        """Extrae tipo y número de documento"""
        doc_types = {
            "cedula": ["cedula", "cédula", "cc", "c.c"],
            "tarjeta_identidad": ["tarjeta", "ti", "t.i"],
            "pasaporte": ["pasaporte", "pa", "p.a"],
            "cedula_extranjeria": ["extranjeria", "ce", "c.e"]
        }
        
        result = {"document_type": None, "document_number": None}
        message_lower = message.lower()
        
        # Buscar tipo de documento
        for doc_type, aliases in doc_types.items():
            if any(alias in message_lower for alias in aliases):
                result["document_type"] = doc_type.replace("_", " ").title()
                break
        
        # Buscar número de documento (secuencia de dígitos)
        numbers = re.findall(r'\d{6,12}', message)
        if numbers:
            result["document_number"] = numbers[0]
        
        return result
    
    def _extract_eps_specialty(self, message: str):
        """Extrae EPS y especialidad médica"""
        eps_list = ["sura", "salud total", "compensar", "nueva eps", "sanitas", "coomeva", "famisanar"]
        specialties = {
            "general": ["general", "medicina general"],
            "dermatologia": ["dermatologia", "dermatología", "dermatologo"],
            "cardiologia": ["cardiologia", "cardiología", "cardiologo", "corazon"],
            "pediatria": ["pediatria", "pediatría", "pediatra", "niños"],
            "ginecologia": ["ginecologia", "ginecología", "ginecologo"],
            "ortopedia": ["ortopedia", "ortopedista", "huesos"]
        }
        
        result = {"eps": None, "specialty": None}
        message_lower = message.lower()
        
        # Buscar EPS
        for eps in eps_list:
            if eps in message_lower:
                result["eps"] = eps.title()
                break
        
        # Buscar especialidad
        for specialty, aliases in specialties.items():
            if any(alias in message_lower for alias in aliases):
                result["specialty"] = specialty.replace("_", " ").title()
                break
        
        return result
    
    def process_message(self, message: str, session_id: str = "default"):
        """Procesa un mensaje del usuario"""
        # Estado inicial
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "current_state": "",
            "patient_data": {},
            "conversation_complete": False
        }
        
        # Ejecutar el grafo
        result = self.graph.invoke(initial_state)
        
        return ChatResponse(
            response=result["messages"][-1].content,
            state=result["current_state"],
            patient_data=result["patient_data"],
            conversation_complete=result["conversation_complete"]
        )

# Configuración de FastAPI
app = FastAPI(title="Medical Appointment Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instancia global del agente
agent = MedicalAppointmentAgent()

# Almacenamiento de sesiones (en producción usar Redis o base de datos)
sessions = {}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    """Endpoint principal para el chat"""
    try:
        # Obtener o crear sesión
        if chat_message.session_id not in sessions:
            sessions[chat_message.session_id] = {
                "messages": [],
                "current_state": "",
                "patient_data": {},
                "conversation_complete": False
            }
        
        session_state = sessions[chat_message.session_id]
        
        # Estado para el grafo
        graph_state = {
            "messages": session_state["messages"] + [HumanMessage(content=chat_message.message)],
            "current_state": session_state["current_state"],
            "patient_data": session_state["patient_data"],
            "conversation_complete": session_state["conversation_complete"]
        }
        
        # Procesar mensaje
        result = agent.graph.invoke(graph_state)
        
        # Actualizar sesión
        sessions[chat_message.session_id] = {
            "messages": result["messages"],
            "current_state": result["current_state"],
            "patient_data": result["patient_data"],
            "conversation_complete": result["conversation_complete"]
        }
        
        return ChatResponse(
            response=result["messages"][-1].content,
            state=result["current_state"],
            patient_data=result["patient_data"],
            conversation_complete=result["conversation_complete"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Limpiar sesión específica"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session cleared"}
    return {"message": "Session not found"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)