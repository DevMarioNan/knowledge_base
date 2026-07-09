import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth.dependencies import get_current_user
from app.config import settings
from app.database.models import Document, DocumentChunk, Trial, TrialMember, TrialSettings, User
from app.database.session import get_db
from app.vector_db.client import get_qdrant

router = APIRouter(prefix="/api/trials", tags=["trials"])


class CreateTrialRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateTrialRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class InviteMemberRequest(BaseModel):
    email: str


class SettingsResponse(BaseModel):
    llm_model: str | None
    top_k_retrieval: int
    top_n_rerank: int
    chunk_size: int
    chunk_overlap: int
    cohere_rerank_model: str | None
    evaluation_threshold: float
    status: str


class UpdateSettingsRequest(BaseModel):
    llm_model: str | None = None
    top_k_retrieval: int | None = None
    top_n_rerank: int | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    cohere_rerank_model: str | None = None
    evaluation_threshold: float | None = None
    status: str | None = None


class MemberResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    joined_at: str


class TrialResponse(BaseModel):
    id: str
    name: str
    description: str | None
    created_by: str
    member_count: int
    role: str
    created_at: str
    updated_at: str


class TrialDetailResponse(BaseModel):
    id: str
    name: str
    description: str | None
    created_by: str
    role: str
    created_at: str
    updated_at: str


async def _get_trial_or_404(trial_id: uuid.UUID, db: AsyncSession) -> Trial:
    result = await db.execute(
        select(Trial).where(Trial.id == trial_id)
    )
    trial = result.scalar_one_or_none()
    if trial is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found")
    return trial


