import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.models import (
    EvaluationDataset,
    EvaluationQuestion,
    EvaluationRun,
    EvaluationRunQuestion,
    User,
)
from app.evaluation.service import (
    add_question,
    create_dataset,
    create_run_record,
    delete_dataset,
    delete_question,
    get_datasets_map,
    get_last_evaluated_at,
    get_run,
    get_run_questions,
    list_datasets,
    list_questions,
    list_runs,
    update_dataset,
    update_question,
)


@pytest.fixture
def user():
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
    )


@pytest.fixture
def trial_id():
    return str(uuid.uuid4())


@pytest.fixture
def dataset_id():
    return str(uuid.uuid4())


@pytest.fixture
def run_id():
    return str(uuid.uuid4())


def make_mock_db(scalar_result=None, scalars_list=None, iterable=None):
    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = scalar_result
    if scalars_list is not None:
        execute_result.scalars.return_value.all.return_value = scalars_list
    if iterable is not None:
        execute_result.__iter__.return_value = iterable
    db.execute.return_value = execute_result
    return db


class TestDatasetCRUD:
    async def test_create_dataset(self, user, trial_id):
        db = AsyncMock()
        ds = await create_dataset(db, trial_id, "Test Dataset", "A description", user)
        assert ds.name == "Test Dataset"
        assert ds.description == "A description"
        assert ds.created_by == user.id
        db.add.assert_called_once()
        db.flush.assert_called_once()
        db.refresh.assert_called_once()

    async def test_list_datasets(self, trial_id):
        ds1 = EvaluationDataset(
            id=uuid.uuid4(), trial_id=uuid.UUID(trial_id), name="DS1", created_by=uuid.uuid4()
        )
        ds2 = EvaluationDataset(
            id=uuid.uuid4(), trial_id=uuid.UUID(trial_id), name="DS2", created_by=uuid.uuid4()
        )
        db = make_mock_db(scalars_list=[ds1, ds2])
        result = await list_datasets(db, trial_id)
        assert len(result) == 2
        assert result[0].name == "DS1"

    async def test_get_datasets_map(self, trial_id):
        rows = [(uuid.uuid4(), "DS1"), (uuid.uuid4(), "DS2")]
        db = make_mock_db(iterable=rows)
        result = await get_datasets_map(db, trial_id)
        assert len(result) == 2

    async def test_update_dataset_not_found(self):
        db = make_mock_db(scalar_result=None)
        result = await update_dataset(db, str(uuid.uuid4()), "New Name", None)
        assert result is None

    async def test_delete_dataset_found(self):
        ds = EvaluationDataset(
            id=uuid.uuid4(), trial_id=uuid.uuid4(), name="DS", created_by=uuid.uuid4()
        )
        db = make_mock_db(scalar_result=ds)
        result = await delete_dataset(db, str(ds.id))
        assert result is True
        db.delete.assert_called_once_with(ds)

    async def test_delete_dataset_not_found(self):
        db = make_mock_db(scalar_result=None)
        result = await delete_dataset(db, str(uuid.uuid4()))
        assert result is False


class TestQuestionCRUD:
    async def test_add_question(self, dataset_id):
        db = AsyncMock()
        q = await add_question(db, dataset_id, "What is X?", "X is Y")
        assert q.question == "What is X?"
        assert q.ground_truth_answer == "X is Y"
        db.add.assert_called_once()
        db.flush.assert_called_once()

    async def test_list_questions(self, dataset_id):
        q1 = EvaluationQuestion(
            id=uuid.uuid4(),
            dataset_id=uuid.UUID(dataset_id),
            question="Q1",
            ground_truth_answer="A1",
        )
        q2 = EvaluationQuestion(
            id=uuid.uuid4(),
            dataset_id=uuid.UUID(dataset_id),
            question="Q2",
            ground_truth_answer="A2",
        )
        db = make_mock_db(scalars_list=[q1, q2])
        result = await list_questions(db, dataset_id)
        assert len(result) == 2

    async def test_update_question_not_found(self):
        db = make_mock_db(scalar_result=None)
        result = await update_question(db, str(uuid.uuid4()), "Updated?", "Updated answer")
        assert result is None

    async def test_delete_question_found(self, dataset_id):
        q = EvaluationQuestion(
            id=uuid.uuid4(), dataset_id=uuid.UUID(dataset_id), question="Q", ground_truth_answer="A"
        )
        db = make_mock_db(scalar_result=q)
        result = await delete_question(db, str(q.id))
        assert result is True
        db.delete.assert_called_once_with(q)

    async def test_delete_question_not_found(self):
        db = make_mock_db(scalar_result=None)
        result = await delete_question(db, str(uuid.uuid4()))
        assert result is False


class TestRunCRUD:
    async def test_create_run_record(self, trial_id, dataset_id, user):
        db = AsyncMock()
        run = await create_run_record(db, trial_id, dataset_id, user)
        assert run.status == "running"
        assert str(run.trial_id) == trial_id
        assert str(run.dataset_id) == dataset_id
        assert run.created_by == user.id
        db.add.assert_called_once()
        db.flush.assert_called_once()

    async def test_list_runs(self, trial_id):
        run = EvaluationRun(
            id=uuid.uuid4(),
            trial_id=uuid.UUID(trial_id),
            dataset_id=uuid.uuid4(),
            status="completed",
            created_by=uuid.uuid4(),
        )
        db = make_mock_db(scalars_list=[run])
        result = await list_runs(db, trial_id)
        assert len(result) == 1
        assert result[0].status == "completed"

    async def test_get_run_found(self, run_id, trial_id):
        run = EvaluationRun(
            id=uuid.UUID(run_id),
            trial_id=uuid.UUID(trial_id),
            dataset_id=uuid.uuid4(),
            status="completed",
            created_by=uuid.uuid4(),
        )
        db = make_mock_db(scalar_result=run)
        result = await get_run(db, run_id)
        assert result is not None
        assert result.status == "completed"

    async def test_get_run_not_found(self, run_id):
        db = make_mock_db(scalar_result=None)
        result = await get_run(db, run_id)
        assert result is None

    async def test_get_run_questions(self, run_id):
        rq = EvaluationRunQuestion(
            id=uuid.uuid4(),
            run_id=uuid.UUID(run_id),
            question_id=uuid.uuid4(),
            question_text="Q",
            ground_truth="A",
            answer="Model answer",
            contexts=[],
            faithfulness=0.9,
            answer_relevancy=0.8,
            context_precision=0.85,
            context_recall=0.75,
        )
        db = make_mock_db(scalars_list=[rq])
        result = await get_run_questions(db, run_id)
        assert len(result) == 1
        assert result[0].faithfulness == 0.9

    async def test_get_last_evaluated_at(self, trial_id):
        dt = datetime.now(UTC)
        db = make_mock_db(scalar_result=dt)
        result = await get_last_evaluated_at(db, trial_id)
        assert result == dt

    async def test_get_last_evaluated_at_none(self, trial_id):
        db = make_mock_db(scalar_result=None)
        result = await get_last_evaluated_at(db, trial_id)
        assert result is None
