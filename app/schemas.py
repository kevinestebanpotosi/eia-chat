from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Mensaje del usuario")
    conversation_id: str = Field(..., description="ID de conversación de Chatwoot")
    inbox_id: int = Field(..., description="ID del inbox de Chatwoot (→ tienda + canal)")
    user_id: int | None = Field(None, description="ID del usuario en Chatwoot")
    channel: str | None = Field(None, description="Canal de origen: whatsapp, instagram, messenger, shop, admin")


class ChatResponse(BaseModel):
    answer: str
    intent_detected: str
    sources_used: int
    conversation_id: str
