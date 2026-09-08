import pytest

from app.retriever import _apply_min_score


def _make(score: float) -> dict:
    return {"score": score, "payload": {"source_id": f"s{score}"}}


class TestApplyMinScore:
    def test_keeps_score_at_or_above_threshold(self, monkeypatch):
        monkeypatch.setattr("app.retriever.settings.RETRIEVER_MIN_SCORE", 0.5)
        out = _apply_min_score([_make(0.6), _make(0.5), _make(0.49)])
        assert [r["score"] for r in out] == [0.6, 0.5]

    def test_all_below_returns_empty(self, monkeypatch):
        monkeypatch.setattr("app.retriever.settings.RETRIEVER_MIN_SCORE", 0.5)
        assert _apply_min_score([_make(0.3), _make(0.2)]) == []

    def test_zero_disables_filter(self, monkeypatch):
        monkeypatch.setattr("app.retriever.settings.RETRIEVER_MIN_SCORE", 0.0)
        assert len(_apply_min_score([_make(0.3), _make(0.2)])) == 2

    def test_preserves_order(self, monkeypatch):
        monkeypatch.setattr("app.retriever.settings.RETRIEVER_MIN_SCORE", 0.5)
        out = _apply_min_score([_make(0.4), _make(0.7), _make(0.9)])
        assert [r["score"] for r in out] == [0.7, 0.9]

    def test_missing_score_is_falsy(self, monkeypatch):
        monkeypatch.setattr("app.retriever.settings.RETRIEVER_MIN_SCORE", 0.5)
        assert _apply_min_score([{"payload": {}}, _make(0.6)]) == [_make(0.6)]