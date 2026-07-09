# CONTEXT — TrialBase Domain Glossary

## Trial

A clinical trial managed by Lumina (e.g., "Phase III ALX-204"). A trial has a name, a list of members, and a set of uploaded documents. Trials are the top-level organizational unit — all documents, threads, and evaluation datasets belong to exactly one trial.

## User

A Lumina employee authenticated via email/password. Any user can create a trial, upload documents, and ask questions. A user becomes a trial member when they create a trial or are invited by an existing member.

## Trial Membership

The association between a user and a trial. Users invited to a trial become members with `member` role. The trial creator is the `owner`. Any member can invite other Lumina users.

## Document

A PDF uploaded to a trial. Documents pass through an async lifecycle: `uploaded → parsing → chunking → embedding → ready`. Failed documents reach a `failed` state with an error message. Documents can be soft-deleted (chunks removed from Qdrant, but existing citations preserved).

## Document Chunk

A fragment of a document produced by the hybrid chunking strategy. Structure-aware mode splits at PDF bookmarks or section headers; recursive character mode is the fallback. Each chunk has metadata: `section_title`, `section_number`, `page_number`, `chunk_index`.

## Chat Thread

A conversation within a trial, visible to all trial members. Threads are auto-created on the first user message with an auto-generated title. Every message is attributed to the user who sent it.

## Message

A single turn in a chat thread, either a user's question or the assistant's answer. Assistant messages include inline numeric citations `[n]` and a structured source list.

## Citation

An inline reference linking a claim in the assistant's answer to a specific document chunk. Displayed as `[n]` markers that render as clickable tooltips with source passages and document/page references.

## Grounding Failure

When the retrieved context does not contain sufficient information to answer the user's question. The assistant responds with "I don't know based on the provided documents for this trial" and the UI shows a distinct grounding failure state.

## Evaluation Dataset

A collection of (question, ground-truth answer) pairs belonging to a trial, created in-app by medical monitors.

## Evaluation Run

A manual trigger that processes a trial's evaluation dataset through the RAG pipeline and computes RAGAS metrics (faithfulness, answer relevancy, context precision, context recall). Results are stored and tracked over time.

## Ingestion

The async process of extracting text from a PDF, chunking it, generating embeddings via OpenAI, and storing the vectors in Qdrant with metadata.

## Hybrid Retrieval

Two-stage search: dense vector search (OpenAI embeddings + Qdrant) fused with keyword search (Qdrant full-text / BM25) via Reciprocal Rank Fusion (RRF), followed by mandatory Cohere reranking.
