# AskUserQuestion Feature Documentation

## Overview

The `AskUserQuestion` feature allows the Claude agent to pause execution and ask the user clarifying questions when a query is ambiguous or requires more context. The user's response is then used to continue processing with better-targeted results.

This feature uses the **Claude Agent SDK's built-in `AskUserQuestion` tool** (not an MCP server) and renders questions as **Adaptive Cards** in the React frontend.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ChatContainer.jsx                                                          │
│       │                                                                     │
│       ▼                                                                     │
│  useStreamingChat.js ──► chatApi.js                                         │
│       │                      │                                              │
│       │                      │ SSE Stream                                   │
│       ▼                      ▼                                              │
│  ChatMessage.jsx ◄── onAskUserQuestion callback                             │
│       │                                                                     │
│       ▼                                                                     │
│  AdaptiveCardQuestion.jsx ──► POST /v1/sessions/{id}/answer                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (FastAPI)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  server.py                                                                  │
│       │                                                                     │
│       ├── _stream_response() ──► event_queue                                │
│       │        │                     ▲                                      │
│       │        ▼                     │                                      │
│       │   run_agent() task ──────────┤                                      │
│       │        │                     │                                      │
│       │        ▼                     │                                      │
│       │   agent_sdk.py               │                                      │
│       │        │                     │                                      │
│       │        ▼                     │                                      │
│       │   can_use_tool callback      │                                      │
│       │        │                     │                                      │
│       │        ▼                     │                                      │
│       │   question_handler.py ───────┘                                      │
│       │        │                                                            │
│       │        ▼                                                            │
│       └── POST /v1/sessions/{id}/answer ──► submit_answers()                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Flow Sequence

```
1. User sends ambiguous query (e.g., "Tell me about regulations")
2. Server starts streaming response
3. Agent yields session_id early for callback registration
4. Server re-registers question callback with real session_id
5. Claude decides query is ambiguous and calls AskUserQuestion tool
6. can_use_tool callback invokes handle_ask_user_question()
7. Handler stores question and calls registered callback
8. Callback puts question into event_queue
9. Server emits SSE event: { type: "ask_user_question", ... }
10. Frontend receives event, sets pendingQuestion state
11. ChatMessage renders AdaptiveCardQuestion component
12. User selects option(s) and clicks Submit
13. Frontend POSTs to /v1/sessions/{session_id}/answer
14. submit_answers() sets asyncio.Event, unblocking handler
15. handle_ask_user_question() returns with user's answers
16. Claude continues processing with clarified intent
17. More chunks stream to frontend
18. Response completes
```

## Backend Components

### 1. question_handler.py

**Purpose**: State management for pending questions and answer synchronization.

**Key Functions**:

| Function | Description |
|----------|-------------|
| `register_question_callback(session_id, callback)` | Register a callback to be invoked when a question is ready |
| `unregister_question_callback(session_id)` | Remove the callback for a session |
| `handle_ask_user_question(input_data, session_id)` | Main handler called by can_use_tool - stores question, invokes callback, waits for answer |
| `submit_answers(session_id, answers)` | Called by /answer endpoint - stores answers and signals the waiting handler |
| `get_pending_question(session_id)` | Get pending question data (used by /pending-question endpoint) |

**State Storage**:
```python
_pending_questions: dict[str, dict] = {}      # Stores question data by session
_answer_events: dict[str, asyncio.Event] = {} # Synchronization events
_answers: dict[str, dict] = {}                # Stores user answers
_question_ready_callbacks: dict[str, Callable] = {}  # Callbacks by session
```

**Timeout**: 55 seconds (SDK has 60s limit)

### 2. agent_sdk.py

**Changes Made**:

1. Added `AskUserQuestion` to `USER_INTERACTION_TOOLS` constant
2. Added `AskUserQuestion` to `_get_allowed_tools()` return list
3. Added `can_use_tool` callback in both `query()` and `stream_query()` methods
4. Added early session_id yield in `stream_query()` for callback registration

**can_use_tool Callback**:
```python
async def _can_use_tool(tool_name: str, input_data: dict, context) -> dict:
    if tool_name == "AskUserQuestion":
        result = await handle_ask_user_question(input_data, session_id)
        return {"behavior": "allow", **result}
    return {"behavior": "allow", "updated_input": input_data}
```

**Early Session ID Yield** (critical for callback registration):
```python
# In stream_query(), right after generating session_id:
yield "", session_id, {"type": "session_init"}
```

### 3. server.py

**New Endpoints**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/sessions/{session_id}/answer` | POST | Submit user's answers to pending question |
| `/v1/sessions/{session_id}/pending-question` | GET | Check if session has pending question |

**Streaming Architecture**:

The `_stream_response()` method uses a **background task + queue** pattern:

1. Creates an `event_queue` for all events (chunks and questions)
2. Runs agent iteration in a background task (`run_agent()`)
3. Main loop reads from queue and yields SSE events
4. Question callback puts questions directly into the queue

This pattern avoids the "cancel scope" error that occurred with `asyncio.wait()`.

**Request/Response Models**:
```python
class UserAnswerRequest(BaseModel):
    answers: dict[str, str]  # Maps question text to selected option label(s)
