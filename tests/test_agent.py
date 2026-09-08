"""Tests de Fase 3 — agente conversacional (core + herramientas).

Usan mocks: no hay llamadas a Qdrant, Azure OpenAI, Groq ni Redis.
Se ejecutan de forma síncrona con `asyncio.run`.
"""

import asyncio
from types import SimpleNamespace

import pytest

from app.agent import tools
from app.agent.core import run_agent
from app.store_resolver import resolve_store, init_stores


@pytest.fixture(autouse=True)
def _setup_stores():
    init_stores()


@pytest.fixture(autouse=True)
def _fake_memory(monkeypatch):
    """Aísla la memoria: nada de Redis, historia en proceso por conversación.

    Cada test puede sobrescribir `tools.get_history` / `core.save_message`
    según lo que quiera verificar.
    """
    history: dict[str, list[dict]] = {}

    def _get_history(cid):
        return [dict(m) for m in history.get(cid, [])]

    monkeypatch.setattr(tools, "get_history", _get_history)
    monkeypatch.setattr("app.agent.core.save_message",
                        lambda cid, role, content: history.setdefault(cid, []).append(
                            {"role": role, "content": content}))
    return history


# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------

def _product(score=0.9, name="KZ Castor Pro"):
    return {
        "score": score,
        "payload": {
            "name": name,
            "url": "https://ecommer.shop/es/product/kz-castor-pro-bass-edition",
        },
    }


def _doc(score=0.8):
    return {
        "score": score,
        "payload": {"text": "Los compradores tendran derecho a la reversión del pago."},
    }


def _stub_classify(result):
    async def _classify(query):
        return list(result)
    return _classify


def _recording_search(calls):
    async def _search(query, store, intents, limit=10):
        calls.append(list(intents))
        return [_product()] if "CATALOGO" in intents else [_doc()]
    return _search


class _FakeGroq:
    def __init__(self, content="", finish_reason="stop", error=None):
        self._content = content
        self._finish_reason = finish_reason
        self._error = error
        self.records = []
        self.chat = SimpleNamespace(completions=self._Completions(self))

    class _Completions:
        def __init__(self, parent):
            self._parent = parent

        async def create(self, **kwargs):
            self._parent.records.append(kwargs)
            if self._parent._error is not None:
                raise self._parent._error
            choice = SimpleNamespace(finish_reason=self._parent._finish_reason)
            choice.message = SimpleNamespace(content=self._parent._content)
            return SimpleNamespace(choices=[choice])


def _run(query, conversation_id="conv-1", inbox_id=2):
    return asyncio.run(run_agent(query, conversation_id, inbox_id))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestToolRegistry:
    def test_expected_tools_registered(self):
        expected = {"search_catalogo", "search_docs", "get_memory", "answer", "escalate"}
        assert expected.issubset(tools.TOOL_REGISTRY.keys())

    def test_escalation_message_keeps_fail_closed_token(self):
        assert "configurada" in tools.ESCALATION_MESSAGE


class TestStoreMappingFlag:
    def test_mapped_store_is_mapped(self):
        assert resolve_store(2).is_mapped is True
        assert resolve_store(10).is_mapped is True

    def test_unknown_store_not_mapped(self):
        assert resolve_store(99).is_mapped is False


class TestEscalate:
    def test_unknown_store_escalates_without_llm(self, monkeypatch):
        monkeypatch.setattr("app.agent.core.classify_intent", _stub_classify(["CATALOGO"]))

        def _boom_search(*args, **kwargs):
            raise AssertionError("No debe buscar contexto en tienda no mapeada")
        monkeypatch.setattr(tools, "search_context", _boom_search)

        saved = []
        monkeypatch.setattr("app.agent.core.save_message",
                            lambda cid, role, content: saved.append((role, content)))

        result = _run("¿tienen audífonos?", conversation_id="c99", inbox_id=99)

        assert result.escalado is True
        assert result.escalado
        assert result.sources_used == 0
        assert result.tools_used == ["escalate"]
        assert "configurada" in result.answer
        assert saved == [("user", "¿tienen audífonos?"), ("assistant", result.answer)]

    def test_escalate_keeps_conversation_id(self, monkeypatch):
        monkeypatch.setattr("app.agent.core.classify_intent", _stub_classify(["INFO_GENERAL"]))
        monkeypatch.setattr("app.agent.core.save_message", lambda *a: None)
        result = _run("¿qué es Ecommer?", conversation_id="c99-bis", inbox_id=99)
        assert result.conversation_id == "c99-bis"
        assert result.escalado is True


