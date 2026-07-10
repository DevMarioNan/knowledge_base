"""
End-to-end manual test for TrialBase RAG pipeline.

Usage:
  # 1. Generate sample PDFs first
  python scripts/generate_sample_pdfs.py

  # 2. Run E2E test (ensure backend is running)
  python scripts/e2e_test.py [--base-url http://localhost:8000]

Environment variables:
  TEST_EMAIL, TEST_PASSWORD - credentials (defaults: e2e@test.local / Test1234!)
"""

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).parent
TEST_SAMPLES = HERE / ".." / "test_samples"

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    os.system(f"{sys.executable} -m pip install httpx -q")
    import httpx


TEST_EMAIL = os.getenv("TEST_EMAIL", "e2e@example.org")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "Test1234!")
TEST_FULL_NAME = os.getenv("TEST_FULL_NAME", "E2E Test User")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

client = httpx.Client(base_url=BASE_URL, timeout=60)
token: str | None = None


def log(label: str, msg: str, obj: object = None):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {label:>12s}  {msg}")
    if obj is not None:
        text = json.dumps(obj, indent=2, default=str)
        for line in text.split("\n"):
            print(f"              {line}")


def api(method: str, path: str, **kwargs) -> httpx.Response:
    headers = kwargs.pop("headers", {})
    if token:
        headers.setdefault("Authorization", f"Bearer {token}")
    return getattr(client, method)(path, headers=headers, **kwargs)


def step(num: int, total: int, description: str):
    print(f"\n{'='*60}")
    print(f" STEP {num}/{total}: {description}")
    print(f"{'='*60}\n")


def register():
    response = api("post", "/api/auth/register", json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "full_name": TEST_FULL_NAME})
    if response.status_code == 201:
        log("OK", f"Registered user: {TEST_EMAIL}")
    elif response.status_code == 409:
        log("OK", f"User already exists: {TEST_EMAIL}")
    else:
        log("FAIL", f"Register failed: {response.status_code}", response.text)
        sys.exit(1)


