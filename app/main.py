import logging
from fastapi import FastAPI, HTTPException
from groq import AsyncGroq

from app.config import settings, validate_settings
from app.schemas import ChatRequest, ChatResponse
from app.store_resolver import resolve_store
from app.intent_classifier import classify_intent
from app.retriever import search_context
from app.memory import get_history, save_message
from app.llm_generator import build_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="EIA RAG Gateway",
    description="Unified RAG: intent classification + vector search + memory + LLM generation",
    version="0.1.0",
)

_groq_client: AsyncGroq | None = None


def _get_groq() -> AsyncGroq:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _groq_client


@app.on_event("startup")
async def startup() -> None:
    try:
        validate_settings()
        logger.info("eia-rag gateway iniciado (collection=%s)", settings.COLLECTION_NAME)
    except ValueError as e:
        logger.error("Configuración inválida: %s", e)
        raise


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: dict) -> ChatResponse:
    if not payload.get("query") and payload.get("message"):
        payload["query"] = payload["message"]
    request = ChatRequest(**payload)
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    store = resolve_store(request.inbox_id)
    logger.info(
        "Consulta: '%s' | tienda=%s | canal=%s | conversation=%s",
        query, store.store_name, store.channel_name, request.conversation_id,
    )

    intents = await classify_intent(query)
    intent_str = ", ".join(intents)
    logger.info("Intenciones: %s", intent_str)

    context_items = await search_context(query, store, intents)

    history = get_history(request.conversation_id)

    messages = build_prompt(
        query=query,
        intent=intent_str,
        context_items=context_items,
        history=history,
        store_prompt=store.system_prompt,
    )

    try:
        client = _get_groq()
        completion = await client.chat.completions.create(
            messages=messages,
            model=settings.GROQ_CHAT_MODEL,
            temperature=0.2,
            max_tokens=150,
        )
        raw = completion.choices[0].message.content or ""
        answer = raw.encode("utf-8", errors="replace").decode("utf-8")
        answer = answer.replace("\n", " ").replace("\r", "").strip()
    except Exception as e:
        logger.error("Error generando respuesta: %s", e)
        answer = "Lo siento, estoy teniendo problemas técnicos en este momento para procesar tu solicitud."

    save_message(request.conversation_id, "user", query)
    save_message(request.conversation_id, "assistant", answer)

    return ChatResponse(
        answer=answer,
        intent_detected=intent_str,
        sources_used=len(context_items),
        conversation_id=request.conversation_id,
    )


@app.get("/health")
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "EIA RAG Gateway",
        "collection": settings.COLLECTION_NAME,
    }
