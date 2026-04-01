"""
Feishu callback and real-time notification handling.
"""
import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.redis import get_redis

router = APIRouter(prefix="/it-feedback", tags=["IT反馈"])

FEEDBACK_CHANNEL = "it_feedback_notifications"


async def event_generator() -> AsyncGenerator[str, None]:
    """SSE event generator that yields notification events."""
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(FEEDBACK_CHANNEL)

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
            if message and message["type"] == "message":
                data = message["data"]
                yield f"event: notification\ndata: {data}\n\n"
            else:
                yield "event: ping\ndata: \n\n"
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(FEEDBACK_CHANNEL)
        await pubsub.close()


@router.get("/subscribe")
async def subscribe_notifications():
    """SSE endpoint for front-end to subscribe to feedback notifications."""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/poll")
async def poll_notifications(last_id: str | None = Query(None)):
    """
    Polling endpoint for front-end to check new notifications.
    Uses Redis list to store pending notifications.
    """
    redis = await get_redis()
    key = f"{FEEDBACK_CHANNEL}:list"

    if last_id:
        cursor = 0
        items = []
        while True:
            cursor, batch = await redis.lscan(key, cursor, count=100)
            for item in batch:
                if item.startswith(f"id:{last_id}"):
                    break
                items.append(item)
            if cursor == 0 or not batch:
                break
        return {"notifications": items[-20:] if len(items) > 20 else items}

    notifications = await redis.lrange(key, -20, -1)
    return {"notifications": notifications}


async def publish_feedback_notification(
    feedback_id: int,
    action: str,
    user_id: str,
    extra_data: dict[str, Any] | None = None,
) -> None:
    """
    Publish a feedback action notification to Redis channel.
    action: 'handle' or 'resolve'
    """
    redis = await get_redis()
    notification = {
        "feedback_id": feedback_id,
        "action": action,
        "user_id": user_id,
        "extra": extra_data or {},
    }
    await redis.publish(FEEDBACK_CHANNEL, json.dumps(notification, ensure_ascii=False))
    key = f"{FEEDBACK_CHANNEL}:list"
    notification_id = f"id:{feedback_id}:{action}:{user_id}"
    await redis.lpush(key, notification_id)
    await redis.ltrim(key, 0, 999)


@router.post("/callback")
async def handle_feishu_callback(
    schema: str = Query(...),
    token: str = Query(...),
    challenge: str | None = Query(None),
):
    """
    Handle Feishu URL verification challenge.
    Feishu sends a GET request with challenge parameter for URL verification.
    """
    if challenge:
        return {"challenge": challenge}
    return {"status": "ok"}


@router.post("/callback/action")
async def handle_card_action(request: dict[str, Any]):
    """
    Handle card button click actions from Feishu.
    """
    try:
        action_value = request.get("action_value", "")
        if action_value.startswith("handle_"):
            feedback_id = int(action_value.split("_")[1])
            return {"status": "ok", "feedback_id": feedback_id, "action": "handle"}
        elif action_value.startswith("resolve_"):
            feedback_id = int(action_value.split("_")[1])
            return {"status": "ok", "feedback_id": feedback_id, "action": "resolve"}
        return {"status": "ignored"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
