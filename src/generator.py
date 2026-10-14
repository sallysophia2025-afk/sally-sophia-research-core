import argparse
import json
import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

from src.retriever import hybrid_search

load_dotenv()

SYSTEM_INSTRUCTION = """You are SALLY SOPHIA's Evidence-Grounded Medical AI & Healthcare Knowledge Synthesis Engine.
Your core mission is to synthesize an accurate, concise, and structured answer to the user's question STRICTLY based on the provided Evidence Cards.

MANDATORY RULES:
1. Ground every substantive statement in the provided evidence. Cite the corresponding Claim ID and Authority.
2. Embed clickable Markdown links to the primary evidence URL whenever referencing a regulation, standard, or article (e.g., [KMK No. 1423/2022](https://...)).
3. Do NOT extrapolate, hallucinate, or assume facts not explicitly stated in the evidence.
4. If the retrieved evidence is incomplete or does not fully answer the question, explicitly disclose the limitation.
5. Conclude with a 1-sentence summary of the jurisdictional and institutional custody implications.
"""

def generate_with_gemini(prompt: str, api_key: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024}
    }
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
    if response.status_code == 200:
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    raise RuntimeError(f"Gemini API error ({response.status_code}): {response.text}")

def generate_with_openai(prompt: str, api_key: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    if response.status_code == 200:
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    raise RuntimeError(f"OpenAI API error ({response.status_code}): {response.text}")

def deterministic_grounded_summary(query: str, records: list) -> str:
    """Deterministic fallback synthesis when no LLM API key is present in .env."""
    lines = [
        f"Based on {len(records)} retrieved evidence claims from the SALLY SOPHIA knowledge base:\n"
    ]
    for r in records:
        link = f"([Primary Source]({r['evidence_url']}))" if r.get("evidence_url") else ""
        auth = r['authorities'][0] if r.get('authorities') else 'Governance Standard'
        juris = f" in {r['jurisdictions'][0]}" if r.get('jurisdictions') else ""
        lines.append(f"* **{r['claim_id']} ({auth}{juris})**: {r['claim_text']} {link}")
    
    lines.append("\n**Jurisdictional Context**: Under JPAIS-MED-REF standards, institutional medical record custody remains non-delegable to external AI processors.")
    lines.append("\n*(Note: Set GEMINI_API_KEY in .env for full generative prose synthesis).*")
    return "\n".join(lines)

def synthesize_answer(query: str, top_k: int = 3):
    print(f"\n[1/2] Retrieving evidence cards across Qdrant & Neo4j...")
    records = hybrid_search(query, top_k=top_k)
    
    if not records:
        return "No relevant evidence cards found to answer the query.", []

    print(f"[2/2] Synthesizing grounded response across {len(records)} evidence cards...")

    # Assemble context bundle
    evidence_context = []
    for r in records:
        evidence_context.append(
            f"Claim ID: {r['claim_id']}\n"
            f"Claim Text: {r['claim_text']}\n"
            f"Type: {r['claim_type']} | Status: {r['status']} | Verification: {r['verification']}\n"
            f"Governing Authority: {', '.join(r['authorities']) if r['authorities'] else 'Unspecified'}\n"
            f"Jurisdiction: {', '.join(r['jurisdictions']) if r['jurisdictions'] else 'Global'}\n"
            f"Evidence URL: {r.get('evidence_url', 'N/A')}\n"
            f"Similarity Score: {r['similarity_score']:.4f}\n"
        )
    
    prompt = f"RESEARCH QUESTION: {query}\n\nRETRIEVED EVIDENCE CARDS:\n" + "\n---\n".join(evidence_context)

    # Route to available LLM or deterministic fallback
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key:
        try:
            synthesis = generate_with_gemini(prompt, gemini_key)
        except Exception as e:
            print(f"Warning: Gemini call failed ({e}), falling back...")
            synthesis = deterministic_grounded_summary(query, records)
    elif openai_key:
        try:
            synthesis = generate_with_openai(prompt, openai_key)
        except Exception as e:
            print(f"Warning: OpenAI call failed ({e}), falling back...")
            synthesis = deterministic_grounded_summary(query, records)
    else:
        synthesis = deterministic_grounded_summary(query, records)

    return synthesis, records

def print_grounded_report(query: str, synthesis: str, records: list):
    print("\n" + "=" * 78)
    print("SALLY SOPHIA — Evidence-Grounded Medical AI Synthesis")
    print("=" * 78)
    print(f"QUESTION: {query}\n")
    print("### Grounded Clinical / Regulatory Synthesis:")
    print(synthesis)
    print("\n" + "-" * 78)
    print("### Evidentiary Provenance Table:")
    print(f"{'Claim ID':<15} | {'Similarity':<10} | {'Authority':<30} | {'Jurisdiction'}")
    print("-" * 78)
    for r in records:
        auth = (r['authorities'][0][:28] + "..") if r.get('authorities') and len(r['authorities'][0]) > 28 else (r['authorities'][0] if r.get('authorities') else 'N/A')
        juris = r['jurisdictions'][0] if r.get('jurisdictions') else 'Global'
        print(f"{r['claim_id']:<15} | {r['similarity_score']:<10.4f} | {auth:<30} | {juris}")
    print("=" * 78)
    print("DISCLAIMER: Analysis synthesized under JPAIS-MED-REF evidence protocols.")
    print("This output is for research and governance. It does not replace clinical judgment.")
    print("=" * 78 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Sally Sophia Grounded Answer Generator")
    parser.add_argument("--query", "-q", type=str, help="Research or governance query")
    parser.add_argument("--top_k", "-k", type=int, default=3, help="Number of evidence cards to retrieve")
    args = parser.parse_args()

    if args.query:
        synthesis, records = synthesize_answer(args.query, top_k=args.top_k)
        print_grounded_report(args.query, synthesis, records)
        return

    print("==================================================================")
    print("SALLY SOPHIA — Grounded Medical AI Synthesis Engine (Interactive)")
    print("Type your clinical AI or governance question, or 'exit' to quit.")
    print("==================================================================")

    while True:
        try:
            q = input("\nEnter Question > ").strip()
            if not q:
                continue
            if q.lower() in ("exit", "quit", "q"):
                print("Exiting generator.")
                break
            synthesis, records = synthesize_answer(q, top_k=args.top_k)
            print_grounded_report(q, synthesis, records)
        except KeyboardInterrupt:
            print("\nGenerator stopped.")
            break
        except Exception as e:
            print(f"Error during synthesis: {e}")

if __name__ == "__main__":
    main()
