from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database.models import User
from app.database.session import get_db
from app.evaluation import service
from app.vector_db.client import get_qdrant

router = APIRouter(prefix="/api/trials/{trial_id}/evaluation", tags=["evaluation"])


# -- Dataset Schemas --

class CreateDatasetRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateDatasetRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class QuestionResponse(BaseModel):
    id: str
    question: str
    ground_truth_answer: str
    created_at: str


class DatasetResponse(BaseModel):
    id: str
    trial_id: str
    name: str
    description: str | None
    created_by: str
    question_count: int
    created_at: str
    updated_at: str


class CreateQuestionRequest(BaseModel):
    question: str
    ground_truth_answer: str


class UpdateQuestionRequest(BaseModel):
    question: str | None = None
    ground_truth_answer: str | None = None


# -- Run Schemas --

class RunQuestionScoreResponse(BaseModel):
    id: str
    question_id: str
    question_text: str
    ground_truth: str
    answer: str
    contexts: list[str]
    faithfulness: float | None
    answer_relevancy: float | None
    context_precision: float | None
    context_recall: float | None


class RunResponse(BaseModel):
    id: str
    trial_id: str
    dataset_id: str
    dataset_name: str
    status: str
    overall_scores: dict | None
    created_by: str
    created_at: str
    completed_at: str | None
    question_count: int


class RunDetailResponse(RunResponse):
    question_scores: list[RunQuestionScoreResponse]


class CreateRunRequest(BaseModel):
    dataset_id: str


class LastEvaluatedResponse(BaseModel):
    last_evaluated_at: str | None


# -- Dataset Endpoints --

@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(
    trial_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DatasetResponse]:
    datasets = await service.list_datasets(db, trial_id)
    result: list[DatasetResponse] = []
    for ds in datasets:
        questions = await service.list_questions(db, str(ds.id))
        result.append(
            DatasetResponse(
                id=str(ds.id),
                trial_id=str(ds.trial_id),
                name=ds.name,
                description=ds.description,
                created_by=str(ds.created_by),
                question_count=len(questions),
                created_at=ds.created_at.isoformat(),
                updated_at=ds.updated_at.isoformat(),
            )
        )
    return result


