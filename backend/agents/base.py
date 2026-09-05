from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import structlog
import httpx
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.callbacks.base import AsyncCallbackHandler

from core.config import settings
from rag.engine import RAGEngine

logger = structlog.get_logger("agents.base")


class GeminiChatModel:
    """Native async HTTPX client for Google Gemini API conforming to LangChain ainvoke interface."""
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", temperature: float = 0.1):
        self.api_key = api_key
        # Strip any "models/" prefix if passed
        self.model = model.replace("models/", "")
        self.temperature = temperature
        
    async def ainvoke(self, messages: List[Any], config: Optional[Dict[str, Any]] = None) -> AIMessage:
        contents = []
        system_instruction = None
        for m in messages:
            role = "user"
            if isinstance(m, SystemMessage) or getattr(m, "type", "") == "system":
                system_instruction = {"parts": [{"text": str(m.content)}]}
                continue
            elif isinstance(m, AIMessage) or getattr(m, "type", "") == "ai":
                role = "model"
            elif isinstance(m, HumanMessage) or getattr(m, "type", "") == "human":
                role = "user"
            contents.append({"role": role, "parts": [{"text": str(m.content)}]})
        
        if not contents and system_instruction:
            contents = [{"role": "user", "parts": system_instruction["parts"]}]
            system_instruction = None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": 4096,
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
            
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return AIMessage(content="")
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            return AIMessage(content=text)


class StreamingCallbackHandler(AsyncCallbackHandler):
    def __init__(self):
        self.tokens = []
    
    async def on_llm_new_token(self, token: str, **kwargs):
        self.tokens.append(token)


class BaseAgent(ABC):
    def __init__(self, rag_engine: RAGEngine = None):
        self.rag_engine = rag_engine
        self.llm = self._create_llm()
    
    def _create_llm(self):
        gemini_key = settings.effective_gemini_api_key
        if (settings.DEFAULT_LLM_PROVIDER == "gemini" or not (settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY)) and gemini_key:
            if ChatGoogleGenerativeAI:
                try:
                    return ChatGoogleGenerativeAI(
                        model=settings.DEFAULT_MODEL,
                        google_api_key=gemini_key,
                        temperature=0.1,
                    )
                except Exception as e:
                    logger.warning("Failed to initialize ChatGoogleGenerativeAI, falling back to native Gemini client", error=str(e))
            return GeminiChatModel(
                api_key=gemini_key,
                model=settings.DEFAULT_MODEL,
                temperature=0.1,
            )
        elif settings.DEFAULT_LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
            return ChatAnthropic(
                model=settings.DEFAULT_MODEL,
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.1,
                max_tokens=4000,
            )
        elif settings.OPENAI_API_KEY:
            return ChatOpenAI(
                model=settings.DEFAULT_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.1,
                max_tokens=4000,
            )
        elif gemini_key:
            return GeminiChatModel(
                api_key=gemini_key,
                model=settings.DEFAULT_MODEL,
                temperature=0.1,
            )
        else:
            logger.warning("No LLM API key configured (GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY), using mock")
            return None
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def _call_llm(self, messages: List, temperature: float = 0.1) -> str:
        if not self.llm:
            return "Mock response - no LLM configured"
        
        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error("LLM call failed", error=str(e))
            raise
    
    async def _call_llm_streaming(self, messages: List, temperature: float = 0.1) -> str:
        if not self.llm:
            return "Mock response - no LLM configured"
        
        try:
            handler = StreamingCallbackHandler()
            response = await self.llm.ainvoke(messages, config={"callbacks": [handler]})
            return response.content
        except Exception as e:
            logger.error("LLM streaming call failed", error=str(e))
            raise
    
    def _build_system_message(self, role: str, guidelines: List[str]) -> SystemMessage:
        content = f"You are a {role}.\n\nGuidelines:\n" + "\n".join(f"- {g}" for g in guidelines)
        return SystemMessage(content=content)


class AgentOrchestrator:
    def __init__(self, rag_engine: RAGEngine = None):
        self.rag_engine = rag_engine or RAGEngine()
        self.agents: Dict[str, BaseAgent] = {}
    
    def register_agent(self, name: str, agent: BaseAgent):
        self.agents[name] = agent
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        return self.agents.get(name)
    
    async def run_agent(self, name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        agent = self.agents.get(name)
        if not agent:
            raise ValueError(f"Agent {name} not found")
        return await agent.process(input_data)
    
    async def run_pipeline(self, pipeline: List[Dict[str, Any]], initial_input: Dict[str, Any]) -> Dict[str, Any]:
        context = initial_input.copy()
        
        for step in pipeline:
            agent_name = step.get("agent")
            if not agent_name:
                continue
            
            agent_input = step.get("input_transform", lambda x: x)(context)
            result = await self.run_agent(agent_name, agent_input)
            
            output_key = step.get("output_key", agent_name)
            context[output_key] = result
        
        return context


class AgentState:
    def __init__(self):
        self.context: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.current_step: Optional[str] = None
    
    def update(self, key: str, value: Any):
        self.context[key] = value
        self.history.append({"step": self.current_step, "key": key, "value": value})
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.context.get(key, default)