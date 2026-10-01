"""Retrieval / query stubs for structured telecom knowledge.

Implements a lightweight stand-in for the "Structured Knowledge
Representation" and retrieval-augmented-generation (RAG) ideas described
in Sections 3.2 and 7.3 of AI-ML-or-LLM-RCA.md. In a production system
this would query a vector database / knowledge graph of 3GPP specs,
vendor manuals, and historical incidents; here it provides a small,
dependency-free in-memory keyword retriever plus a simple historical
incident store, so the rest of the pipeline has a concrete interface to
build against.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class KnowledgeDocument:
    """A single retrievable piece of domain knowledge."""

    doc_id: str
    title: str
    text: str
    tags: List[str] = field(default_factory=list)


class KnowledgeBase:
    """A minimal in-memory knowledge base with keyword-based retrieval.

    This stands in for retrieval over 3GPP specifications, vendor
    manuals, troubleshooting rules, and historical incident reports as
    described in the paper's discussion of RAG-based knowledge grounding.
    """

    def __init__(self, documents: List[KnowledgeDocument] | None = None) -> None:
        self._documents: Dict[str, KnowledgeDocument] = {}
        for doc in documents or default_documents():
            self.add(doc)

    def add(self, document: KnowledgeDocument) -> None:
        self._documents[document.doc_id] = document

    def all(self) -> List[KnowledgeDocument]:
        return list(self._documents.values())

    def search(self, query: str, top_k: int = 3) -> List[KnowledgeDocument]:
        """Return up to ``top_k`` documents ranked by naive keyword overlap
        with ``query`` (case-insensitive substring/token matching)."""
        query_tokens = {tok for tok in query.lower().split() if tok}
        scored = []
        for doc in self._documents.values():
            haystack = f"{doc.title} {doc.text} {' '.join(doc.tags)}".lower()
            score = sum(1 for tok in query_tokens if tok in haystack)
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def search_by_tag(self, tag: str) -> List[KnowledgeDocument]:
        return [doc for doc in self._documents.values() if tag in doc.tags]


def default_documents() -> List[KnowledgeDocument]:
    """A small built-in seed knowledge base covering common telecom RCA
    failure domains referenced throughout the paper (coverage/downtilt,
    mobility/handover, resource scheduling, interference, transport)."""
    return [
        KnowledgeDocument(
            doc_id="kb-downtilt",
            title="Serving cell downtilt and edge coverage loss",
            text=(
                "An excessive mechanical or digital downtilt angle reduces "
                "far-field coverage, lowering serving SS-RSRP/SINR at the "
                "cell edge and causing throughput degradation independent "
                "of mobility or scheduling."
            ),
            tags=["coverage", "downtilt", "engineering_parameter"],
        ),
        KnowledgeDocument(
            doc_id="kb-handover",
            title="Frequent handovers and mobility-driven degradation",
            text=(
                "A high handover count within a short trajectory window "
                "can introduce throughput interruptions during "
                "re-establishment, especially when combined with "
                "elevated UE speed."
            ),
            tags=["mobility", "handover"],
        ),
        KnowledgeDocument(
            doc_id="kb-rb-scheduling",
            title="Insufficient scheduled resource blocks",
            text=(
                "Average scheduled RBs below the nominal sufficiency "
                "threshold indicate resource scheduling constraints "
                "(e.g. congestion) that directly limit achievable "
                "downlink throughput."
            ),
            tags=["scheduling", "resource_blocks", "congestion"],
        ),
        KnowledgeDocument(
            doc_id="kb-interference",
            title="PCI collision and neighbor-cell interference",
            text=(
                "When a neighbor cell shares the same PCI-mod-N group as "
                "the serving cell, elevated interference can degrade "
                "SINR and reduce throughput even with strong RSRP."
            ),
            tags=["interference", "pci", "neighbor_cell"],
        ),
        KnowledgeDocument(
            doc_id="kb-transport",
            title="Transport-layer bottlenecks affecting radio KPIs",
            text=(
                "A radio-layer KPI degradation can originate from a "
                "transport-network bottleneck (e.g. backhaul congestion) "
                "rather than the radio layer itself, requiring cross-"
                "layer correlation before attributing the cause."
            ),
            tags=["transport", "cross_layer"],
        ),
    ]
