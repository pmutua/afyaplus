"""LangChain tool for grounded AfyaPlus knowledge retrieval."""

from __future__ import annotations

from langchain_core.tools import tool

from app.rag.retrieval import query_knowledge


@tool
def search_afyaplus_knowledge(question: str) -> str:
    """Search AfyaPlus insurance and clinical-routing policy knowledge.

    Use this only for questions about AfyaPlus coverage, member verification,
    claims, pre-authorization, or documented clinical-routing policy. Do not
    use it for diagnosis, prescriptions, dosage decisions, or general medical
    knowledge.
    """

    try:
        return query_knowledge(question)
    except Exception:
        return "AfyaPlus knowledge search is temporarily unavailable."
