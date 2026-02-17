# Chat Feedback Feature Documentation

## Overview

The feedback feature allows users to provide ratings (thumbs up/thumbs down) on chat responses from the AI assistant. When a user clicks thumbs down, they can optionally provide a text comment explaining what went wrong.

## Architecture

### Data Model

Feedback is stored as a **separate property** on the `ChatSession` node in Neo4j, keeping it distinct from the actual message content.

```
ChatSession Node Properties:
├── session_id: string
├── title: string
├── created_at: datetime
├── last_updated: datetime
├── messages_json: string (JSON array of messages)
├── feedback_json: string (JSON array of feedback entries)  <-- NEW
└── ...other properties
```

#### Feedback Entry Structure

Each feedback entry in `feedback_json` contains:

```json
{
  "message_index": 1,           // Index of the message in the conversation
  "rating": "positive",         // "positive" or "negative"
  "comment": "Great response!", // Optional text feedback (mainly for negative)
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Why Separate from Messages?

Feedback is metadata *about* the message, not part of the message content itself. Storing it separately:
- Keeps message data clean and focused on conversation content
- Allows querying/aggregating feedback independently
- Makes it easier to analyze feedback patterns without parsing message arrays
- Follows separation of concerns principle

## API Endpoints

### Submit Feedback

**POST** `/api/chat/sessions/{session_id}/feedback`

Submit feedback for a specific message in a chat session.

**Request Body:**
```json
{
  "message_index": 1,
  "rating": "positive",
  "comment": "Optional comment"
}
```

**Response:**
```json
{
  "status": "success",
  "session_id": "session_abc123",
  "message_index": 1,
  "rating": "positive"
}
```

**Notes:**
- If the session doesn't exist in Neo4j yet (common for new streaming sessions), the endpoint will create a minimal session node with the feedback
- Feedback for the same `message_index` will be updated (not duplicated)

### Get Session Messages with Feedback

**GET** `/api/chat/sessions/{session_id}/messages`

Returns the chat session with all messages and associated feedback.

**Response:**
```json
{
  "session_id": "session_abc123",
  "title": "Policy Discussion",
  "created_at": "2024-01-15T10:00:00.000Z",
  "last_updated": "2024-01-15T10:30:00.000Z",
  "messages": [
    {"role": "user", "content": "What is GDPR?", "timestamp": "..."},
    {"role": "assistant", "content": "GDPR is...", "timestamp": "..."}
  ],
  "feedback": [
    {"message_index": 1, "rating": "positive", "comment": null, "timestamp": "..."}
  ],
  "entity_count": 5
}
```

## Frontend Components

### ChatMessage.jsx

The `ChatMessage` component displays individual messages and handles feedback interactions.

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `role` | string | "user" or "assistant" |
| `content` | string | Message content |
| `isStreaming` | boolean | Whether message is still streaming |
| `messageIndex` | number | Index of this message in the conversation |
| `feedback` | string \| null | Current feedback state ("positive", "negative", or null) |
| `onFeedback` | function | Callback: `(messageIndex, rating, comment) => Promise` |

**Behavior:**
- Feedback buttons only appear for assistant messages (not user messages)
- Buttons are hidden while streaming
- Thumbs up: Immediate submission, buttons disabled
- Thumbs down: Shows text input for optional comment, requires Submit click

### useStreamingChat Hook

The hook manages chat state including feedback.

**Returns:**
```javascript
{
  messages,        // Array of message objects with feedback state
  submitFeedback,  // Function to submit feedback
  // ...other properties
}
```

**Message Object Structure:**
```javascript
{
  id: "assistant_1705312200000",
  role: "assistant",
  content: "Response text...",
  feedback: "positive",      // null | "positive" | "negative"
  feedbackComment: "Great!"  // Optional comment
}
```

### feedbackApi.js

Service module for feedback API calls.

```javascript
import { submitFeedback } from '../services/feedbackApi'

// Usage
const result = await submitFeedback({
  sessionId: "session_abc123",
  messageIndex: 1,
  rating: "negative",
  comment: "Response was incorrect"
})

