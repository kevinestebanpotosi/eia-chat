import json
import logging
import time
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from app.config import settings

logger = logging.getLogger(__name__)

_client: Redis | None = None
_last_attempt: float = 0.0
_RETRY_INTERVAL = 30

MEMORY_PREFIX = "eia-rag"
MAX_MESSAGES = 12
TTL_SECONDS = 86400


def _get_client() -> Redis | None:
    global _client, _last_attempt
    if _client is not None:
        return _client
    if not settings.REDIS_URL:
        return None
    if time.time() - _last_attempt < _RETRY_INTERVAL:
        return None
    _last_attempt = time.time()
    try:
        _client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        _client.ping()
        logger.info("Redis conectado correctamente")
        return _client
    except Exception as e:
        logger.warning("Redis no disponible — reintento en %ds (%s)", _RETRY_INTERVAL, e)
        _client = None
        return None


def _key(conversation_id: str) -> str:
    return f"{MEMORY_PREFIX}:conversation:{conversation_id}:messages"


def get_history(conversation_id: str) -> list[dict]:
    global _client
    client = _get_client()
    if client is None:
        return []
    try:
        raw = client.lrange(_key(conversation_id), 0, -1)
    except (RedisConnectionError, OSError) as e:
        logger.warning("Redis no disponible — historial vacío (%s)", e)
        _client = None
        return []
    messages: list[dict] = []
    for item in raw:
        try:
            messages.append(json.loads(item))
        except json.JSONDecodeError:
            continue
    return messages


def save_message(conversation_id: str, role: str, content: str) -> None:
    global _client
    client = _get_client()
    if client is None:
        return
    try:
        key = _key(conversation_id)
        item = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        client.rpush(key, item)
        client.ltrim(key, -MAX_MESSAGES, -1)
        client.expire(key, TTL_SECONDS)
    except (RedisConnectionError, OSError) as e:
        logger.warning("Redis no disponible — mensaje no guardado (%s)", e)
        _client = None
