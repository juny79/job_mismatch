"""Deterministic in-memory GraphRAG workflow for approved PoC postings.

This demonstrates ingestion-to-graph-to-retrieval-to-cited-summary flow without
external databases, embeddings, or LLM calls. It is not a production adapter.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Any

from src.domain.models import Evidence, JobPosting
from src.retrieval.search import SearchHit, searchable, search


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    kind: str
    label: str


@dataclass(frozen=True)
class GraphEdge:
    source_id: str
    target_id: str
    relationship: str
    posting_id: str
    evidence: tuple[Evidence, ...] = ()
    synthetic: bool = False


@dataclass(frozen=True)
class JobGraph:
    nodes: dict[str, GraphNode]
    edges: tuple[GraphEdge, ...]
    postings: dict[str, JobPosting]


def _node_id(kind: str, label: str) -> str:
    return f"{kind.casefold()}:{label.strip().casefold()}"


def build_job_graph(postings: list[JobPosting]) -> JobGraph:
    """Build an in-memory property graph from approved records only."""
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    approved: dict[str, JobPosting] = {}

    def add_node(kind: str, label: str) -> str:
        node_id = _node_id(kind, label)
        nodes.setdefault(node_id, GraphNode(node_id, kind, label))
        return node_id

    def add_edge(
        source_id: str,
        target_id: str,
        relationship: str,
        posting: JobPosting,
        evidence_field: str | None = None,
    ) -> None:
        evidence = tuple(
            item for item in posting.evidence
            if evidence_field is not None and item.field == evidence_field
        )
        edges.append(GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            posting_id=posting.posting_id,
            evidence=evidence,
            synthetic=posting.synthetic,
        ))

    for posting in postings:
        if not searchable(posting):
            continue
        approved[posting.posting_id] = posting
        posting_node = add_node("Posting", posting.posting_id)
        source_node = add_node("Source", posting.source_id)
        add_edge(posting_node, source_node, "FROM_SOURCE", posting)

        for kind, label, relationship, evidence_field in (
            ("Role", posting.role_category, "HAS_ROLE", "role_category"),
            ("Location", posting.region, "LOCATED_IN", "region"),
        ):
            if label.strip():
                target = add_node(kind, label)
                add_edge(posting_node, target, relationship, posting, evidence_field)

        if posting.company_id or posting.company_name:
            company_key = posting.company_id or posting.company_name
            company_node = add_node("Company", company_key)
            add_edge(company_node, posting_node, "POSTED_JOB", posting)

        for skill in posting.required_skills:
            if skill.strip():
                target = add_node("Skill", skill)
                add_edge(posting_node, target, "REQUIRES_SKILL", posting, "required_skills")
        for benefit in posting.benefits:
            if benefit.strip():
                target = add_node("Benefit", benefit)
                add_edge(posting_node, target, "OFFERS_BENEFIT", posting, "benefits")

    return JobGraph(nodes=nodes, edges=tuple(edges), postings=approved)


def retrieve_graph(graph: JobGraph, query: str, region: str | None = None) -> list[SearchHit]:
    """Match graph entities first; use reviewed keyword search as a fallback."""
    terms = tuple(term.casefold() for term in query.split() if term.strip())
    matched_nodes = {
        node_id for node_id, node in graph.nodes.items()
        if node.kind != "Posting" and any(term in node.label.casefold() for term in terms)
    }
    posting_ids = {
        edge.posting_id for edge in graph.edges
        if edge.source_id in matched_nodes or edge.target_id in matched_nodes
    }

    graph_hits = [
        SearchHit(graph.postings[posting_id], terms)
        for posting_id in sorted(posting_ids)
        if posting_id in graph.postings
        and (not region or region.casefold() in graph.postings[posting_id].region.casefold())
    ]
    if graph_hits or not terms:
        return graph_hits

    return search(list(graph.postings.values()), query, region)


def _posting_result(hit: SearchHit) -> dict[str, Any]:
    posting = hit.posting
    evidence = [
        {"field": item.field, "quote": item.quote, "locator": item.locator}
        for item in posting.evidence
    ]
    return {
        "posting_id": posting.posting_id,
        "title": posting.title,
        "region": posting.region,
        "role_category": posting.role_category,
        "skills": list(posting.required_skills),
        "benefits": list(posting.benefits),
        "salary": {
            "status": posting.salary.status,
            "raw": posting.salary.raw,
            "minimum": posting.salary.minimum,
            "maximum": posting.salary.maximum,
            "unit": posting.salary.unit,
        },
        "source": {
            "id": posting.source_id,
            "name": posting.source_name,
            "record_id": posting.source_record_id,
            "url": posting.source_url,
            "posted_at": posting.posted_at,
            "collected_at": posting.collected_at,
        },
        "evidence": evidence,
        "synthetic": posting.synthetic,
    }


def graph_summary(graph: JobGraph) -> dict[str, Any]:
    skills = Counter(
        graph.nodes[edge.target_id].label
        for edge in graph.edges
        if edge.relationship == "REQUIRES_SKILL"
    )
    regions = Counter(
        graph.nodes[edge.target_id].label
        for edge in graph.edges
        if edge.relationship == "LOCATED_IN"
    )
    return {
        "approved_postings": len(graph.postings),
        "node_count": len(graph.nodes),
        "relationship_count": len(graph.edges),
        "synthetic_postings": sum(p.synthetic for p in graph.postings.values()),
        "postings_by_region": dict(sorted(regions.items())),
        "postings_by_skill": dict(sorted(skills.items())),
    }


def answer_with_graph(
    postings: list[JobPosting],
    query: str,
    region: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic evidence package; abstain when retrieval is empty."""
    graph = build_job_graph(postings)
    hits = retrieve_graph(graph, query, region)
    results = [_posting_result(hit) for hit in hits]
    return {
        "mode": "synthetic_demo" if results and all(row["synthetic"] for row in results) else "local_graph_retrieval",
        "query": query,
        "region_filter": region,
        "result_count": len(results),
        "abstained": not results,
        "message": (
            "검색된 승인 레코드의 근거만 표시합니다. 합성 데이터는 실제 시장 근거가 아닙니다."
            if results and all(row["synthetic"] for row in results)
            else "검색된 승인 레코드의 근거만 표시합니다."
            if results
            else "조건에 맞는 승인 레코드가 없습니다. 근거가 없어 답변을 생성하지 않았습니다."
        ),
        "graph_summary": graph_summary(graph),
        "results": results,
    }
