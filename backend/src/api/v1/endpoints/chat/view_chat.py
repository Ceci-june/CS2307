from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from src.services.auth.dependencies import get_current_user
from src.services.chat import repository
from src.search.schemas import SearchRequest
from src.search.service import hybrid_search_service


router = APIRouter()

# Cap how many prior turns are replayed to the LLM to bound token usage.
_HISTORY_TURNS = 10


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2000)
    conversation_id: Optional[int] = None
    top_k: int = Field(default=3, ge=1, le=20)
    filters: Dict[str, Any] = Field(default_factory=dict)


def _history_from_messages(messages: list[dict]) -> list[dict]:
    """Turn stored rows into ``{role, content}`` turns for the LLM (text only)."""
    history = []
    for row in messages:
        content = (row.get("content") or "").strip()
        if not content:
            continue
        role = "assistant" if row.get("role") == "assistant" else "user"
        history.append({"role": role, "content": content})
    return history[-_HISTORY_TURNS:]


@router.post("", summary="Send a chat message (multi-turn, persisted)")
async def chat(data: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]

    if data.conversation_id is not None:
        conversation = await run_in_threadpool(
            repository.get_conversation, data.conversation_id, user_id
        )
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc trò chuyện")
        prior = await run_in_threadpool(repository.get_messages, data.conversation_id)
        history = _history_from_messages(prior)
        conversation_id = data.conversation_id
    else:
        title = data.message[:80]
        conversation = await run_in_threadpool(repository.create_conversation, user_id, title)
        conversation_id = conversation["id"]
        history = []

    await run_in_threadpool(repository.add_message, conversation_id, "user", data.message)

    request = SearchRequest(query=data.message, top_k=data.top_k, filters=data.filters)
    try:
        result = await hybrid_search_service.search(
            request, history=history, user_id=user_id
        )
    except Exception as exc:  # noqa: BLE001 - log internals, return a generic message
        logger.exception("Chat search failed for conversation {}", conversation_id)
        raise HTTPException(
            status_code=500, detail="Đã xảy ra lỗi khi tìm kiếm. Vui lòng thử lại sau."
        ) from exc

    assistant_text = result.get("assistant_answer") or (
        "Dựa trên yêu cầu của bạn, tôi tìm thấy các bất động sản sau:"
        if result.get("results")
        else "Xin lỗi, tôi không tìm thấy bất động sản nào phù hợp với yêu cầu của bạn."
    )
    await run_in_threadpool(
        repository.add_message,
        conversation_id,
        "assistant",
        assistant_text,
        result.get("results"),
        result.get("parsed_query"),
    )
    # Title is set once at creation; only bump updated_at here (COALESCE kept the
    # original title anyway, so passing it every turn was a no-op).
    await run_in_threadpool(repository.touch_conversation, conversation_id)

    payload = {"conversation_id": conversation_id, **result}
    return {"data": payload, "errors": [], "status": "success"}


@router.get("/conversations", summary="List the current user's conversations")
async def list_conversations(current_user: dict = Depends(get_current_user)):
    rows = await run_in_threadpool(repository.list_conversations, current_user["id"])
    return {"data": rows, "errors": [], "status": "success"}


@router.get("/conversations/{conversation_id}", summary="Full message history of a conversation")
async def get_conversation(conversation_id: int, current_user: dict = Depends(get_current_user)):
    conversation = await run_in_threadpool(
        repository.get_conversation, conversation_id, current_user["id"]
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc trò chuyện")
    messages = await run_in_threadpool(repository.get_messages, conversation_id)
    return {
        "data": {"conversation": conversation, "messages": messages},
        "errors": [],
        "status": "success",
    }
