# Client brief — Lumina Clinical Research

## The client

**Lumina Clinical Research** is a mid-sized Contract Research Organization (CRO) with ~150 clinical trial managers, medical monitors, and regulatory affairs specialists. They manage Phase II and Phase III clinical trials for mid-cap biotech and pharmaceutical companies.

## How Lumina makes money

- They are paid by biotech sponsors to execute clinical trials, manage hospital trial sites, collect patient data, and ensure strict regulatory compliance.
- Their reputation hinges on zero protocol deviations, clean data, and passing FDA/EMA audits without findings.

## How they add value

- Clinical trial protocols are notoriously dense, often running 200+ pages with complex inclusion/exclusion criteria, dosing schedules, and adverse event reporting rules.
- Lumina's staff translates these massive documents into daily operational guidance for hundreds of hospital site coordinators and nurses.
- The value is *precision and speed*: giving site staff immediate, accurate answers so patient care and data collection never stall.

## The problem

Every clinical trial manager and medical monitor spends roughly **half of every day** doing document cross-referencing — opening the master protocol, checking the latest protocol amendment, cross-referencing the Investigator's Brochure, and digging through site-specific SOPs to answer questions from trial sites. 

This lookup work is:

- High-stakes (a wrong answer causes a protocol deviation or patient safety issue)
- Repetitive (site coordinators ask the same questions about lab thresholds or dosing windows constantly)
- Fragmented (documents are constantly updated, version-controlled in SharePoint, and scattered across dense PDFs)

## What they want

An internal RAG Knowledge Base App — let's call it **TrialBase** — where any Lumina trial manager can:

- Upload multiple documents for a specific trial (Master Protocol, Amendments, Investigator Brochure, Site Manuals).
- Ask questions in plain English about trial procedures.
- Get a sourced answer that cites the specific document, section, and page.
- Trust the answer enough to relay it directly to a clinical site.
- Use an **evaluation dashboard** to test the system's accuracy on a gold-standard Q&A dataset before deploying it to a new trial.

## Example user questions

The system needs to handle complex, multi-document queries over uploaded PDFs, utilizing hybrid search and re-ranking to find specific clinical criteria:

1. What are the exact exclusion criteria regarding prior cardiovascular events in the Phase III ALX-204 trial, and did Amendment 3 change the time-window for these events?
2. If a patient experiences a Grade 3 hepatic adverse event, what is the required dose modification and the reporting timeline to the sponsor according to the Investigator's Brochure?
3. Compare the blood draw schedules for Visit 4 and Visit 5. Are fasting labs required for both, and what is the allowable window in days?
4. How should the site handle investigational product storage temperature excursions, and what specific form needs to be submitted to Lumina's QA team?
5. Across the Master Protocol and the latest Site Manual, what are the rules for allowing a patient to continue on concomitant prohibited medications if they were already taking them prior to screening?

## What "trust" means here

This is clinical research. A hallucinated answer can lead to a patient safety issue or an FDA audit finding. The bot must:

- **Never invent clinical rules.** If the protocol is silent, it says so.
- **Always cite.** Every claim links to the source document, section, and page.
- **Show the underlying passage** so the medical monitor can verify the exact wording in one click.
- **Be auditable.** The evaluation dashboard must prove the system is retrieving the correct context and generating faithful answers before it touches a live trial.

## Constraints

- **Corpus:** Highly specific, user-uploaded clinical trial documents (PDFs, DOCX) per project.
- **Users:** ~150 Lumina internal staff (trial managers, medical monitors, QA).
- **Login:** Lumina corporate email addresses.
- **Tech Stack:** Python, FastAPI, Qdrant (self-hosted via Docker) or Pinecone, OpenAI embeddings, Cohere Rerank, RAGAS for the evaluation dashboard, SQLAlchemy, React, Tailwind, Shadcn.
- **Hosting:** Must run in Lumina's secure AWS environment (Dockerized) to maintain HIPAA/GCP compliance.

## Out of scope (explicitly)

- Medical advice to patients or doctors.
- Integration with EDC (Electronic Data Capture) systems like Medidata Rave.
- Multi-tenant access for the biotech sponsors (internal Lumina use only for now).
- Automated regulatory submissions.
- Mobile app.

## Definition of done

The Head of Clinical Operations and 5 senior medical monitors run a simulated trial Q&A audit using the evaluation dashboard. If the RAGAS metrics (faithfulness and context precision) exceed the agreed threshold, and the pilot group reports it saves them at least 2 hours of document-hunting per day, Lumina rolls it out to all active Phase III trials.