"""
Small utilities shared by the streaming endpoint:

- sse_event(): formats a dict as a proper Server-Sent-Events wire message.
- StreamRegistry: tracks active streams by request_id so a client can
  cancel one in flight via POST /chat/cancel/{request_id}.
"""

import asyncio
import json
import time
import uuid


def sse_event(event: str, data: dict) -> str:
    """
    Format one Server-Sent Event.

    SSE wire format is:
        event: <name>\n
        data: <json>\n
        \n                (blank line terminates the event)
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


class StreamRegistry:
    """
    Tracks in-flight streams so they can be cancelled and so we can cap
    total concurrency. One asyncio.Event per active request_id -- setting
    the event is how /chat/cancel signals the generator to stop.
    """

    def __init__(self, max_concurrent: int):
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def new_request_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def register(self, request_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._cancel_events[request_id] = event
        return event

    def cancel(self, request_id: str) -> bool:
        event = self._cancel_events.get(request_id)
        if event is None:
            return False
        event.set()
        return True

    def unregister(self, request_id: str) -> None:
        self._cancel_events.pop(request_id, None)

    def is_active(self, request_id: str) -> bool:
        return request_id in self._cancel_events

    @property
    def active_count(self) -> int:
        return len(self._cancel_events)

    @property
    def semaphore(self) -> asyncio.Semaphore:
        return self._semaphore


def now_ms() -> int:
    return int(time.time() * 1000)
