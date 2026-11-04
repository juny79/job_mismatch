"""Explainable lexical-plus-graph retrieval baseline; no external services."""

from dataclasses import dataclass

from src.domain.models import Evidence, JobPosting
from src.retrieval.graphrag import GraphEdge, JobGraph, build_job_graph
from src.retrieval.search import searchable

FIELD_WEIGHTS = {
    "title": 5.0,
    "role_category": 4.0,
    "required_skills": 3.5,
    "benefits": 2.5,
    "raw_text": 1.5,
    "region": 1.0,
    "company_name": 1.0,
}


@dataclass(frozen=True)
class HybridHit:
    posting: JobPosting
    score: float
    matched_terms: tuple[str, ...]
    matched_fields: tuple[str, ...]
    channels: tuple[str, ...]
    graph_paths: tuple[dict[str, object], ...]
    evidence: tuple[Evidence, ...]


def _terms(query: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(term.casefold() for term in query.split() if term.strip()))


def _field_values(posting: JobPosting) -> dict[str, tuple[str, ...]]:
    return {
        "title": (posting.title,),
        "role_category": (posting.role_category,),
        "required_skills": posting.required_skills,
        "benefits": posting.benefits,
        "raw_text": (posting.raw_text,),
        "region": (posting.region,),
        "company_name": (posting.company_name,),
    }


def _edge_label(graph: JobGraph, edge: GraphEdge) -> str:
    target = graph.nodes.get(edge.target_id)
    source = graph.nodes.get(edge.source_id)
    return (target or source).label if (target or source) else ""


def _graph_matches(graph: JobGraph, query_terms: tuple[str, ...]) -> dict[str, list[dict[str, object]]]:
    matches: dict[str, list[dict[str, object]]] = {}
    for edge in graph.edges:
        if edge.relationship not in {"HAS_ROLE", "LOCATED_IN", "REQUIRES_SKILL", "OFFERS_BENEFIT", "POSTED_JOB"}:
            continue
        endpoint_id = edge.source_id if edge.relationship == "POSTED_JOB" else edge.target_id
        endpoint = graph.nodes.get(endpoint_id)
        label = endpoint.label.casefold() if endpoint else ""
        matched = tuple(term for term in query_terms if term in label)
        if not matched:
            continue
        matches.setdefault(edge.posting_id, []).append({
            "relationship": edge.relationship,
            "label": endpoint.label if endpoint else "",
            "matched_terms": matched,
            "evidence": tuple(edge.evidence),
            "synthetic": edge.synthetic,
        })
    return matches


def _all_posting_graph_paths(graph: JobGraph) -> dict[str, list[dict[str, object]]]:
    paths_by_posting: dict[str, list[dict[str, object]]] = {}
    for edge in graph.edges:
        if edge.relationship not in {"HAS_ROLE", "LOCATED_IN", "REQUIRES_SKILL", "OFFERS_BENEFIT", "POSTED_JOB"}:
            continue
        endpoint_id = edge.source_id if edge.relationship == "POSTED_JOB" else edge.target_id
        endpoint = graph.nodes.get(endpoint_id)
        if not endpoint:
            continue
        paths_by_posting.setdefault(edge.posting_id, []).append({
            "relationship": edge.relationship,
            "label": endpoint.label,
            "matched_terms": (),
            "evidence": tuple(edge.evidence),
            "synthetic": edge.synthetic,
        })
    return paths_by_posting


def hybrid_search(
    postings: list[JobPosting],
    query: str,
    region: str | None = None,
    *,
    limit: int = 60,
) -> list[HybridHit]:
    """Rank approved records; report field, channel, graph path, and evidence."""
    terms = _terms(query)
    graph = build_job_graph(postings)
    graph_matches = _graph_matches(graph, terms) if terms else _all_posting_graph_paths(graph)
    hits: list[HybridHit] = []

    for posting in postings:
        if not searchable(posting):
            continue
        if region and region.casefold() not in posting.region.casefold():
            continue
        values = _field_values(posting)
        term_fields: dict[str, set[str]] = {term: set() for term in terms}
        score = 0.0
        for field, field_values in values.items():
            normalized = tuple(value.casefold() for value in field_values if value)
            matched = {term for term in terms if any(term in value for value in normalized)}
            if matched:
                score += FIELD_WEIGHTS[field] * len(matched)
                for term in matched:
                    term_fields[term].add(field)

        paths = graph_matches.get(posting.posting_id, [])
        for path in paths:
            for term in path["matched_terms"]:
                term_fields[term].add(f"graph:{path['relationship']}")
            score += 2.0 * len(path["matched_terms"])

        matched_terms = tuple(term for term in terms if term_fields[term])
        if terms and not matched_terms:
            continue
        if not terms:
            score = float(len(paths))
        fields = tuple(sorted({field for matches in term_fields.values() for field in matches}))
        channels = tuple(channel for channel, present in (
            ("lexical", any(not field.startswith("graph:") for field in fields)),
            ("graph", bool(paths)),
        ) if present)
        relevant_evidence = (
            tuple(
                item for item in posting.evidence
                if item.field in fields or any(item.field in _path_evidence_fields(path["relationship"]) for path in paths)
            )
            if terms else posting.evidence
        )
        hits.append(HybridHit(
            posting=posting,
            score=score,
            matched_terms=matched_terms,
            matched_fields=fields,
            channels=channels,
            graph_paths=tuple(paths),
            evidence=relevant_evidence,
        ))

    hits.sort(key=lambda hit: (-hit.score, hit.posting.posting_id))
    return hits[:max(0, limit)]


def _path_evidence_fields(relationship: str) -> tuple[str, ...]:
    return {
        "HAS_ROLE": ("role_category",),
        "LOCATED_IN": ("region",),
        "REQUIRES_SKILL": ("required_skills",),
        "OFFERS_BENEFIT": ("benefits",),
        "POSTED_JOB": ("company_name",),
    }.get(relationship, ())