```

## Frontend Components

### 1. chatApi.js

**New/Modified Functions**:

| Function | Description |
|----------|-------------|
| `streamChatMessage({ ..., onAskUserQuestion })` | Added callback for question events |
| `submitQuestionAnswer(sessionId, answers)` | POST answers to backend |

**SSE Event Detection**:
```javascript
if (parsed.type === 'ask_user_question') {
  onAskUserQuestion({
    sessionId: parsed.session_id,
    questions: parsed.questions
  })
  continue
}
```

### 2. useStreamingChat.js

**New State**:
```javascript
const [pendingQuestion, setPendingQuestion] = useState(null)
```

**New Functions**:
- `answerQuestion(answers)` - Submit answers and clear pending state
- `clearPendingQuestion()` - Clear without submitting (for cancel)

**Returns**:
```javascript
return {
  // ... existing returns ...
  pendingQuestion,
  answerQuestion,
  clearPendingQuestion,
}
```

### 3. ChatMessage.jsx

**New Props**:
- `pendingQuestion` - Question data to render (or null)
- `onAnswerSubmit` - Callback when user submits answer

**Rendering Logic**:
```jsx
{!isUser && isStreaming && pendingQuestion && onAnswerSubmit && (
  <AdaptiveCardQuestion
    questions={pendingQuestion.questions}
    sessionId={pendingQuestion.sessionId}
    onAnswerSubmit={onAnswerSubmit}
  />
)}
```

### 4. AdaptiveCardQuestion.jsx

**Purpose**: Renders Claude's questions as an interactive Adaptive Card.

**Props**:
| Prop | Type | Description |
|------|------|-------------|
| `questions` | Array | Array of question objects from Claude |
| `sessionId` | String | Session ID for answer submission |
| `onAnswerSubmit` | Function | Callback with formatted answers |

**Question Format** (from Claude):
```json
{
  "questions": [{
    "question": "Which regulatory area would you like me to focus on?",
    "header": "Topic",
    "options": [
      {"label": "EU AI Act", "description": "AI regulation"},
      {"label": "Data Protection", "description": "GDPR/DSGVO"}
    ],
    "multiSelect": false
  }]
}
```

**Answer Format** (to backend):
```json
{
  "answers": {
    "Which regulatory area would you like me to focus on?": "EU AI Act"
  }
}
```

**Features**:
- Renders each question with header and options
- Supports multi-select (checkbox) and single-select (radio)
- Includes custom text input option
- Styled to match the application theme

### 5. ChatContainer.jsx

**Changes**:
- Extracts `pendingQuestion` and `answerQuestion` from `useStreamingChat`
- Passes them to `ChatMessage` for the streaming message

## System Prompts

### policy_tracker_system.md

Added documentation for tool #32 `AskUserQuestion`:
- When to use (vague queries, multiple interpretations, missing context)
- Question format requirements
- Example usage with JSON

### tool_selection_strategy.md

Added clarification-first strategy:
- New rows in tool selection table for ambiguous queries
- Decision tree for when to ask vs. proceed
- Example `AskUserQuestion` calls
- "Do NOT Guess" guidance

## Configuration

### Dependencies

**Frontend**:
```bash
npm install adaptivecards
```

**Backend**: No new dependencies (uses built-in Claude SDK features)

## Error Handling

### Timeout
If user doesn't respond within 55 seconds:
- `handle_ask_user_question()` returns with empty answers
- Claude continues with alternative approach

### No Pending Question
If `/answer` is called without a pending question:
- Returns 404 error
- Frontend should handle gracefully

### Stream Errors
If agent errors during processing:
- Error event pushed to queue
- SSE error response sent to frontend
- Agent task cleaned up in finally block

## Testing

### Test Queries That Should Trigger AskUserQuestion

| Query | Expected Behavior |
|-------|-------------------|
| "Tell me about regulations" | Ask which regulatory area |
| "What's the current status?" | Ask status of what entity |
| "Give me a summary" | Ask what topic and depth |
| "What's the latest news?" | Ask which topic area |
| "Compare them" | Ask which entities to compare |
| "AI updates" | Ask: EU AI Act? German policy? Companies? |

### Verification Steps

1. Start backend: `ray serve run src.claude_agent.server:app`
2. Start frontend: `npm run dev`
3. Send ambiguous query
4. Verify:
   - SSE event emitted with `type: "ask_user_question"`
   - Adaptive Card renders in UI
   - Options are clickable
   - Submit sends POST to `/answer`
   - Response continues after submission

### Debug Logging

Key log messages to look for:
```
Question callback invoked - putting question into event queue
Re-registering question callback: pending_xxx -> claude_xxx
[Session claude_xxx] Emitting ask_user_question SSE event
[Session claude_xxx] Answers submitted, resuming agent
```

## File Summary

| File | Type | Purpose |
|------|------|---------|
| `src/claude_agent/question_handler.py` | Backend | State management for questions |
| `src/claude_agent/agent_sdk.py` | Backend | SDK integration, can_use_tool callback |
| `src/claude_agent/server.py` | Backend | Streaming, endpoints, event queue |
| `src/prompts/sdk_agents/policy_tracker_system.md` | Prompt | Tool documentation |
| `src/prompts/sdk_agents/tool_selection_strategy.md` | Prompt | When to ask for clarification |
| `ui/.../services/chatApi.js` | Frontend | SSE handling, answer submission |
| `ui/.../hooks/useStreamingChat.js` | Frontend | State management |
| `ui/.../components/chat/AdaptiveCardQuestion.jsx` | Frontend | Adaptive Card renderer |
| `ui/.../components/chat/ChatMessage.jsx` | Frontend | Question display integration |
| `ui/.../components/chat/ChatContainer.jsx` | Frontend | Props wiring |

## Limitations

1. **60-second timeout**: User must respond within ~55 seconds
2. **Question limits**: 1-4 questions per call, 2-4 options each
3. **Not in subagents**: `AskUserQuestion` doesn't work in Task-spawned agents
4. **Single session**: Each session can only have one pending question at a time

## Future Improvements

1. **Cancel button**: Allow user to skip/cancel the question
2. **Timeout indicator**: Show countdown to user
3. **Question history**: Store answered questions for context
4. **Rich options**: Support images/icons in options
5. **Validation**: Validate answers before submission
