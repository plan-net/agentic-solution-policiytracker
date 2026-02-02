"""Handler for AskUserQuestion tool in Claude Agent SDK.

This module provides state management for pending clarifying questions
from Claude. When Claude calls the AskUserQuestion tool, this handler:
1. Stores the question data and signals it's ready for the UI
2. Waits for the user to submit an answer (via the /answer endpoint)
3. Returns the answer to Claude so it can continue

The handler uses asyncio.Event for efficient waiting without blocking,
and an async queue to signal when questions are ready to be sent to the UI.
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

# Store pending questions by session
_pending_questions: dict[str, dict] = {}
_answer_events: dict[str, asyncio.Event] = {}
_answers: dict[str, dict] = {}

# Callbacks to notify when a question is ready (keyed by session_id)
# These callbacks are set by the streaming response handler
_question_ready_callbacks: dict[str, Callable[[dict], Awaitable[None]]] = {}


def register_question_callback(
    session_id: str,
    callback: Callable[[dict], Awaitable[None]]
) -> None:
    """Register a callback to be called when a question is ready.

    The streaming response handler calls this to register itself
    so it can be notified immediately when Claude asks a question.

    Args:
        session_id: The session ID
        callback: Async callback that receives the question data
    """
    _question_ready_callbacks[session_id] = callback
    logger.debug(f"[Session {session_id}] Question callback registered")


def unregister_question_callback(session_id: str) -> None:
    """Unregister the question callback for a session.

    Called when the streaming response completes.

    Args:
        session_id: The session ID
    """
    _question_ready_callbacks.pop(session_id, None)
    logger.debug(f"[Session {session_id}] Question callback unregistered")


async def handle_ask_user_question(
    input_data: dict,
    session_id: str,
) -> dict:
    """Handle AskUserQuestion tool call.

    Stores the questions, notifies the UI via callback, and waits for user response.

    Args:
        input_data: The tool input containing questions array
        session_id: The session ID for this conversation

    Returns:
        Dict with updated_input containing questions and answers
    """
    logger.info(
        f"[Session {session_id}] AskUserQuestion called with "
        f"{len(input_data.get('questions', []))} questions"
    )

    # Store pending question
    _pending_questions[session_id] = input_data
    _answer_events[session_id] = asyncio.Event()

    # Notify the streaming response handler that a question is ready
    # This allows the SSE event to be emitted immediately
    callback = _question_ready_callbacks.get(session_id)
    if callback:
        try:
            await callback(input_data)
            logger.info(f"[Session {session_id}] Question callback invoked successfully")
        except Exception as e:
            logger.error(f"[Session {session_id}] Question callback failed: {e}")
    else:
        logger.warning(
            f"[Session {session_id}] No question callback registered - "
            "UI may not receive the question"
        )

    # Wait for user to submit answers (with 55s timeout, SDK has 60s limit)
    try:
        await asyncio.wait_for(
            _answer_events[session_id].wait(),
            timeout=55.0
        )
    except asyncio.TimeoutError:
        logger.warning(
            f"[Session {session_id}] AskUserQuestion timed out waiting for user response"
        )
        # Clean up and return empty answers - Claude will try different approach
        _cleanup_session(session_id)
        return {
            "updated_input": {
                "questions": input_data.get("questions", []),
                "answers": {}
            }
        }

    # Get the answers that were submitted
    answers = _answers.get(session_id, {})
    _cleanup_session(session_id)

    logger.info(f"[Session {session_id}] User answered: {list(answers.keys())}")

    return {
        "updated_input": {
            "questions": input_data.get("questions", []),
            "answers": answers
        }
    }


def _cleanup_session(session_id: str) -> None:
    """Clean up session state after question is answered or timed out."""
    _pending_questions.pop(session_id, None)
    _answer_events.pop(session_id, None)
    _answers.pop(session_id, None)
    # Note: Don't unregister callback here - let the streaming handler do it


def submit_answers(session_id: str, answers: dict[str, str]) -> bool:
    """Submit user's answers for a pending question.

    Called by the /answer API endpoint when the user submits their response.

    Args:
        session_id: The session ID
        answers: Dict mapping question text to selected option label(s)

    Returns:
        True if answers were accepted, False if no pending question
    """
    if session_id not in _answer_events:
        logger.warning(f"[Session {session_id}] No pending question to answer")
        return False

    _answers[session_id] = answers
    _answer_events[session_id].set()
    logger.info(f"[Session {session_id}] Answers submitted, resuming agent")
    return True


def get_pending_question(session_id: str) -> Optional[dict]:
    """Get pending question for a session.

    Args:
        session_id: The session ID

    Returns:
        The pending question data if exists, None otherwise
    """
    return _pending_questions.get(session_id)


def has_pending_question(session_id: str) -> bool:
    """Check if session has a pending question.

    Args:
        session_id: The session ID

    Returns:
        True if there's a pending question for this session
    """
    return session_id in _pending_questions
