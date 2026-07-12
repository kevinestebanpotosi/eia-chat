import re
import logging
from groq import AsyncGroq
from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _client


ROUTER_SYSTEM_PROMPT = """Eres el enrutador de intenciones de la plataforma Ecommer. Clasifica la entrada del usuario en una o varias de estas categorías:

1. "CATALOGO": Busca comprar, pregunta por productos, características o disponibilidad de stock.
2. "POLITICAS": Pregunta por envíos, devoluciones, garantías o reglas específicas de una compra.
3. "INFO_GENERAL": Pregunta sobre qué es Ecommer, cómo funciona, costos de suscripción, pasarelas de pago, facturación, soporte técnico, misión o visión de la empresa.
4. "CONVERSACIONAL": Saludos, agradecimientos o preguntas totalmente fuera de contexto.

Si la consulta cubre más de una categoría, responde con las categorías separadas por comas.
Responde ÚNICAMENTE con las palabras exactas de las categorías, en mayúsculas."""


def _parse_intent_output(raw: str) -> list[str]:
    normalized = re.sub(r"[\n;]+", ",", raw)
    tokens = [t.strip() for t in normalized.split(",") if t.strip()]
    valid = {"CATALOGO", "POLITICAS", "INFO_GENERAL", "CONVERSACIONAL"}
    return list(dict.fromkeys(t for t in tokens if t in valid))


def _keyword_fallback(query: str) -> list[str]:
    q = query.lower()
    detected: list[str] = []

    if re.search(r"\b(compra|comprar|producto|productos|stock|precio|caracter[ií]stica|cat[aá]logo|tiene|tengo|buscar|dime)\b", q):
        detected.append("CATALOGO")

    if re.search(r"\b(devoluci[oó]n|devoluciones|garant[ií]a|env[ií]o|envios|pol[ií]tica|cambio|reembolso)\b", q):
        detected.append("POLITICAS")

    if re.search(r"\b(ecommer|suscripci[oó]n|costos|wompi|dian|facturaci[oó]n|pago|pasarela|misi[oó]n|soporte|empresa|como funciona)\b", q):
        detected.append("INFO_GENERAL")

    if not detected and re.search(r"\b(hola|buenos|buenas|gracias|qué tal|buen dia|buenas tardes|saludos)\b", q):
        detected.append("CONVERSACIONAL")

    return list(dict.fromkeys(detected))


async def classify_intent(query: str) -> list[str]:
    logger.info("Clasificando intención: '%s'", query)
    try:
        client = _get_client()
        completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            model=settings.GROQ_ROUTER_MODEL,
            temperature=0.0,
            max_tokens=10,
        )
        raw = completion.choices[0].message.content.strip().upper()
        detected = _parse_intent_output(raw)
        fallback = _keyword_fallback(query)

        combined = list(dict.fromkeys(detected + fallback))
        if not combined:
            return ["CONVERSACIONAL"]

        if "CONVERSACIONAL" in combined and len(combined) > 1:
            combined = [i for i in combined if i != "CONVERSACIONAL"]

        return combined

    except Exception as e:
        logger.error("Error clasificando intención: %s", e)
        return _keyword_fallback(query) or ["CONVERSACIONAL"]
