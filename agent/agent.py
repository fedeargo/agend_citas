from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import Dict, Any, List
from datetime import datetime
from typing import Annotated, TypedDict


from agent.tools import MEDICAL_TOOLS
from models.schemas import AppointmentResponse

class AgentState(TypedDict):
    messages: Annotated[List, "Messages in the conversation"]
    user_id: str



class AppointmentAgent:
    def __init__(self):
        # Configurar el LLM
        self.llm = ChatVertexAI(
            model="gemini-2.0-flash-001",
            temperature=0.0,
        )
        
        # Bindear las herramientas al LLM
        self.llm_with_tools = self.llm.bind_tools(MEDICAL_TOOLS)
        
        # Crear el memory saver (checkpointer)
        self.memory = MemorySaver()
        
        # Crear el grafo con checkpointer
        self.graph = self._build_graph()
        
        # Prompt del sistema
        self.system_prompt = """Eres un asistente especializado en agendamiento de citas médicas en Colombia.

        Tu trabajo es ayudar a los usuarios a:
        1. Identificar su EPS
        2. Encontrar la especialidad médica que necesitan
        3. Consultar disponibilidad de médicos o de especialidades
        4. Agendar citas médicas

        IMPORTANTE:
        - Siempre mantén una conversación natural y amigable.
        - Pregunta por información faltante de manera conversacional.
        - Usa las herramientas disponibles para consultar datos reales.
        - Nunca inventes EPS, especialidades, ni médicos: consulta siempre con las herramientas.
        - Confirma los detalles antes de agendar una cita.
        - Si no entiendes algo, pide clarificación de manera amable.

        EPS disponibles: Sura EPS, Sanitas EPS, Compensar EPS, Nueva EPS, Famisanar EPS  
        Especialidades disponibles: Medicina General, Cardiología, Dermatología, Ginecología, Pediatría, Oftalmología, Psicología, Ortopedia, Neurología

        Herramientas disponibles y cuándo usarlas:

        - `list_eps`: Úsala si el usuario pregunta cuáles EPS están disponibles.
        - `search_similar_eps`: Úsala si el usuario menciona una EPS no exactamente igual a las registradas.
        - `list_specialties`: Úsala si el usuario pregunta por las especialidades médicas disponibles.
        - `search_similar_specialities`: Úsala si el usuario menciona una especialidad médica con errores o variaciones.
        - `get_doctors_for_specialty`: Úsala si el usuario quiere saber qué médicos hay en una especialidad específica.
        - `get_doctor_available_dates`: Úsala para saber qué fechas están disponibles para un médico.
        - `check_doctor_availability`: Úsala para verificar los horarios disponibles en una fecha específica con un médico.
        - `get_available_schedule_by_specialty`: Úsala si el usuario quiere ver disponibilidad de citas por especialidad sin especificar médico.
        - `schedule_appointment`: Úsala solo cuando tengas todos los datos confirmados: EPS, especialidad, doctor, fecha y hora.
        - `get_user_appointments_tool`: Úsala si el usuario quiere consultar sus citas existentes.
        - `get_current_date`: Úsala si necesitas saber la fecha actual.
        - `get_tomorrow_date`: Úsala si el usuario pregunta por disponibilidad "mañana".

        Instrucciones adicionales:
        - Siempre valida los nombres de EPS y especialidades usando las herramientas de similitud antes de proceder.
        - Antes de agendar una cita, repite los detalles al usuario para que confirme.
        - Si un dato no está claro, pregúntalo de forma educada.
        """

    def _build_graph(self) -> StateGraph:
        """Construir el grafo del agente con checkpointer"""
        
        def should_continue(state: AgentState) -> str:
            """Decidir si continuar con herramientas o terminar"""
            messages = state["messages"]
            last_message = messages[-1]
            
            # Si el último mensaje del AI tiene tool_calls, ejecutar herramientas
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            else:
                return "end"
        
        def call_model(state: AgentState) -> Dict[str, Any]:
            """Llamar al modelo LLM"""
            messages = state["messages"]
            user_id = state.get("user_id", "unknown")
            
            # Agregar el prompt del sistema si es el primer mensaje
            if not any(isinstance(msg, SystemMessage) for msg in messages):
                # Incluir el user_id en el prompt del sistema
                system_content = f"{self.system_prompt}\n\nID del usuario actual: {user_id}"
                system_msg = SystemMessage(content=system_content)
                messages = [system_msg] + messages
            
            response = self.llm_with_tools.invoke(messages)
            return {"messages": [response]}
        
        # Crear el grafo
        workflow = StateGraph(AgentState)

        # Agregar nodos
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(MEDICAL_TOOLS))

        # Definir el flujo
        workflow.set_entry_point("agent")
        
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                "end": END
            }
        )

        workflow.add_edge("tools", "agent")
        
        # Compilar con el memory saver
        return workflow.compile(checkpointer=self.memory)

    async def chat(self, message: str, user_id: str) -> AppointmentResponse:
        """
        Chatear con el agente de agendamiento usando memory saver
        
        Args:
            message: Mensaje del usuario
            user_id: ID del usuario (también usado como thread_id)
        
        Returns:
            Respuesta del agente
        """
        
        # Configuración del thread para el checkpointer usando user_id
        config = {
            "configurable": {
                "thread_id": user_id
            }
        }
        
        try:
            # Ejecutar el grafo con el mensaje actual y el user_id
            # El estado se maneja automáticamente por el checkpointer
            result = await self.graph.ainvoke(
                {
                    "messages": [HumanMessage(content=message)],
                    "user_id": user_id
                }, 
                config=config
            )
            
            # Obtener la respuesta del agente
            last_message = result["messages"][-1]
            agent_response = last_message.content
            
            # Determinar si se completó una cita
            
            return AppointmentResponse(
                success=True,
                message=agent_response,
                thread_id=user_id 
            )
            
        except Exception as e:
            # Manejar errores
            error_message = f"Lo siento, ocurrió un error: {str(e)}"
            
            return AppointmentResponse(
                success=False,
                message=error_message,
                thread_id=user_id
            )
    

