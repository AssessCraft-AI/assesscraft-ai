import logging
from typing import List, Dict, Any, Optional
from app.config import settings
from app.models import SourceCitation
from app.services.firestore import db

logger = logging.getLogger("assesscraft.search")

_discovery_client = None


def get_discovery_client():
    global _discovery_client
    if _discovery_client is None and settings.GCP_PROJECT_ID:
        try:
            from google.cloud import discoveryengine_v1 as discoveryengine
            client_options = {}
            if settings.VERTEX_SEARCH_LOC != "global":
                client_options["api_endpoint"] = f"{settings.VERTEX_SEARCH_LOC}-discoveryengine.googleapis.com"
            _discovery_client = discoveryengine.SearchServiceClient(client_options=client_options)
        except Exception as e:
            logger.warning(f"Could not initialize Vertex AI Search client ({e}). Using local fallback search.")
            _discovery_client = None
    return _discovery_client


async def search_knowledge_base(
    query: str,
    course_id: str,
    kinds: Optional[List[str]] = None,
    top_k: int = 5,
) -> List[SourceCitation]:
    """
    Queries Vertex AI Search data store for the course.
    Returns ranked list of SourceCitations with snippets and metadata.
    """
    client = get_discovery_client()

    # 1. Cloud Search via Vertex AI Search (Discovery Engine)
    if client and settings.GCP_PROJECT_ID and settings.SEARCH_DATASTORE_ID:
        try:
            from google.cloud import discoveryengine_v1 as discoveryengine

            serving_config = client.serving_config_path(
                project=settings.GCP_PROJECT_ID,
                location=settings.VERTEX_SEARCH_LOC,
                data_store=settings.SEARCH_DATASTORE_ID,
                serving_config="default_config",
            )

            filter_expr = f'courseId: ANY("{course_id}")'
            if kinds:
                kinds_filter = ", ".join(f'"{k}"' for k in kinds)
                filter_expr += f' AND kind: ANY({kinds_filter})'

            request = discoveryengine.SearchRequest(
                serving_config=serving_config,
                query=query,
                page_size=top_k,
                filter=filter_expr,
                query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                    condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO
                ),
            )
            response = client.search(request)

            citations = []
            for result in response.results:
                doc = result.document
                data = doc.derived_struct_data or {}
                snippets = data.get("snippets", [])
                snippet_text = snippets[0].get("snippet") if snippets else str(data.get("extractive_answers", ""))
                citations.append(
                    SourceCitation(
                        docId=doc.id,
                        title=data.get("title") or doc.id,
                        snippet=snippet_text or query,
                        uri=data.get("link"),
                    )
                )
            if citations:
                return citations
        except Exception as e:
            logger.warning(f"Vertex AI Search failed ({e}); using local Firestore search fallback.")

    # 2. Local Fallback Search over course documents & pastItems
    filters = [("courseId", "==", course_id)]
    all_docs = await db.query("documents", filters=filters)
    if kinds:
        all_docs = [d for d in all_docs if d.get("kind") in kinds]

    query_terms = [t.lower() for t in query.split() if len(t) > 2]
    scored_results = []

    for d in all_docs:
        body = d.get("fullText") or d.get("contentSnippet") or ""
        # Score ~800-char passages so the citation is the relevant part, not the document's opening.
        passages = [body[i:i + 800] for i in range(0, len(body), 800)] or [""]
        best_score, best_passage = max(
            ((sum(p.lower().count(t) for t in query_terms), p) for p in passages), key=lambda x: x[0]
        )
        best_score += sum((d.get("title") or "").lower().count(t) for t in query_terms)
        if best_score > 0 or not query_terms:
            scored_results.append((d, best_score, best_passage))

    scored_results.sort(key=lambda x: x[1], reverse=True)

    citations = []
    for d, _, passage in scored_results[:top_k]:
        snippet = passage.strip() or f"Excerpt from {d.get('title')}"
        citations.append(
            SourceCitation(
                docId=d.get("id"),
                title=d.get("title"),
                snippet=snippet[:600],
                uri=d.get("gcsUri"),
            )
        )

    # Also search pastItems if kinds include past_paper
    if not kinds or "past_paper" in kinds:
        past_items = await db.query("pastItems", filters=[("courseId", "==", course_id)])
        for p in past_items:
            p_text = p.get("text", "")
            p_lower = p_text.lower()
            p_score = sum(p_lower.count(term) for term in query_terms)
            if p_score > 0:
                citations.append(
                    SourceCitation(
                        docId=p.get("docId", "past-items"),
                        title=f"{course_id} Past Exam {p.get('year')}",
                        snippet=p_text[:280],
                    )
                )

    return citations[:top_k]