async def _verify_membership(
    trial_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> TrialMember:
    result = await db.execute(
        select(TrialMember).where(
            TrialMember.trial_id == trial_id,
            TrialMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this trial",
        )
    return member


async def _verify_admin(trial_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> TrialMember:
    member = await _verify_membership(trial_id, user_id, db)
    if member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return member


@router.get("", response_model=list[TrialResponse])
async def list_trials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TrialResponse]:
    result = await db.execute(
        select(TrialMember)
        .options(joinedload(TrialMember.trial))
        .where(TrialMember.user_id == current_user.id)
    )
    memberships = result.scalars().all()

    if not memberships:
        return []

    trial_ids = [m.trial_id for m in memberships]
    count_result = await db.execute(
        select(TrialMember.trial_id, func.count().label("count"))
        .where(TrialMember.trial_id.in_(trial_ids))
        .group_by(TrialMember.trial_id)
    )
    counts = {row.trial_id: row.count for row in count_result}

    trials: list[TrialResponse] = []
    for membership in memberships:
        trial = membership.trial
        trials.append(
            TrialResponse(
                id=str(trial.id),
                name=trial.name,
                description=trial.description,
                created_by=str(trial.created_by),
                member_count=counts.get(trial.id, 1),
                role=membership.role,
                created_at=trial.created_at.isoformat(),
                updated_at=trial.updated_at.isoformat(),
            )
        )
    return trials


@router.post("", response_model=TrialResponse, status_code=status.HTTP_201_CREATED)
async def create_trial(
    body: CreateTrialRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrialResponse:
    trial = Trial(
        name=body.name,
        description=body.description,
        created_by=current_user.id,
    )
    db.add(trial)
    await db.flush()
    await db.refresh(trial)

    membership = TrialMember(
        trial_id=trial.id,
        user_id=current_user.id,
        role="admin",
    )
    db.add(membership)

    trial_settings = TrialSettings(trial_id=trial.id)
    db.add(trial_settings)
    await db.flush()

    return TrialResponse(
        id=str(trial.id),
        name=trial.name,
        description=trial.description,
        created_by=str(trial.created_by),
        member_count=1,
        role="admin",
        created_at=trial.created_at.isoformat(),
        updated_at=trial.updated_at.isoformat(),
    )


@router.get("/{trial_id}", response_model=TrialDetailResponse)
async def get_trial(
    trial_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrialDetailResponse:
    member = await _verify_membership(trial_id, current_user.id, db)
    trial = await _get_trial_or_404(trial_id, db)
    return TrialDetailResponse(
        id=str(trial.id),
        name=trial.name,
        description=trial.description,
        created_by=str(trial.created_by),
        role=member.role,
        created_at=trial.created_at.isoformat(),
        updated_at=trial.updated_at.isoformat(),
    )


@router.put("/{trial_id}", response_model=TrialDetailResponse)
async def update_trial(
    trial_id: uuid.UUID,
    body: UpdateTrialRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrialDetailResponse:
    member = await _verify_admin(trial_id, current_user.id, db)
    trial = await _get_trial_or_404(trial_id, db)

    if body.name is not None:
        trial.name = body.name
    if body.description is not None:
        trial.description = body.description

    await db.flush()
    await db.refresh(trial)
    return TrialDetailResponse(
        id=str(trial.id),
        name=trial.name,
        description=trial.description,
        created_by=str(trial.created_by),
        role=member.role,
        created_at=trial.created_at.isoformat(),
        updated_at=trial.updated_at.isoformat(),
    )


@router.delete("/{trial_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trial(
    trial_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    trial = await _get_trial_or_404(trial_id, db)
    if trial.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the trial creator can delete the trial",
        )

    doc_result = await db.execute(
        select(Document.id).where(Document.trial_id == trial_id)
    )
    document_ids = doc_result.scalars().all()

    if document_ids:
        chunk_result = await db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id.in_(document_ids))
        )
        chunks = chunk_result.scalars().all()

        embedding_ids = [c.embedding_id for c in chunks if c.embedding_id]
        if embedding_ids:
            async with get_qdrant() as qdrant:
                await qdrant.delete(
                    collection_name=settings.vector_collection_name,
                    points_selector=[str(eid) for eid in embedding_ids],
                )

        for chunk in chunks:
            await db.delete(chunk)

        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.trial_id == trial_id)
        )

        for doc_id in document_ids:
            file_path = Path(settings.storage_path) / f"{doc_id}.pdf"
            if file_path.exists():
                file_path.unlink()

        await db.execute(
            delete(Document).where(Document.trial_id == trial_id)
        )

    await db.execute(delete(TrialSettings).where(TrialSettings.trial_id == trial.id))
    await db.execute(delete(TrialMember).where(TrialMember.trial_id == trial.id))
    await db.delete(trial)


@router.get("/{trial_id}/members", response_model=list[MemberResponse])
async def list_members(
    trial_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MemberResponse]:
    await _verify_membership(trial_id, current_user.id, db)
    result = await db.execute(
        select(TrialMember)
        .options(joinedload(TrialMember.user))
        .where(TrialMember.trial_id == trial_id)
    )
    members = result.scalars().all()
    return [
        MemberResponse(
            id=str(m.user.id),
            email=m.user.email,
            full_name=m.user.full_name,
            role=m.role,
            joined_at=m.created_at.isoformat(),
        )
        for m in members
    ]


@router.post(
    "/{trial_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED
)
async def invite_member(
    trial_id: uuid.UUID,
    body: InviteMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    await _verify_admin(trial_id, current_user.id, db)

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found with that email",
        )

    existing = await db.execute(
        select(TrialMember).where(
            TrialMember.trial_id == trial_id,
            TrialMember.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this trial",
        )

    membership = TrialMember(trial_id=trial_id, user_id=user.id, role="member")
    db.add(membership)
    await db.flush()
    await db.refresh(membership)

    return MemberResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role="member",
        joined_at=membership.created_at.isoformat(),
    )


@router.delete("/{trial_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    trial_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _verify_admin(trial_id, current_user.id, db)

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot remove yourself. Delete the trial instead.",
        )

    result = await db.execute(
        select(TrialMember).where(
            TrialMember.trial_id == trial_id,
            TrialMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    await db.delete(member)


@router.get("/{trial_id}/settings", response_model=SettingsResponse)
async def get_trial_settings(
    trial_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    await _verify_membership(trial_id, current_user.id, db)
    result = await db.execute(
        select(TrialSettings).where(TrialSettings.trial_id == trial_id)
    )
    trial_settings = result.scalar_one_or_none()

    if trial_settings is None:
        trial_settings = TrialSettings(trial_id=trial_id)
        db.add(trial_settings)
        await db.flush()
        await db.refresh(trial_settings)

    return SettingsResponse(
        llm_model=trial_settings.llm_model,
        top_k_retrieval=trial_settings.top_k_retrieval,
        top_n_rerank=trial_settings.top_n_rerank,
        chunk_size=trial_settings.chunk_size,
        chunk_overlap=trial_settings.chunk_overlap,
        cohere_rerank_model=trial_settings.cohere_rerank_model,
        evaluation_threshold=trial_settings.evaluation_threshold,
        status=trial_settings.status,
    )


@router.put("/{trial_id}/settings", response_model=SettingsResponse)
async def update_trial_settings(
    trial_id: uuid.UUID,
    body: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    await _verify_admin(trial_id, current_user.id, db)

    result = await db.execute(
        select(TrialSettings).where(TrialSettings.trial_id == trial_id)
    )
    trial_settings = result.scalar_one_or_none()

    if trial_settings is None:
        trial_settings = TrialSettings(trial_id=trial_id)
        db.add(trial_settings)
        await db.flush()
        await db.refresh(trial_settings)

    if body.llm_model is not None:
        trial_settings.llm_model = body.llm_model
    if body.top_k_retrieval is not None:
        trial_settings.top_k_retrieval = body.top_k_retrieval
    if body.top_n_rerank is not None:
        trial_settings.top_n_rerank = body.top_n_rerank
    if body.chunk_size is not None:
        trial_settings.chunk_size = body.chunk_size
    if body.chunk_overlap is not None:
        trial_settings.chunk_overlap = body.chunk_overlap
    if body.cohere_rerank_model is not None:
        trial_settings.cohere_rerank_model = body.cohere_rerank_model
    if body.evaluation_threshold is not None:
        trial_settings.evaluation_threshold = body.evaluation_threshold
    if body.status is not None:
        trial_settings.status = body.status

    await db.flush()
    await db.refresh(trial_settings)

    return SettingsResponse(
        llm_model=trial_settings.llm_model,
        top_k_retrieval=trial_settings.top_k_retrieval,
        top_n_rerank=trial_settings.top_n_rerank,
        chunk_size=trial_settings.chunk_size,
        chunk_overlap=trial_settings.chunk_overlap,
        cohere_rerank_model=trial_settings.cohere_rerank_model,
        evaluation_threshold=trial_settings.evaluation_threshold,
        status=trial_settings.status,
    )