def login():
    global token
    response = api("post", "/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert response.status_code == 200, f"Login failed: {response.status_code} {response.text}"
    data = response.json()
    token = data["access_token"]
    log("OK", f"Logged in. JWT: {token[:20]}...")


def create_trial():
    name = f"E2E Test Trial {uuid.uuid4().hex[:8]}"
    response = api("post", "/api/trials", json={"name": name})
    assert response.status_code in (200, 201), f"Create trial failed: {response.status_code} {response.text}"
    trial = response.json()
    log("OK", f"Trial created", {"id": trial["id"], "name": trial["name"]})
    return trial["id"]


def upload_documents(trial_id: str, pdf_dir: Path):
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    assert pdf_files, f"No PDFs found in {pdf_dir}. Run generate_sample_pdfs.py first."

    doc_ids = []
    for pdf_path in pdf_files:
        log("...", f"Uploading: {pdf_path.name}")
        with open(pdf_path, "rb") as f:
            response = api("post", f"/api/trials/{trial_id}/documents",
                           files={"file": (pdf_path.name, f, "application/pdf")})
        if response.status_code in (200, 201):
            doc = response.json()
            doc_ids.append(doc["id"])
            log("OK", f"Uploaded: {pdf_path.name}", {"id": doc["id"]})
        else:
            log("WARN", f"Upload failed for {pdf_path.name}: {response.status_code}", response.text)

    log("RESULT", f"Uploaded {len(doc_ids)}/{len(pdf_files)} documents successfully")
    return doc_ids


def wait_for_processing(trial_id: str, doc_ids: list[str], timeout_sec: int = 300):
    log("...", "Waiting for document processing...")
    start = time.time()
    pending = set(doc_ids)
    seen_errors = set()

    while pending and (time.time() - start) < timeout_sec:
        response = api("get", f"/api/trials/{trial_id}/documents")
        assert response.status_code == 200, f"List docs failed: {response.text}"
        docs = response.json()

        for doc in docs:
            doc_id = doc["id"]
            status = doc.get("status", "unknown")
            if doc_id in pending:
                elapsed = int(time.time() - start)
                if status == "ready":
                    pending.remove(doc_id)
                    log("OK", f"Doc {doc['filename']} ready ({elapsed}s)")
                elif status == "error":
                    pending.remove(doc_id)
                    seen_errors.add(doc_id)
                    log("WARN", f"Doc {doc['filename']} FAILED", doc.get("error_message", "unknown error"))
                else:
                    log("...", f"  {doc['filename']} = {status} ({elapsed}s)")

        if pending:
            time.sleep(5)

    if pending:
        log("FAIL", f"Timeout after {timeout_sec}s. Pending: {pending}")
        sys.exit(1)

    if seen_errors:
        log("WARN", f"{len(seen_errors)} documents had errors. Continuing with remaining.")

    log("OK", f"All documents processed ({int(time.time() - start)}s)")


def chat_query(trial_id: str, query: str) -> dict:
    """Send a chat query and return the full response."""
    log("...", f"Query: {query}")

    thread_id = None
    full_text = ""
    citations = []

    response = api("post", f"/api/trials/{trial_id}/chat",
                   json={"query": query, "thread_id": thread_id},
                   headers={"Accept": "text/event-stream"},
                   timeout=120)

    assert response.status_code == 200, f"Chat stream failed: {response.status_code} {response.text}"
    content_type = response.headers.get("content-type", "")

    if "text/event-stream" in content_type:
        for line in response.text.split("\n"):
            line = line.strip()
            if line.startswith("data: "):
                data = line[6:]
                try:
                    event = json.loads(data)
                    event_type = event.get("type", "")
                    if event_type == "token":
                        full_text += event.get("content", "")
                    elif event_type == "citations":
                        citations = event.get("citations", citations)
                    elif event_type == "done":
                        pass
                    elif event_type == "grounding_failure":
                        log("WARN", "Grounding failure detected - LLM could not answer from context")
                        return {"text": event.get("message", ""), "citations": [], "grounding_failure": True}
                    elif event_type == "error":
                        log("FAIL", f"Stream error: {event.get('message', '')}")
                        return {"text": "", "citations": [], "error": event.get("message", "")}
                except json.JSONDecodeError:
                    pass
    else:
        result = response.json()
        full_text = result.get("content", result.get("text", ""))
        citations = result.get("citations", [])

    return {"text": full_text, "citations": citations, "grounding_failure": False}


def verify_response(result: dict, query: str, min_citations: int = 1):
    text = result.get("text", "")
    citations = result.get("citations", [])

    if result.get("grounding_failure"):
        log("CHECK", "Grounding failure (expected if no relevant docs)")
        return True

    if not text:
        log("FAIL", "Empty response")
        return False

    word_count = len(text.split())
    log("OK", f"Response received ({word_count} words)")

    import re
    inline_citations = set(re.findall(r'\[(\d+)\]', text))
    total_citations = max(len(citations), len(inline_citations))

    if total_citations < min_citations:
        log("WARN", f"Only {total_citations} citation refs (expected >= {min_citations})", text[:200])
    else:
        log("OK", f"Has {total_citations} citation refs")

    log("RESPONSE", text[:500])

    return total_citations >= min_citations


def cleanup_trial(trial_id: str):
    log("...", f"Cleaning up trial {trial_id}...")
    response = api("delete", f"/api/trials/{trial_id}")
    if response.status_code in (200, 204):
        log("OK", "Trial deleted")
    else:
        log("WARN", f"Could not delete trial: {response.status_code}")


def main():
    parser = argparse.ArgumentParser(description="TrialBase E2E Test")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--no-cleanup", action="store_true", help="Keep trial after test")
    args = parser.parse_args()

    global BASE_URL
    if args.base_url:
        BASE_URL = args.base_url

    total_steps = 7

    step(1, total_steps, "User Registration")
    register()

    step(2, total_steps, "User Login")
    login()

    step(3, total_steps, "Create Trial")
    trial_id = create_trial()

    try:
        step(4, total_steps, "Upload Documents")
        if not TEST_SAMPLES.exists():
            log("FAIL", f"Sample PDF directory not found: {TEST_SAMPLES}")
            log("INFO", "Run `python scripts/generate_sample_pdfs.py` first")
            sys.exit(1)
        doc_ids = upload_documents(trial_id, TEST_SAMPLES)

        step(5, total_steps, "Wait for Processing")
        wait_for_processing(trial_id, doc_ids)

        step(6, total_steps, "Chat Queries")
        queries = [
            "What is the primary objective of the xanomeline-trospium study?",
            "What were the main adverse events reported in the safety report?",
            "What are the key inclusion criteria for this clinical trial?",
            "How will the primary efficacy analysis be performed?",
        ]

        passed = 0
        for i, query in enumerate(queries, 1):
            print(f"\n  --- Query {i}/{len(queries)} ---")
            result = chat_query(trial_id, query)
            if verify_response(result, query, min_citations=1):
                passed += 1
            print()

        step(7, total_steps, "Summary")
        print(f"\n  Queries passed: {passed}/{len(queries)}")
        if passed == len(queries):
            log("PASS", "All E2E tests passed!")
        else:
            log("WARN", f"{len(queries) - passed} queries had issues")

    finally:
        if not args.no_cleanup:
            cleanup_trial(trial_id)
        else:
            log("INFO", f"Trial {trial_id} kept (--no-cleanup)")


if __name__ == "__main__":
    main()
