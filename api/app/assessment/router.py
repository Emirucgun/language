"""Ölçüm testleri: 14 gün hatırlama (H1) ve son test (H3).

Her ikisi de ölçümdür: doğru cevap gösterilmez, tekrar motoru etkilenmez.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.assessment import retention
from app.deps import ConsentedUser, Db
from app.onboarding import fixed_tests
from app.onboarding.placement import FixedQuestionView

router = APIRouter(prefix="/api/tests", tags=["tests"])


class TestsDue(BaseModel):
    retention: bool
    post: bool


class TestAnswer(BaseModel):
    question_id: str = Field(max_length=16)
    answer: str = Field(max_length=200)  # boş: "bilmiyorum"
    duration_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class RetentionView(BaseModel):
    questions: list[retention.RetentionQuestionView]
    answered: list[str]


class RetentionResult(BaseModel):
    """Yalnızca çalışılmış öğeler: kontrol soruları öğrencinin notu değildir."""

    done: bool
    correct: int | None = None
    total: int | None = None


class PostResult(BaseModel):
    score: float
    pre_score: float


class PostView(BaseModel):
    questions: list[FixedQuestionView]
    answered: list[str]
    result: PostResult | None


@router.get("/due")
def tests_due(db: Db, user: ConsentedUser) -> TestsDue:
    return TestsDue(
        retention=retention.open_test(db, user.id) is not None,
        post=fixed_tests.post_due(db, user.id),
    )


@router.get("/retention")
def get_retention(db: Db, user: ConsentedUser) -> RetentionView:
    test = retention.open_test(db, user.id)
    if test is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Şu an bekleyen test yok.")
    return RetentionView(questions=retention.views(test), answered=sorted(test.answered))


@router.post("/retention/answer")
def post_retention_answer(body: TestAnswer, db: Db, user: ConsentedUser) -> RetentionResult:
    try:
        score = retention.answer(
            db, user.id, body.question_id, body.answer.strip(), body.duration_ms
        )
    except retention.NoOpenTest as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Şu an bekleyen test yok.") from exc
    except retention.QuestionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Soru bulunamadı.") from exc
    except retention.AlreadyAnswered as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu soru zaten cevaplandı.") from exc
    if score is None:
        return RetentionResult(done=False)
    return RetentionResult(done=True, correct=score.target_correct, total=score.target_total)


def _post_result(db: Db, user: ConsentedUser, score: float | None) -> PostResult | None:
    if score is None:
        return None
    pre = fixed_tests.placement_result(db, user.id)
    return PostResult(score=score, pre_score=pre.score if pre else 0.0)


def _require_open(db: Db, user: ConsentedUser) -> None:
    """Zamanı gelmemiş son test açılmaz: erken alınırsa artış ölçülemez."""
    if not fixed_tests.post_open(db, user.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Son testin zamanı henüz gelmedi.")


@router.get("/post")
def get_post(db: Db, user: ConsentedUser) -> PostView:
    _require_open(db, user)
    try:
        current = fixed_tests.state(db, user.id, "post")
    except fixed_tests.TestNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Son test yüklenmedi.") from exc
    return PostView(
        questions=fixed_tests.views(current.questions, user.id),
        answered=sorted(current.answered),
        result=_post_result(db, user, current.result.score if current.result else None),
    )


@router.post("/post/answer", status_code=status.HTTP_204_NO_CONTENT)
def post_post_answer(body: TestAnswer, db: Db, user: ConsentedUser) -> None:
    _require_open(db, user)
    try:
        fixed_tests.answer(
            db, user.id, "post", body.question_id, body.answer.strip(), body.duration_ms
        )
    except fixed_tests.TestNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Son test yüklenmedi.") from exc
    except fixed_tests.QuestionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Soru bulunamadı.") from exc
    except fixed_tests.AlreadyAnswered as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu soru zaten cevaplandı.") from exc


@router.post("/post/complete")
def complete_post(db: Db, user: ConsentedUser) -> PostResult:
    _require_open(db, user)
    try:
        result = fixed_tests.complete(db, user.id, "post")
    except fixed_tests.TestNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Son test yüklenmedi.") from exc
    shown = _post_result(db, user, result.score)
    assert shown is not None
    return shown
