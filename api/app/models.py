"""Tüm tabloları `Base.metadata`'ya kaydeder (Alembic ve testler bunu içe aktarır)."""

from app.auth.models import AuthSession, Invite, LoginToken, User
from app.content.models import ErrorTag, FixedTest, Item, VocabAllowlist
from app.curriculum.models import Curriculum
from app.db import Base
from app.events.models import Event
from app.feedback.models import ErrorMark, Feedback
from app.llm.models import LearnerSnapshot, LlmCall
from app.reports.models import Review, WeeklyReport
from app.scheduler.models import ItemState
from app.sessions.models import Activity, ActivityContent, StudySession

__all__ = [
    "Activity",
    "ActivityContent",
    "AuthSession",
    "Base",
    "Curriculum",
    "ErrorMark",
    "ErrorTag",
    "Event",
    "Feedback",
    "FixedTest",
    "Invite",
    "Item",
    "ItemState",
    "LearnerSnapshot",
    "LlmCall",
    "LoginToken",
    "Review",
    "StudySession",
    "User",
    "VocabAllowlist",
    "WeeklyReport",
]
