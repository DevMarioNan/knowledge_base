import uuid
from datetime import datetime

import structlog
from qdrant_client import AsyncQdrantClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import (
    EvaluationDataset,
    EvaluationQuestion,
    EvaluationRun,
    EvaluationRunQuestion,
    TrialSettings,
    User,
)
from app.ingestion.embedder import embed_texts
from app.llm.client import generate
from app.retrieval.hybrid import hybrid_search
from app.retrieval.reranker import rerank
from app.retrieval.types import RetrievedChunk

logger = structlog.get_logger()


async def _retrieve_for_question(
    qdrant: AsyncQdrantClient,
    trial_id: str,
    question: str,
    top_k: int = 10,
    top_n: int = 5,
    rerank_model: str | None = None,
) -> tuple[list[RetrievedChunk], str]:
    vectors = await embed_texts([question])
    query_vector = vectors[0]

    raw_chunks = await hybrid_search(
        qdrant=qdrant,
        collection=settings.vector_collection_name,
        trial_id=trial_id,
        query_text=question,
        query_vector=query_vector,
        top_k=top_k,
    )

    retrieved = [
        RetrievedChunk(
            chunk_id=c["chunk_id"],
            document_id=c["document_id"],
            content=c["content"],
            score=c.get("rrf_score", c.get("score", 0.0)),
            source_filename=c.get("source_filename", ""),
            page_number=c.get("page_number"),
            section_title=c.get("section_title"),
            section_number=c.get("section_number"),
            chunk_index=c.get("chunk_index", 0),
        )
        for c in raw_chunks
    ]

    reranked = await rerank(
        query=question,
        chunks=retrieved,
        model=rerank_model,
        top_n=top_n,
    )

    return reranked


async def _generate_answer(
    question: str, chunks: list[RetrievedChunk], model: str | None = None
) -> str:
    context_text = "\n\n".join(
        f"[{i+1}] {c.content}" for i, c in enumerate(chunks)
    )
    prompt = (
        "You are a clinical trial document analyst. Answer the question based strictly "
        "on the provided context. If the context does not contain the answer, say "
        "'I don't know based on the provided documents'.\n\n"
        f"Context:\n{context_text}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )
    result = await generate(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        stream=False,
    )
    return result if isinstance(result, str) else ""


async def _compute_ragas_metrics(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
) -> list[dict[str, float]]:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    ragas_metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]

    data = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }
    dataset = Dataset.from_dict(data)

    llm = LangchainLLMWrapper.from_model_name(settings.llm_model)
    result = evaluate(
        dataset=dataset,
        metrics=ragas_metrics,
        llm=llm,
    )

    scores_per_row: list[dict[str, float]] = []
    df = result.to_pandas()
    for _, row in df.iterrows():
        scores_per_row.append({
            "faithfulness": float(row.get("faithfulness", 0) or 0),
            "answer_relevancy": float(row.get("answer_relevancy", 0) or 0),
            "context_precision": float(row.get("context_precision", 0) or 0),
            "context_recall": float(row.get("context_recall", 0) or 0),
        })
    return scores_per_row


