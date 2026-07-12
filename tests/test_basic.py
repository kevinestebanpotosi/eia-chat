import pytest
from app.store_resolver import resolve_store, StoreConfig
from app.intent_classifier import _keyword_fallback, _parse_intent_output
from app.schemas import ChatRequest, ChatResponse


class TestStoreResolver:
    def test_global_store(self):
        store = resolve_store(1)
        assert store.store_name == "ecommer-global"
        assert store.is_global is True
        assert store.channel_tokens == []
        assert store.audience == "CLIENTE"

    def test_tenant_store(self):
        store = resolve_store(2)
        assert store.store_name == "sol-y-luna"
        assert store.is_global is False
        assert "sol-y-luna-token" in store.channel_tokens
        assert store.audience == "CLIENTE"

    def test_unknown_store_fallback(self):
        store = resolve_store(99)
        assert store.store_name == "tienda-99"
        assert store.is_global is False
        assert store.audience == "CLIENTE"


class TestIntentClassifier:
    def test_catalogo_keywords(self):
        result = _keyword_fallback("quiero comprar adidas superstar")
        assert "CATALOGO" in result

    def test_catalogo_keywords_tiene(self):
        result = _keyword_fallback("¿tiene adidas superstar?")
        assert "CATALOGO" in result

    def test_politicas_keywords(self):
        result = _keyword_fallback("¿cuál es la política de devoluciones?")
        assert "POLITICAS" in result

    def test_info_general_keywords(self):
        result = _keyword_fallback("¿qué es Ecommer?")
        assert "INFO_GENERAL" in result

    def test_conversacional_keywords(self):
        result = _keyword_fallback("hola, buenos días")
        assert "CONVERSACIONAL" in result

    def test_mixed_intents(self):
        result = _keyword_fallback("quiero comprar adidas y cuál es su política de devoluciones?")
        assert "CATALOGO" in result
        assert "POLITICAS" in result

    def test_parse_intent_output_valid(self):
        result = _parse_intent_output("CATALOGO, POLITICAS")
        assert result == ["CATALOGO", "POLITICAS"]

    def test_parse_intent_output_invalid(self):
        result = _parse_intent_output("OTRA_COSA")
        assert result == []

    def test_parse_intent_output_single(self):
        result = _parse_intent_output("CONVERSACIONAL")
        assert result == ["CONVERSACIONAL"]


class TestSchemas:
    def test_chat_request_valid(self):
        req = ChatRequest(query="hola", conversation_id="c1", inbox_id=1)
        assert req.query == "hola"
        assert req.user_id is None

    def test_chat_request_with_user(self):
        req = ChatRequest(query="test", conversation_id="c1", inbox_id=2, user_id=123)
        assert req.user_id == 123

    def test_chat_response(self):
        resp = ChatResponse(
            answer="Hola!",
            intent_detected="CONVERSACIONAL",
            sources_used=0,
            conversation_id="c1",
        )
        assert resp.sources_used == 0