if (result.success) {
  console.log("Feedback submitted")
}
```

## UI States

### Visual Feedback States

| State | Thumbs Up | Thumbs Down |
|-------|-----------|-------------|
| Default | Gray outline | Gray outline |
| Hover | Green outline | Red outline |
| Positive selected | Green filled | Gray (disabled) |
| Negative selected | Gray (disabled) | Red filled |
| Comment box open | - | Red filled, input shown |

### User Flow

**Thumbs Up:**
1. User clicks thumbs up
2. Button turns green (filled)
3. Feedback submitted immediately to API
4. Both buttons become disabled

**Thumbs Down:**
1. User clicks thumbs down
2. Button turns red (filled)
3. Text input appears: "What went wrong? (optional)"
4. User types comment (optional) and clicks Submit
5. Feedback submitted to API
6. Both buttons become disabled

## Neo4j Queries

### Query Feedback for a Session

```cypher
MATCH (s:ChatSession {session_id: $session_id})
RETURN s.feedback_json AS feedback
```

### Find All Negative Feedback

```cypher
MATCH (s:ChatSession)
WHERE s.feedback_json IS NOT NULL
WITH s, apoc.convert.fromJsonList(s.feedback_json) AS feedbacks
UNWIND feedbacks AS fb
WHERE fb.rating = 'negative'
RETURN s.session_id, fb.message_index, fb.comment, fb.timestamp
ORDER BY fb.timestamp DESC
```

### Aggregate Feedback Statistics

```cypher
MATCH (s:ChatSession)
WHERE s.feedback_json IS NOT NULL
WITH apoc.convert.fromJsonList(s.feedback_json) AS feedbacks
UNWIND feedbacks AS fb
RETURN fb.rating, count(*) AS count
```

## File Structure

```
Backend:
├── src/graph_viz/
│   ├── chat_sessions.py      # Models: SubmitFeedbackRequest, FeedbackEntry
│   │                         # Service: submit_message_feedback(), get_session_feedback()
│   └── app.py                # Endpoint: POST /api/chat/sessions/{id}/feedback

├── src/chat/server/
│   └── app.py                # Message persistence after streaming

Frontend:
├── ui/policy-tracker/src/
│   ├── services/
│   │   └── feedbackApi.js    # API client for feedback
│   ├── hooks/
│   │   └── useStreamingChat.js  # State management with feedback
│   └── components/chat/
│       ├── ChatMessage.jsx   # Feedback UI (buttons, comment box)
│       └── ChatContainer.jsx # Passes feedback props to messages
```

## Error Handling

### Backend
- Invalid rating (not "positive" or "negative"): Returns 400 Bad Request
- Session not found: Creates session with feedback (graceful handling)
- Database errors: Returns 500 Internal Server Error with details

### Frontend
- No session ID: Logs error, returns false
- API failure: Logs error, returns false (UI doesn't update)
- Network errors: Caught by axios interceptor, logged

## Testing

### Manual Testing Steps

1. **Start new chat session**
   - Send a message
   - Wait for response to complete
   - Verify thumbs up/down buttons appear

2. **Test thumbs up**
   - Click thumbs up
   - Verify button turns green
   - Verify both buttons become disabled
   - Check Neo4j: `MATCH (s:ChatSession) RETURN s.feedback_json`

3. **Test thumbs down with comment**
   - Start new chat
   - Click thumbs down
   - Verify text input appears
   - Type a comment
   - Click Submit
   - Verify feedback stored with comment

4. **Test session reload**
   - Submit feedback
   - Refresh page or navigate away and back
   - Verify feedback state is restored (correct button highlighted)

### API Testing with curl

```bash
# Submit positive feedback
curl -X POST http://localhost:8001/api/chat/sessions/session_abc123/feedback \
  -H "Content-Type: application/json" \
  -d '{"message_index": 1, "rating": "positive"}'

# Submit negative feedback with comment
curl -X POST http://localhost:8001/api/chat/sessions/session_abc123/feedback \
  -H "Content-Type: application/json" \
  -d '{"message_index": 1, "rating": "negative", "comment": "Response was unclear"}'

# Get session with feedback
curl http://localhost:8001/api/chat/sessions/session_abc123/messages
```