async def run_evaluation(
    db: AsyncSession,
    qdrant: AsyncQdrantClient,
    trial_id: str,
    dataset_id: str,
    user: User,
) -> EvaluationRun:
    dataset_id_uuid = uuid.UUID(dataset_id)
    trial_id_uuid = uuid.UUID(trial_id)

    result = await db.execute(
        select(EvaluationDataset).where(EvaluationDataset.id == dataset_id_uuid)
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise ValueError("Dataset not found")

    questions_result = await db.execute(
        select(EvaluationQuestion)
        .where(EvaluationQuestion.dataset_id == dataset_id_uuid)
        .order_by(EvaluationQuestion.created_at)
    )
    questions = questions_result.scalars().all()
    if not questions:
        raise ValueError("Dataset has no questions")

    settings_result = await db.execute(
        select(TrialSettings).where(TrialSettings.trial_id == trial_id_uuid)
    )
    trial_settings = settings_result.scalar_one_or_none()
    top_k = trial_settings.top_k_retrieval if trial_settings else 10
    top_n = trial_settings.top_n_rerank if trial_settings else 5
    rerank_model = trial_settings.cohere_rerank_model if trial_settings else None
    llm_model = trial_settings.llm_model if trial_settings else None

    run = EvaluationRun(
        trial_id=trial_id_uuid,
        dataset_id=dataset_id_uuid,
        status="running",
        created_by=user.id,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    try:
        question_texts: list[str] = []
        answers: list[str] = []
        contexts_list: list[list[str]] = []
        ground_truths: list[str] = []

        for q in questions:
            retrieved_chunks = await _retrieve_for_question(
                qdrant=qdrant,
                trial_id=trial_id,
                question=q.question,
                top_k=top_k,
                top_n=top_n,
                rerank_model=rerank_model,
            )

            answer = await _generate_answer(q.question, retrieved_chunks, llm_model)

            question_texts.append(q.question)
            answers.append(answer)
            contexts_list.append([c.content for c in retrieved_chunks])
            ground_truths.append(q.ground_truth_answer)

        scores = await _compute_ragas_metrics(
            questions=question_texts,
            answers=answers,
            contexts=contexts_list,
            ground_truths=ground_truths,
        )

        overall = {
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
        }
        for s in scores:
            for key in overall:
                overall[key] += s.get(key, 0.0)
        n = len(scores)
        if n > 0:
            for key in overall:
                overall[key] = round(overall[key] / n, 4)

        run.overall_scores = overall

        run_questions: list[EvaluationRunQuestion] = []
        for q, answer, contexts, s in zip(questions, answers, contexts_list, scores):
            rq = EvaluationRunQuestion(
                run_id=run.id,
                question_id=q.id,
                question_text=q.question,
                ground_truth=q.ground_truth_answer,
                answer=answer,
                contexts=contexts,
                faithfulness=s.get("faithfulness"),
                answer_relevancy=s.get("answer_relevancy"),
                context_precision=s.get("context_precision"),
                context_recall=s.get("context_recall"),
            )
            run_questions.append(rq)
            db.add(rq)

        run.status = "completed"
        run.completed_at = datetime.now(datetime.UTC)
        await db.flush()
        await db.refresh(run)

        logger.info(
            "evaluation_run_completed",
            run_id=str(run.id),
            question_count=n,
            scores=overall,
        )

    except Exception as exc:
        run.status = "failed"
        await db.flush()
        await db.refresh(run)
        logger.error("evaluation_run_failed", error=str(exc))
        raise

    return run


# --- Dataset CRUD ---

async def create_dataset(
    db: AsyncSession,
    trial_id: str,
    name: str,
    description: str | None,
    user: User,
) -> EvaluationDataset:
    dataset = EvaluationDataset(
        trial_id=uuid.UUID(trial_id),
        name=name,
        description=description,
        created_by=user.id,
    )
    db.add(dataset)
    await db.flush()
    await db.refresh(dataset)
    return dataset


async def list_datasets(db: AsyncSession, trial_id: str) -> list[EvaluationDataset]:
    result = await db.execute(
        select(EvaluationDataset)
        .where(EvaluationDataset.trial_id == uuid.UUID(trial_id))
        .order_by(EvaluationDataset.created_at.desc())
    )
    return list(result.scalars().all())


async def get_dataset(db: AsyncSession, dataset_id: str) -> EvaluationDataset | None:
    result = await db.execute(
        select(EvaluationDataset).where(EvaluationDataset.id == uuid.UUID(dataset_id))
    )
    return result.scalar_one_or_none()


async def update_dataset(
    db: AsyncSession,
    dataset_id: str,
    name: str | None,
    description: str | None,
) -> EvaluationDataset | None:
    result = await db.execute(
        select(EvaluationDataset).where(EvaluationDataset.id == uuid.UUID(dataset_id))
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        return None
    if name is not None:
        dataset.name = name
    if description is not None:
        dataset.description = description
    await db.flush()
    await db.refresh(dataset)
    return dataset


async def delete_dataset(db: AsyncSession, dataset_id: str) -> bool:
    result = await db.execute(
        select(EvaluationDataset).where(EvaluationDataset.id == uuid.UUID(dataset_id))
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        return False
    await db.delete(dataset)
    return True


# --- Question CRUD ---

async def add_question(
    db: AsyncSession,
    dataset_id: str,
    question: str,
    ground_truth_answer: str,
) -> EvaluationQuestion:
    q = EvaluationQuestion(
        dataset_id=uuid.UUID(dataset_id),
        question=question,
        ground_truth_answer=ground_truth_answer,
    )
    db.add(q)
    await db.flush()
    await db.refresh(q)
    return q


async def list_questions(db: AsyncSession, dataset_id: str) -> list[EvaluationQuestion]:
    result = await db.execute(
        select(EvaluationQuestion)
        .where(EvaluationQuestion.dataset_id == uuid.UUID(dataset_id))
        .order_by(EvaluationQuestion.created_at)
    )
    return list(result.scalars().all())


async def update_question(
    db: AsyncSession,
    question_id: str,
    question: str | None,
    ground_truth_answer: str | None,
) -> EvaluationQuestion | None:
    result = await db.execute(
        select(EvaluationQuestion).where(EvaluationQuestion.id == uuid.UUID(question_id))
    )
    q = result.scalar_one_or_none()
    if not q:
        return None
    if question is not None:
        q.question = question
    if ground_truth_answer is not None:
        q.ground_truth_answer = ground_truth_answer
    await db.flush()
    await db.refresh(q)
    return q


async def delete_question(db: AsyncSession, question_id: str) -> bool:
    result = await db.execute(
        select(EvaluationQuestion).where(EvaluationQuestion.id == uuid.UUID(question_id))
    )
    q = result.scalar_one_or_none()
    if not q:
        return False
    await db.delete(q)
    return True


async def get_datasets_map(db: AsyncSession, trial_id: str) -> dict[str, str]:
    result = await db.execute(
        select(EvaluationDataset.id, EvaluationDataset.name)
        .where(EvaluationDataset.trial_id == uuid.UUID(trial_id))
    )
    return {str(row[0]): row[1] for row in result}


async def create_run_record(
    db: AsyncSession,
    trial_id: str,
    dataset_id: str,
    user: User,
) -> EvaluationRun:
    run = EvaluationRun(
        trial_id=uuid.UUID(trial_id),
        dataset_id=uuid.UUID(dataset_id),
        status="running",
        created_by=user.id,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


async def run_evaluation_background(
    trial_id: str,
    dataset_id: str,
    run_id: str,
) -> None:
    from app.database.session import async_session_factory
    from app.vector_db.client import get_qdrant

    async with async_session_factory() as db:
        async with get_qdrant() as qdrant:
            try:
                result = await db.execute(
                    select(EvaluationRun).where(EvaluationRun.id == uuid.UUID(run_id))
                )
                run = result.scalar_one_or_none()
                if not run:
                    return

                trial_id_uuid = uuid.UUID(trial_id)
                dataset_id_uuid = uuid.UUID(dataset_id)

                questions_result = await db.execute(
                    select(EvaluationQuestion)
                    .where(EvaluationQuestion.dataset_id == dataset_id_uuid)
                    .order_by(EvaluationQuestion.created_at)
                )
                questions = questions_result.scalars().all()
                if not questions:
                    run.status = "failed"
                    await db.flush()
                    return

                settings_result = await db.execute(
                    select(TrialSettings).where(TrialSettings.trial_id == trial_id_uuid)
                )
                trial_settings = settings_result.scalar_one_or_none()
                top_k = trial_settings.top_k_retrieval if trial_settings else 10
                top_n = trial_settings.top_n_rerank if trial_settings else 5
                rerank_model = trial_settings.cohere_rerank_model if trial_settings else None
                llm_model = trial_settings.llm_model if trial_settings else None

                question_texts: list[str] = []
                answers: list[str] = []
                contexts_list: list[list[str]] = []
                ground_truths: list[str] = []

                for q in questions:
                    retrieved_chunks = await _retrieve_for_question(
                        qdrant=qdrant,
                        trial_id=trial_id,
                        question=q.question,
                        top_k=top_k,
                        top_n=top_n,
                        rerank_model=rerank_model,
                    )
                    answer = await _generate_answer(q.question, retrieved_chunks, llm_model)
                    question_texts.append(q.question)
                    answers.append(answer)
                    contexts_list.append([c.content for c in retrieved_chunks])
                    ground_truths.append(q.ground_truth_answer)

                scores = await _compute_ragas_metrics(
                    questions=question_texts,
                    answers=answers,
                    contexts=contexts_list,
                    ground_truths=ground_truths,
                )

                overall: dict[str, float] = {
                    "faithfulness": 0.0,
                    "answer_relevancy": 0.0,
                    "context_precision": 0.0,
                    "context_recall": 0.0,
                }
                for s in scores:
                    for key in overall:
                        overall[key] += s.get(key, 0.0)
                n = len(scores)
                if n > 0:
                    for key in overall:
                        overall[key] = round(overall[key] / n, 4)

                run.overall_scores = overall

                for q, answer, contexts, s in zip(questions, answers, contexts_list, scores):
                    rq = EvaluationRunQuestion(
                        run_id=run.id,
                        question_id=q.id,
                        question_text=q.question,
                        ground_truth=q.ground_truth_answer,
                        answer=answer,
                        contexts=contexts,
                        faithfulness=s.get("faithfulness"),
                        answer_relevancy=s.get("answer_relevancy"),
                        context_precision=s.get("context_precision"),
                        context_recall=s.get("context_recall"),
                    )
                    db.add(rq)

                run.status = "completed"
                run.completed_at = datetime.now(datetime.UTC)
                await db.flush()

                logger.info(
                    "evaluation_run_completed",
                    run_id=run_id,
                    question_count=n,
                    scores=overall,
                )

            except Exception as exc:
                run.status = "failed"
                await db.flush()
                logger.error("evaluation_run_failed", run_id=run_id, error=str(exc))

            await db.commit()


async def list_runs(db: AsyncSession, trial_id: str) -> list[EvaluationRun]:
    result = await db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.trial_id == uuid.UUID(trial_id))
        .order_by(EvaluationRun.created_at.desc())
    )
    return list(result.scalars().all())


async def get_run(db: AsyncSession, run_id: str) -> EvaluationRun | None:
    result = await db.execute(
        select(EvaluationRun).where(EvaluationRun.id == uuid.UUID(run_id))
    )
    return result.scalar_one_or_none()


async def get_run_questions(
    db: AsyncSession, run_id: str
) -> list[EvaluationRunQuestion]:
    result = await db.execute(
        select(EvaluationRunQuestion)
        .where(EvaluationRunQuestion.run_id == uuid.UUID(run_id))
        .order_by(EvaluationRunQuestion.created_at)
    )
    return list(result.scalars().all())


async def get_last_evaluated_at(
    db: AsyncSession, trial_id: str
) -> datetime | None:
    result = await db.execute(
        select(EvaluationRun.completed_at)
        .where(
            EvaluationRun.trial_id == uuid.UUID(trial_id),
            EvaluationRun.status == "completed",
        )
        .order_by(EvaluationRun.completed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
