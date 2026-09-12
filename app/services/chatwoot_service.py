import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_message_to_chatwoot(conversation_id: int, content: str) -> dict:
    if not settings.CHATWOOT_BASE_URL:
        raise ValueError("CHATWOOT_BASE_URL no está configurado")
    if not settings.CHATWOOT_ACCOUNT_ID:
        raise ValueError("CHATWOOT_ACCOUNT_ID no está configurado")
    if not settings.CHATWOOT_API_ACCESS_TOKEN:
        raise ValueError("CHATWOOT_API_ACCESS_TOKEN no está configurado")

    url = (
        f"{settings.CHATWOOT_BASE_URL}/api/v1/accounts/"
        f"{settings.CHATWOOT_ACCOUNT_ID}/conversations/"
        f"{conversation_id}/messages"
    )

    headers = {
        "Content-Type": "application/json",
        "api_access_token": settings.CHATWOOT_API_ACCESS_TOKEN,
    }

    payload = {
        "content": content,
        "message_type": "outgoing",
        "private": False,
        "content_type": "text",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            json=payload,
            headers=headers,
        )

    response.raise_for_status()

    return response.json()
