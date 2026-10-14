import argparse
import hashlib
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

COLLECTION_NAME = "sally_sophia_evidence_claims"

# Embedding Vectorizer
try:
    from fastembed import TextEmbedding
    _embed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    def get_query_vector(text: str):
        return list(_embed_model.embed([text]))[0].tolist()
except Exception:
    def get_query_vector(text: str, dim: int = 384):
        h = hashlib.sha256(text.encode("utf-8")).digest()
        return [((b / 255.0) * 2 - 1) for b in (h * (dim // 32 + 1))[:dim]]

def get_clients():
    # 1. Qdrant Client
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    if not qdrant_url or not qdrant_key:
        raise ValueError("Missing QDRANT_URL or QDRANT_API_KEY in .env")
    
    from qdrant_client import QdrantClient
    q_client = QdrantClient(url=qdrant_url, api_key=qdrant_key, check_compatibility=False)

    # 2. Neo4j Client
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_pwd = os.getenv("NEO4J_PASSWORD")
    if not neo4j_uri or not neo4j_pwd:
        raise ValueError("Missing NEO4J_URI or NEO4J_PASSWORD in .env")

    from neo4j import GraphDatabase
    n_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pwd))

    return q_client, n_driver

def hybrid_search(query: str, top_k: int = 3):
    q_client, n_driver = get_clients()

    # Step 1: Semantic Vector Search in Qdrant (using query_points)
    query_vector = get_query_vector(query)
    
    if hasattr(q_client, "query_points"):
        res = q_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k
        )
        search_hits = res.points if hasattr(res, "points") else res
    else:
        search_hits = q_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k
        )

    if not search_hits:
        print("No matching claims found in vector index.")
        return []

    claim_ids = [hit.payload.get("claim_id") for hit in search_hits if hit.payload]
    score_map = {hit.payload.get("claim_id"): hit.score for hit in search_hits if hit.payload}

    # Step 2: Knowledge Graph Traversal in Neo4j
    cypher_query = """
    MATCH (c:Claim)
    WHERE c.id IN $claim_ids
    OPTIONAL MATCH (c)-[:DERIVED_FROM]->(s:Source)
    OPTIONAL MATCH (c)-[:GOVERNED_BY]->(a:Authority)
    OPTIONAL MATCH (c)-[:APPLIES_TO]->(j:Jurisdiction)
    RETURN c.id AS claim_id,
           c.text AS claim_text,
           c.type AS claim_type,
           c.status AS status,
           c.verification_status AS verification,
           c.evidence_url AS evidence_url,
           c.last_reviewed AS last_reviewed,
           collect(DISTINCT s.id) AS sources,
           collect(DISTINCT a.name) AS authorities,
           collect(DISTINCT j.name) AS jurisdictions
    """

    enriched_records = []
    with n_driver.session() as session:
        result = session.run(cypher_query, claim_ids=claim_ids)
        for record in result:
            cid = record["claim_id"]
            data = dict(record)
            data["similarity_score"] = score_map.get(cid, 0.0)
            enriched_records.append(data)

    n_driver.close()

    # Sort results by vector similarity score descending
    enriched_records.sort(key=lambda r: r["similarity_score"], reverse=True)
    return enriched_records

def print_evidence_report(query: str, records: list):
    print("\n" + "=" * 70)
    print(f"QUERY: \"{query}\"")
    print(f"RETRIEVED: {len(records)} Evidence Cards (Qdrant Semantic + Neo4j Graph)")
    print("=" * 70)

    for idx, r in enumerate(records, start=1):
        print(f"\n[Evidence Card #{idx}] {r['claim_id']}  (Similarity: {r['similarity_score']:.4f})")
        print(f"  Claim:        {r['claim_text']}")
        print(f"  Type:         {r['claim_type']} | Status: {r['status']} | Verification: {r['verification']}")
        
        auths = ", ".join(r["authorities"]) if r["authorities"] else "Unspecified"
        juris = ", ".join(r["jurisdictions"]) if r["jurisdictions"] else "Global / Multi-jurisdiction"
        sources = ", ".join(r["sources"]) if r["sources"] else "N/A"
        
        print(f"  Authority:    {auths}")
        print(f"  Jurisdiction: {juris}")
        print(f"  Source ID:    {sources}")
        if r.get("evidence_url"):
            print(f"  Evidence URL: {r['evidence_url']}")
        print("-" * 70)

def main():
    parser = argparse.ArgumentParser(description="Sally Sophia Hybrid RAG Retriever")
    parser.add_argument("--query", "-q", type=str, help="Clinical AI research or governance query")
    parser.add_argument("--top_k", "-k", type=int, default=3, help="Number of evidence claims to retrieve")
    args = parser.parse_args()

    if args.query:
        records = hybrid_search(args.query, top_k=args.top_k)
        print_evidence_report(args.query, records)
        return

    # Interactive CLI Mode
    print("==================================================================")
    print("SALLY SOPHIA - Hybrid RAG Clinical AI Knowledge Retriever (CLI)")
    print("Type your clinical AI or governance question, or 'exit' to quit.")
    print("==================================================================")

    while True:
        try:
            q = input("\nEnter query > ").strip()
            if not q:
                continue
            if q.lower() in ("exit", "quit", "q"):
                print("Exiting retriever.")
                break
            records = hybrid_search(q, top_k=args.top_k)
            print_evidence_report(q, records)
        except KeyboardInterrupt:
            print("\nRetriever stopped.")
            break
        except Exception as e:
            print(f"Error executing hybrid search: {e}")

if __name__ == "__main__":
    main()