@router.post("/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    trial_id: str,
    body: CreateDatasetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    ds = await service.create_dataset(db, trial_id, body.name, body.description, current_user)
    return DatasetResponse(
        id=str(ds.id),
        trial_id=str(ds.trial_id),
        name=ds.name,
        description=ds.description,
        created_by=str(ds.created_by),
        question_count=0,
        created_at=ds.created_at.isoformat(),
        updated_at=ds.updated_at.isoformat(),
    )


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    trial_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    ds = await service.get_dataset(db, dataset_id)
    if not ds or str(ds.trial_id) != trial_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    questions = await service.list_questions(db, str(ds.id))
    return DatasetResponse(
        id=str(ds.id),
        trial_id=str(ds.trial_id),
        name=ds.name,
        description=ds.description,
        created_by=str(ds.created_by),
        question_count=len(questions),
        created_at=ds.created_at.isoformat(),
        updated_at=ds.updated_at.isoformat(),
    )


@router.put("/datasets/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    trial_id: str,
    dataset_id: str,
    body: UpdateDatasetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    ds = await service.update_dataset(db, dataset_id, body.name, body.description)
    if not ds or str(ds.trial_id) != trial_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    questions = await service.list_questions(db, str(ds.id))
    return DatasetResponse(
        id=str(ds.id),
        trial_id=str(ds.trial_id),
        name=ds.name,
        description=ds.description,
        created_by=str(ds.created_by),
        question_count=len(questions),
        created_at=ds.created_at.isoformat(),
        updated_at=ds.updated_at.isoformat(),
    )


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    trial_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    deleted = await service.delete_dataset(db, dataset_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")


# -- Question Endpoints --

@router.get("/datasets/{dataset_id}/questions", response_model=list[QuestionResponse])
async def list_questions(
    trial_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[QuestionResponse]:
    ds = await service.get_dataset(db, dataset_id)
    if not ds or str(ds.trial_id) != trial_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    questions = await service.list_questions(db, dataset_id)
    return [
        QuestionResponse(
            id=str(q.id),
            question=q.question,
            ground_truth_answer=q.ground_truth_answer,
            created_at=q.created_at.isoformat(),
        )
        for q in questions
    ]


@router.post(
    "/datasets/{dataset_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_question(
    trial_id: str,
    dataset_id: str,
    body: CreateQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    ds = await service.get_dataset(db, dataset_id)
    if not ds or str(ds.trial_id) != trial_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    q = await service.add_question(db, dataset_id, body.question, body.ground_truth_answer)
    return QuestionResponse(
        id=str(q.id),
        question=q.question,
        ground_truth_answer=q.ground_truth_answer,
        created_at=q.created_at.isoformat(),
    )


@router.put("/datasets/{dataset_id}/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    trial_id: str,
    dataset_id: str,
    question_id: str,
    body: UpdateQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    q = await service.update_question(db, question_id, body.question, body.ground_truth_answer)
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return QuestionResponse(
        id=str(q.id),
        question=q.question,
        ground_truth_answer=q.ground_truth_answer,
        created_at=q.created_at.isoformat(),
    )


@router.delete(
    "/datasets/{dataset_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_question(
    trial_id: str,
    dataset_id: str,
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    deleted = await service.delete_question(db, question_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")


# -- Run Endpoints --

@router.get("/runs", response_model=list[RunResponse])
async def list_runs(
    trial_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RunResponse]:
    runs = await service.list_runs(db, trial_id)
    datasets_map = await service.get_datasets_map(db, trial_id)
    result: list[RunResponse] = []
    for run in runs:
        questions = await service.get_run_questions(db, str(run.id))
        result.append(
            RunResponse(
                id=str(run.id),
                trial_id=str(run.trial_id),
                dataset_id=str(run.dataset_id),
                dataset_name=datasets_map.get(str(run.dataset_id), "Unknown Dataset"),
                status=run.status,
                overall_scores=run.overall_scores,
                created_by=str(run.created_by),
                created_at=run.created_at.isoformat(),
                completed_at=run.completed_at.isoformat() if run.completed_at else None,
                question_count=len(questions),
            )
        )
    return result


@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def start_run(
    trial_id: str,
    body: CreateRunRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    run = await service.create_run_record(db, trial_id, body.dataset_id, current_user)
    background_tasks.add_task(
        service.run_evaluation_background,
        trial_id=trial_id,
        dataset_id=body.dataset_id,
        run_id=str(run.id),
    )
    datasets_map = await service.get_datasets_map(db, trial_id)
    return RunResponse(
        id=str(run.id),
        trial_id=str(run.trial_id),
        dataset_id=str(run.dataset_id),
        dataset_name=datasets_map.get(str(run.dataset_id), "Unknown Dataset"),
        status=run.status,
        overall_scores=run.overall_scores,
        created_by=str(run.created_by),
        created_at=run.created_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        question_count=0,
    )


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
async def get_run(
    trial_id: str,
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RunDetailResponse:
    run = await service.get_run(db, run_id)
    if not run or str(run.trial_id) != trial_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    questions = await service.get_run_questions(db, run_id)
    datasets_map = await service.get_datasets_map(db, trial_id)
    return RunDetailResponse(
        id=str(run.id),
        trial_id=str(run.trial_id),
        dataset_id=str(run.dataset_id),
        dataset_name=datasets_map.get(str(run.dataset_id), "Unknown Dataset"),
        status=run.status,
        overall_scores=run.overall_scores,
        created_by=str(run.created_by),
        created_at=run.created_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        question_count=len(questions),
        question_scores=[
            RunQuestionScoreResponse(
                id=str(rq.id),
                question_id=str(rq.question_id),
                question_text=rq.question_text,
                ground_truth=rq.ground_truth,
                answer=rq.answer,
                contexts=rq.contexts,
                faithfulness=rq.faithfulness,
                answer_relevancy=rq.answer_relevancy,
                context_precision=rq.context_precision,
                context_recall=rq.context_recall,
            )
            for rq in questions
        ],
    )


@router.get("/last-evaluated", response_model=LastEvaluatedResponse)
async def last_evaluated(
    trial_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LastEvaluatedResponse:
    dt = await service.get_last_evaluated_at(db, trial_id)
    return LastEvaluatedResponse(
        last_evaluated_at=dt.isoformat() if dt else None
    )
