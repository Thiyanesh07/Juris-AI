"""Phase 6 — LLM legal QA grounded on hybrid retrieval evidence."""

from app.qa.service import QAInvalidModelOutputError, ask_legal_question

__all__ = ["QAInvalidModelOutputError", "ask_legal_question"]
