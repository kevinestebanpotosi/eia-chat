import logging
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Filter, FieldCondition, MatchAny, IsEmptyCondition, PayloadField
from openai import AsyncAzureOpenAI
from app.config import settings
from app.store_resolver import StoreConfig

logger = logging.getLogger(__name__)

_qdrant: AsyncQdrantClient | None = None
_azure: AsyncAzureOpenAI | None = None


def _get_qdrant() -> AsyncQdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=10.0,
        )
    return _qdrant


def _get_azure() -> AsyncAzureOpenAI:
    global _azure
    if _azure is None:
        _azure = AsyncAzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-02-01",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        )
    return _azure


async def _embed(text: str) -> list[float]:
    client = _get_azure()
    response = await client.embeddings.create(
        input=[text],
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        dimensions=1536,
    )
    return response.data[0].embedding


async def search_context(
    query: str,
    store: StoreConfig,
    intents: list[str],
    limit: int = 10,
) -> list[dict]:
    logger.info("Buscando: '%s' (store=%s, intents=%s)", query, store.store_name, intents)

    if "CONVERSACIONAL" in intents and len(intents) == 1:
        logger.info("Intención CONVERSACIONAL — saltando búsqueda en Qdrant")
        return []

    try:
        query_vector = await _embed(query)
    except Exception as e:
        logger.error("Error generando embedding: %s", e)
        return []

    must_conditions: list[FieldCondition] = []

    has_catalogo = "CATALOGO" in intents

    if not (has_catalogo and store.is_global):
        must_conditions.append(
            FieldCondition(
                key="audience",
                match=MatchAny(any=[store.audience]),
            )
        )

    content_type_values = []
    for intent in intents:
        if intent in ("CATALOGO", "POLITICAS", "INFO_GENERAL"):
            content_type_values.append(intent)

    if content_type_values:
        must_conditions.append(
            FieldCondition(
                key="content_type",
                match=MatchAny(any=content_type_values),
            )
        )
    _platform_only = IsEmptyCondition(is_empty=PayloadField(key="metadata.channel_tokens"))

    if has_catalogo and store.is_global:
        pass
    elif has_catalogo and store.channel_tokens:
        must_conditions.append(
            FieldCondition(
                key="metadata.channel_tokens",
                match=MatchAny(any=store.channel_tokens),
            )
        )
    elif store.is_global:
        must_conditions.append(_platform_only)
    elif store.channel_tokens:
        must_conditions.append(
            Filter(should=[
                FieldCondition(
                    key="metadata.channel_tokens",
                    match=MatchAny(any=store.channel_tokens),
                ),
                _platform_only,
            ])
        )

    search_filter = Filter(must=must_conditions) if must_conditions else None

    try:
        client = _get_qdrant()
        response = await client.query_points(
            collection_name=settings.COLLECTION_NAME,
            query=query_vector,
            query_filter=search_filter,
            limit=limit,
            with_payload=True,
        )
        results = response.points
        logger.info("Encontrados %d resultados", len(results))
        return [{"score": hit.score, "payload": hit.payload} for hit in results]

    except UnexpectedResponse as e:
        if e.status_code == 404:
            logger.warning("Colección '%s' no existe", settings.COLLECTION_NAME)
            return []
        if e.status_code == 400:
            logger.warning("Error 400 de Qdrant — reintentando sin filtro de audiencia")
            try:
                fallback_conditions = [
                    c for c in must_conditions
                    if not (isinstance(c, FieldCondition) and c.key == "audience")
                ]
                fallback_filter = Filter(must=fallback_conditions) if fallback_conditions else None
                response = await client.query_points(
                    collection_name=settings.COLLECTION_NAME,
                    query=query_vector,
                    query_filter=fallback_filter,
                    limit=limit,
                    with_payload=True,
                )
                return [{"score": hit.score, "payload": hit.payload} for hit in response.points]
            except Exception as f:
                logger.error("Fallo también el fallback: %s", f)
                return []
        logger.error("Error Qdrant HTTP: %s", e)
        return []
    except Exception as e:
        logger.error("Error en retriever: %s", e)
        return []
