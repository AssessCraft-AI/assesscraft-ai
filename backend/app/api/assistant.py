from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from app.models import SourceCitation, User
from app.auth import get_current_user
from app.api.courses import get_accessible_course

router = APIRouter(prefix="/courses/{course_id}", tags=["assistant"])


class AssistantQuestion(BaseModel):
    question: str


class AssistantAnswer(BaseModel):
    answer: str
    citations: List[SourceCitation]


@router.post("/assistant", response_model=AssistantAnswer)
async def ask_assistant(
    course_id: str,
    payload: AssistantQuestion,
    current_user: User = Depends(get_current_user),
):
    await get_accessible_course(course_id, current_user)

    from app.agents.assistant import answer_course_query
    answer_text, citations = await answer_course_query(course_id=course_id, question=payload.question)
    return AssistantAnswer(
        answer=answer_text,
        citations=citations,
    )
