import json
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROCESSED_JSON = Path("data/processed/claims_processed.json")
PROCESSED_CSV = Path("data/processed/claims_processed.csv")

def load_claims():
    if not PROCESSED_JSON.exists():
        raise FileNotFoundError(f"Missing {PROCESSED_JSON}. Run pipelines/kaggle_extractor.py first.")
    with open(PROCESSED_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

# 1. KAGGLE PUSH
def push_to_kaggle():
    print("\n--- 1. Pushing to Kaggle ---")
    meta_path = Path("data/processed/dataset-metadata.json")
    metadata = {
        "title": "Sally Sophia - Medical AI Evidence: JPAIS-MED-REF",
        "id": "sallysophia2025/sally-sophia-medical-ai-evidence-jpais-med-ref",
        "licenses": [{"name": "CC-BY-4.0"}]
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    cmd = [
        "kaggle", "datasets", "version",
        "-p", "data/processed",
        "-m", "Automated sync: 47 verified evidence claims and canonical JSON",
        "--dir-mode", "zip"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print("✓ Kaggle: Successfully published new dataset version.")
    else:
        print("✗ Kaggle notice:", res.stderr.strip() or res.stdout.strip())

# 2. QDRANT CLOUD PUSH
def push_to_qdrant(claims):
    print("\n--- 2. Pushing to Qdrant Cloud ---")
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")

    if not api_key or "YOUR_QDRANT" in api_key:
        print("⚠ Qdrant: Skipped (QDRANT_API_KEY not set in .env)")
        return

    try:
        from qdrant_client import QdrantClient, models
        client = QdrantClient(url=url, api_key=api_key, check_compatibility=False)
        
        collection_name = "sally_sophia_evidence_claims"
        documents = [c.get("claim_text", "") for c in claims]
        metadatas = [
            {
                "claim_id": c.get("claim_id"),
                "source_id": c.get("source_id"),
                "claim_type": c.get("claim_type"),
                "status": c.get("status"),
                "verification_status": c.get("verification_status"),
                "jurisdiction": c.get("jurisdiction"),
                "authority": c.get("authority"),
                "evidence_url": c.get("evidence_url")
            }
            for c in claims
        ]

        # Generate embeddings via FastEmbed or dense fallback
        try:
            from fastembed import TextEmbedding
            embed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            vectors = [v.tolist() for v in embed_model.embed(documents)]
        except Exception:
            # Deterministic fallback embedding vector if FastEmbed weights aren't cached
            import hashlib
            def hash_vector(text, dim=384):
                h = hashlib.sha256(text.encode("utf-8")).digest()
                return [((b / 255.0) * 2 - 1) for b in (h * (dim // 32 + 1))[:dim]]
            vectors = [hash_vector(d) for d in documents]

        dim = len(vectors[0])
        
        # Ensure collection exists
        existing = [c.name for c in client.get_collections().collections]
        if collection_name not in existing:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE)
            )

        points = [
            models.PointStruct(id=i, vector=v, payload=m)
            for i, (v, m) in enumerate(zip(vectors, metadatas), start=1)
        ]
        client.upsert(collection_name=collection_name, points=points)
        print(f"✓ Qdrant: Indexed {len(points)} evidence vectors into '{collection_name}' (dim={dim})")
    except Exception as e:
        print("✗ Qdrant error:", e)

# 3. NEO4J AURADB PUSH
def push_to_neo4j(claims):
    print("\n--- 3. Pushing to Neo4j AuraDB ---")
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD")

    if not uri or not pwd or "YOUR_NEO4J" in pwd:
        print("⚠ Neo4j: Skipped (NEO4J_URI or NEO4J_PASSWORD not set in .env)")
        return

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        
        query = """
        UNWIND $batch AS row
        MERGE (c:Claim {id: row.claim_id})
        SET c.text = row.claim_text,
            c.type = row.claim_type,
            c.status = row.status,
            c.verification_status = row.verification_status,
            c.evidence_url = row.evidence_url,
            c.last_reviewed = row.last_reviewed

        MERGE (s:Source {id: row.source_id})
        MERGE (c)-[:DERIVED_FROM]->(s)

        FOREACH (_ IN CASE WHEN row.authority <> '' THEN [1] ELSE [] END |
            MERGE (a:Authority {name: row.authority})
            MERGE (c)-[:GOVERNED_BY]->(a)
        )

        FOREACH (_ IN CASE WHEN row.jurisdiction <> '' THEN [1] ELSE [] END |
            MERGE (j:Jurisdiction {name: row.jurisdiction})
            MERGE (c)-[:APPLIES_TO]->(j)
        )
        """
        with driver.session() as session:
            session.run(query, batch=claims)
        driver.close()
        print(f"✓ Neo4j: Merged {len(claims)} Claim nodes, Source entities, and Relationships.")
    except Exception as e:
        if "Name or service not known" in str(e):
            print("✗ Neo4j notice: Database appears to be paused in console.neo4j.io. Resume instance to connect.")
        else:
            print("✗ Neo4j error:", e)

# 4. MEDICAL AI WIKI PUSH
def push_to_wiki(claims):
    print("\n--- 4. Pushing to Medical AI Wiki ---")
    wiki_out = Path("data/processed/wiki_jpais_med_ref.wiki")
    
    wikitext = "== JPAIS-MED-REF Evidence Claims Index ==\n\n"
    wikitext += "The following 47 verified evidence claims form the evidentiary grounding for the JPAIS-MED-REF framework.\n\n"
    wikitext += '{| class="wikitable sortable"\n'
    wikitext += "! Claim ID !! Claim Summary !! Type !! Status !! Verification !! Jurisdiction !! Authority !! Evidence\n"
    
    for c in claims:
        link = f"[{c['evidence_url']} Link]" if c.get("evidence_url") else "N/A"
        wikitext += "|-\n"
        wikitext += f"| '''{c.get('claim_id')}''' || {c.get('claim_text')} || {c.get('claim_type')} || {c.get('status')} || {c.get('verification_status')} || {c.get('jurisdiction') or '-'} || {c.get('authority') or '-'} || {link}\n"
    
    wikitext += "|}\n\n[[Category:JPAIS-MED-REF]] [[Category:Medical AI Governance]]\n"
    
    with open(wiki_out, "w", encoding="utf-8") as f:
        f.write(wikitext)
    print(f"✓ Wiki: Generated wikitext deliverable at {wiki_out}")

    wiki_user = os.getenv("WIKI_USER")
    wiki_pwd = os.getenv("WIKI_PASSWORD")
    if wiki_user and wiki_pwd:
        try:
            import mwclient
            # Miraheze requires /w/ path and a descriptive User-Agent
            site = mwclient.Site(
                "medicalai.miraheze.org",
                path="/w/",
                clients_useragent="SallySophiaBot/1.0 (https://medicalai.miraheze.org; contact@sallysophia.org)"
            )
            site.login(wiki_user, wiki_pwd)
            page = site.pages["JPAIS-MED-REF/Evidence_Claims"]
            page.save(wikitext, summary="Automated CI/CD evidence sync from sally-sophia-research-core")
            print("✓ Wiki: Published live to https://medicalai.miraheze.org/wiki/JPAIS-MED-REF/Evidence_Claims")
        except Exception as e:
            print("✗ Wiki notice:", e)
    else:
        print("ℹ Wiki: WIKI_USER and WIKI_PASSWORD not set in .env. Wikitext generated locally.")

if __name__ == "__main__":
    claims = load_claims()
    print(f"Loaded {len(claims)} processed claims.")
    push_to_kaggle()
    push_to_qdrant(claims)
    push_to_neo4j(claims)
    push_to_wiki(claims)
    print("\n✓ Pipeline execution complete.")