class TestDispatch:
    def test_catalogo_uses_search_catalogo(self, monkeypatch):
        monkeypatch.setattr("app.agent.core.classify_intent", _stub_classify(["CATALOGO"]))
        calls = []
        monkeypatch.setattr(tools, "search_context", _recording_search(calls))
        monkeypatch.setattr(tools, "_get_groq", lambda: _FakeGroq("Respuesta del agente."))

        result = _run("¿tienen audífonos KZ Castor Pro?", inbox_id=2)

        assert result.escalado is False
        assert result.sources_used == 1
        assert result.answer == "Respuesta del agente."
        assert "search_catalogo" in result.tools_used
        assert "answer" in result.tools_used
        assert calls == [["CATALOGO"]]

    def test_docs_uses_search_docs(self, monkeypatch):
        monkeypatch.setattr("app.agent.core.classify_intent", _stub_classify(["POLITICAS"]))
        calls = []
        monkeypatch.setattr(tools, "search_context", _recording_search(calls))
        monkeypatch.setattr(tools, "_get_groq", lambda: _FakeGroq("Política."))

        result = _run("¿cuál es la política de devoluciones?", inbox_id=2)

        assert result.sources_used == 1
        assert "search_docs" in result.tools_used
        assert calls == [["POLITICAS"]]

    def test_mixed_intents_use_both_search_tools(self, monkeypatch):
        monkeypatch.setattr("app.agent.core.classify_intent",
                            _stub_classify(["CATALOGO", "POLITICAS"]))
        calls = []
        monkeypatch.setattr(tools, "search_context", _recording_search(calls))
        monkeypatch.setattr(tools, "_get_groq", lambda: _FakeGroq("Mixta."))

        result = _run("¿venden café y cuál es la política?", inbox_id=2)

        assert result.sources_used == 2
        assert "search_catalogo" in result.tools_used
        assert "search_docs" in result.tools_used
        assert calls == [["CATALOGO"], ["POLITICAS"]]

    def test_conversacional_skips_search(self, monkeypatch):
        monkeypatch.setattr("app.agent.core.classify_intent", _stub_classify(["CONVERSACIONAL"]))

        def _boom_search(*args, **kwargs):
            raise AssertionError("CONVERSACIONAL no debe llamar al retriever")
        monkeypatch.setattr(tools, "search_context", _boom_search)
        monkeypatch.setattr(tools, "_get_groq", lambda: _FakeGroq("¡Hola!"))

        result = _run("hola, buenos días", inbox_id=2)

        assert result.escalado is False
        assert result.sources_used == 0
        assert not any(n.startswith("search_") for n in result.tools_used)
        assert result.answer == "¡Hola!"


class TestLLMFallbacks:
    def test_empty_content_fallback(self, monkeypatch):
        monkeypatch.setattr("app.agent.core.classify_intent", _stub_classify(["CATALOGO"]))
        monkeypatch.setattr(tools, "search_context", _recording_search([]))
        monkeypatch.setattr(tools, "_get_groq", lambda: _FakeGroq(content="", finish_reason="stop"))

        result = _run("¿cuánto cuesta el KZ?", inbox_id=2)

        assert "reformular" in result.answer

    def test_groq_error_fallback(self, monkeypatch):
        monkeypatch.setattr("app.agent.core.classify_intent", _stub_classify(["CATALOGO"]))
        monkeypatch.setattr(tools, "search_context", _recording_search([]))
        monkeypatch.setattr(tools, "_get_groq",
                            lambda: _FakeGroq(error=RuntimeError("boom")))

        result = _run("¿tienen café orgánico?", inbox_id=2)

        assert "problemas técnicos" in result.answer


class TestMemory:
    def test_history_flows_into_prompt(self, monkeypatch):
        monkeypatch.setattr("app.agent.core.classify_intent", _stub_classify(["CATALOGO"]))
        monkeypatch.setattr(tools, "search_context", _recording_search([]))
        monkeypatch.setattr(tools, "get_history",
                            lambda cid: [{"role": "user", "content": "turno anterior"}])
        fake = _FakeGroq("Respuesta.")
        monkeypatch.setattr(tools, "_get_groq", lambda: fake)

        _run("¿y trae estuche?", conversation_id="mem-1", inbox_id=2)

        messages = fake.records[0]["messages"]
        assert {"role": "user", "content": "turno anterior"} in messages
        assert messages[-1] == {"role": "user", "content": "¿y trae estuche?"}

    def test_messages_saved_user_and_assistant(self, monkeypatch):
        monkeypatch.setattr("app.agent.core.classify_intent", _stub_classify(["CATALOGO"]))
        monkeypatch.setattr(tools, "search_context", _recording_search([]))
        monkeypatch.setattr(tools, "_get_groq", lambda: _FakeGroq("Respuesta."))
        saved = []
        monkeypatch.setattr("app.agent.core.save_message",
                            lambda cid, role, content: saved.append((role, content)))

        _run("¿tienen amigurumis?", conversation_id="mem-2", inbox_id=10)

        assert saved == [("user", "¿tienen amigurumis?"), ("assistant", "Respuesta.")]


class TestInputs:
    def test_empty_query_raises(self):
        with pytest.raises(ValueError):
            _run("   ", inbox_id=2)

    def test_missing_conversation_id_generates_one(self, monkeypatch):
        monkeypatch.setattr("app.agent.core.classify_intent", _stub_classify(["CATALOGO"]))
        monkeypatch.setattr(tools, "search_context", _recording_search([]))
        monkeypatch.setattr(tools, "_get_groq", lambda: _FakeGroq("Respuesta."))
        result = asyncio.run(run_agent("hola", "", 2))
        assert result.conversation_id.startswith("agent-")