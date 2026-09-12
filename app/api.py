import logging

from fastapi import APIRouter, Body, HTTPException

from app.agent.core import run_agent
from app.services.chatwoot_parser import parse_chatwoot_webhook
from app.services.chatwoot_service import send_message_to_chatwoot
from app.services.webhook_parser import parse_messenger_webhook

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Chatwoot"],
)


@router.get("/hello")
def hello() -> dict:
    return {"message": "Hola desde la API"}


@router.post("/chat")
async def chat(payload: dict = Body(...)):
    try:
        query = payload.get("query") or payload.get("message") or payload.get("prompt")

        if not query:
            raise ValueError("Debes enviar 'query', 'message' o 'prompt'")

        result = await run_agent(
            query=query,
            conversation_id=payload.get("conversation_id", "test"),
            inbox_id=payload.get("inbox_id", 0),
            user_id=payload.get("user_id"),
            channel=payload.get("channel"),
        )

        return {"answer": result.answer}

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar el agente: {str(error)}",
        )


@router.post("/webhook", summary="Messenger Webhook")
async def messenger_webhook(payload: dict = Body(...)):
    parsed = parse_messenger_webhook(payload)

    if parsed is None:
        return {
            "ignored": True,
            "reason": "Mensaje vacío, echo o formato inválido",
        }

    try:
        conversation_id = str(
            parsed.get("conversation_id")
            or parsed.get("sender_id")
        )

        user_message = parsed["query"]

        result = await run_agent(
            query=user_message,
            conversation_id=conversation_id,
            inbox_id=0,
            user_id=parsed.get("sender_id"),
        )

        return {
            "ignored": False,
            "source": "messenger_direct",
            "sender_id": parsed.get("sender_id"),
            "query": user_message,
            "response": result.answer,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando webhook: {str(error)}",
        )


@router.post("/chatwoot-webhook", summary="Chatwoot Webhook")
async def chatwoot_webhook(payload: dict = Body(...)):
    parsed = parse_chatwoot_webhook(payload)

    if parsed is None:
        return {
            "ignored": True,
            "reason": "Evento no válido, mensaje vacío, mensaje saliente o inbox no permitida",
        }

    try:
        user_message = parsed["query"]

        result = await run_agent(
            query=user_message,
            conversation_id=f"chatwoot_{parsed['conversation_id']}",
            inbox_id=parsed["inbox_id"],
            user_id=parsed.get("sender_id"),
            channel=parsed.get("channel"),
        )

        chatwoot_response = await send_message_to_chatwoot(
            conversation_id=parsed["conversation_id"],
            content=result.answer,
        )

        return {
            "ignored": False,
            "source": "chatwoot",
            "conversation_id": parsed["conversation_id"],
            "sender_id": parsed.get("sender_id"),
            "message_id": parsed.get("message_id"),
            "inbox_id": parsed.get("inbox_id"),
            "channel": parsed.get("channel"),
            "query": user_message,
            "response": result.answer,
            "chatwoot_message_id": chatwoot_response.get("id"),
        }

    except Exception as error:
        logger.error("Error procesando webhook de Chatwoot: %s", error)

        raise HTTPException(
            status_code=500,
            detail=f"Error procesando webhook de Chatwoot: {str(error)}",
        )
