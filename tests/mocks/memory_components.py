"""Mock memory components for testing multi-agent system."""

from datetime import datetime
from typing import Any, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class MockInMemoryStore:
    """Mock implementation of LangGraph's InMemoryStore for testing."""

    def __init__(self):
        self._store: dict[str, Any] = {}
        self.call_history: list[dict[str, Any]] = []

    async def aget(self, key: str) -> Any:
        """Get value from store."""
        self._log_call("aget", {"key": key})
        return self._store.get(key)

    async def aput(self, key: str, value: Any) -> None:
        """Put value in store."""
        self._log_call("aput", {"key": key, "value_type": type(value).__name__})
        self._store[key] = value

    async def adelete(self, key: str) -> None:
        """Delete key from store."""
        self._log_call("adelete", {"key": key})
        if key in self._store:
            del self._store[key]

    def _log_call(self, method: str, params: dict[str, Any]) -> None:
        """Log method call for testing verification."""
        self.call_history.append(
            {"method": method, "params": params, "timestamp": datetime.now().isoformat()}
        )

    def get_store_contents(self) -> dict[str, Any]:
        """Get all store contents for testing."""
        return self._store.copy()

    def clear_store(self) -> None:
        """Clear all store contents."""
        self._store.clear()

    def reset_call_history(self) -> None:
        """Reset call history for testing."""
        self.call_history.clear()


class MockInMemorySaver:
    """Mock implementation of LangGraph's InMemorySaver for testing."""

    def __init__(self):
        self._checkpoints: dict[str, dict[str, Any]] = {}
        self.call_history: list[dict[str, Any]] = []

    async def aget(self, config: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Get checkpoint by configuration."""
        thread_id = config.get("configurable", {}).get("thread_id")
        self._log_call("aget", {"thread_id": thread_id})

        if thread_id and thread_id in self._checkpoints:
            return self._checkpoints[thread_id]
        return None

    async def aput(self, config: dict[str, Any], checkpoint: dict[str, Any]) -> None:
        """Save checkpoint."""
        thread_id = config.get("configurable", {}).get("thread_id")
        self._log_call("aput", {"thread_id": thread_id, "checkpoint_keys": list(checkpoint.keys())})

        if thread_id:
            self._checkpoints[thread_id] = checkpoint

    def _log_call(self, method: str, params: dict[str, Any]) -> None:
        """Log method call for testing verification."""
        self.call_history.append(
            {"method": method, "params": params, "timestamp": datetime.now().isoformat()}
        )

    def get_checkpoint(self, thread_id: str) -> Optional[dict[str, Any]]:
        """Get checkpoint for testing."""
        return self._checkpoints.get(thread_id)

    def clear_checkpoints(self) -> None:
        """Clear all checkpoints."""
        self._checkpoints.clear()

    def reset_call_history(self) -> None:
        """Reset call history for testing."""
        self.call_history.clear()


class MockMemoryManager:
    """Mock implementation of MemoryManager for testing."""

    def __init__(self):
        self.store = MockInMemoryStore()
        self.checkpointer = MockInMemorySaver()
        self.max_conversation_tokens = 4000
        self.call_history: list[dict[str, Any]] = []

        # Pre-populate with realistic test data
        self._setup_test_data()

    def _setup_test_data(self):
        """Setup realistic test data."""
        # User preferences
        self.store._store["user_prefs_test_user"] = {
            "detail_level": "high",
            "response_format": "structured",
            "citation_style": "academic",
            "preferred_jurisdictions": ["EU", "US"],
            "notification_preferences": {"enforcement_actions": True, "policy_updates": True},
        }

        # Learned patterns
        self.store._store["patterns_query_patterns"] = [
            {
                "pattern_type": "intent_classification",
                "pattern": "enforcement_tracking",
                "confidence": 0.85,
                "examples": ["fines", "enforcement", "penalties"],
                "learned_date": "2024-11-15",
            },
            {
                "pattern_type": "entity_preference",
                "pattern": "focus_on_big_tech",
                "confidence": 0.92,
                "entities": ["Meta", "Google", "Amazon", "Apple"],
                "learned_date": "2024-11-10",
            },
        ]

        # Tool performance history
        self.store._store["tool_perf_search"] = {
            "total_executions": 150,
            "success_rate": 0.94,
            "avg_execution_time": 0.12,
            "common_errors": ["timeout", "rate_limit"],
        }

        self.store._store["tool_perf_entity_lookup"] = {
            "total_executions": 89,
            "success_rate": 0.98,
            "avg_execution_time": 0.05,
            "common_errors": ["entity_not_found"],
        }

        # Query insights
        self.store._store["query_insights_test_user"] = {
            "common_intents": [
                ("information_seeking", 45),
                ("compliance_research", 32),
                ("enforcement_tracking", 23),
            ],
            "frequent_entities": [
                ("GDPR", 28),
                ("Meta", 22),
                ("EU AI Act", 18),
                ("Digital Services Act", 15),
            ],
            "preferred_detail_level": "high",
            "typical_query_complexity": "medium",
            "last_satisfaction": 4.2,
        }

        # Sample conversation history
        self.checkpointer._checkpoints["test_thread"] = {
            "messages": [
                HumanMessage(content="What are the latest GDPR enforcement actions?"),
                AIMessage(content="Recent GDPR enforcement includes..."),
                HumanMessage(content="How does this affect Meta specifically?"),
                AIMessage(content="Meta faces several compliance challenges..."),
            ],
            "session_metadata": {
                "user_id": "test_user",
                "session_start": "2024-11-20T10:00:00Z",
                "query_count": 2,
            },
        }

    async def get_conversation_context(
        self, thread_id: str, max_tokens: int = None
    ) -> list[BaseMessage]:
        """Mock conversation context retrieval."""
        self._log_call(
            "get_conversation_context", {"thread_id": thread_id, "max_tokens": max_tokens}
        )

        checkpoint = await self.checkpointer.aget({"configurable": {"thread_id": thread_id}})
        if checkpoint and "messages" in checkpoint:
            messages = checkpoint["messages"]
            # Simple token limiting (mock implementation)
            if max_tokens and len(messages) > 5:
                return messages[-5:]  # Return last 5 messages
            return messages
        return []

    async def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        """Mock user preferences retrieval."""
        self._log_call("get_user_preferences", {"user_id": user_id})
        return await self.store.aget(f"user_prefs_{user_id}") or {}

    async def update_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """Mock user preference update."""
        self._log_call("update_user_preference", {"user_id": user_id, "key": key})

        prefs = await self.get_user_preferences(user_id)
        prefs[key] = value
        await self.store.aput(f"user_prefs_{user_id}", prefs)

    async def get_learned_patterns(self, pattern_type: str) -> list[dict[str, Any]]:
        """Mock learned patterns retrieval."""
        self._log_call("get_learned_patterns", {"pattern_type": pattern_type})
        return await self.store.aget(f"patterns_{pattern_type}") or []

    async def save_learned_pattern(self, pattern_type: str, pattern_data: dict[str, Any]) -> None:
        """Mock pattern learning."""
        self._log_call("save_learned_pattern", {"pattern_type": pattern_type})

        patterns = await self.get_learned_patterns(pattern_type)
        patterns.append(pattern_data)

        # Keep only last 100 patterns
        if len(patterns) > 100:
            patterns = patterns[-100:]

        await self.store.aput(f"patterns_{pattern_type}", patterns)

    async def get_tool_performance_history(self, tool_name: str) -> dict[str, Any]:
        """Mock tool performance history."""
        self._log_call("get_tool_performance_history", {"tool_name": tool_name})

        default_perf = {
            "total_executions": 0,
            "success_rate": 0.0,
            "avg_execution_time": 0.0,
            "common_errors": [],
        }

        return await self.store.aget(f"tool_perf_{tool_name}") or default_perf

    async def update_tool_performance(
        self, tool_name: str, success: bool, execution_time: float, error: Optional[str] = None
    ) -> None:
        """Mock tool performance update."""
        self._log_call(
            "update_tool_performance",
            {
                "tool_name": tool_name,
                "success": success,
                "execution_time": execution_time,
                "error": error,
            },
        )

        history = await self.get_tool_performance_history(tool_name)

        # Update metrics (simplified)
        history["total_executions"] += 1
        if success:
            current_successes = history["success_rate"] * (history["total_executions"] - 1)
            history["success_rate"] = (current_successes + 1) / history["total_executions"]
        else:
            current_successes = history["success_rate"] * (history["total_executions"] - 1)
            history["success_rate"] = current_successes / history["total_executions"]

        # Update execution time
        current_total_time = history["avg_execution_time"] * (history["total_executions"] - 1)
        history["avg_execution_time"] = (current_total_time + execution_time) / history[
            "total_executions"
        ]

        # Track errors
        if error and error not in history["common_errors"]:
            history["common_errors"].append(error)
            if len(history["common_errors"]) > 10:
                history["common_errors"] = history["common_errors"][-10:]

        await self.store.aput(f"tool_perf_{tool_name}", history)

    async def get_query_insights(self, user_id: str) -> dict[str, Any]:
        """Mock query insights retrieval."""
        self._log_call("get_query_insights", {"user_id": user_id})

        default_insights = {
            "common_intents": [],
            "frequent_entities": [],
            "preferred_detail_level": "medium",
            "typical_query_complexity": "medium",
        }

        return await self.store.aget(f"query_insights_{user_id}") or default_insights

    async def learn_from_query(
        self,
        user_id: str,
        query: str,
        intent: str,
        entities: list[str],
        satisfaction_rating: Optional[float] = None,
    ) -> None:
        """Mock query learning."""
        self._log_call(
            "learn_from_query",
            {
                "user_id": user_id,
                "intent": intent,
                "entity_count": len(entities),
                "satisfaction_rating": satisfaction_rating,
            },
        )

        insights = await self.get_query_insights(user_id)

        # Update common intents (simplified)
        intent_counts = dict(insights.get("common_intents", []))
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
        insights["common_intents"] = list(intent_counts.items())

        # Update frequent entities
        entity_counts = dict(insights.get("frequent_entities", []))
        for entity in entities:
            entity_counts[entity] = entity_counts.get(entity, 0) + 1
        insights["frequent_entities"] = list(entity_counts.items())

        if satisfaction_rating is not None:
            insights["last_satisfaction"] = satisfaction_rating

        await self.store.aput(f"query_insights_{user_id}", insights)

    async def clear_user_data(self, user_id: str) -> None:
        """Mock user data clearing for GDPR compliance."""
        self._log_call("clear_user_data", {"user_id": user_id})

        keys_to_clear = [f"user_prefs_{user_id}", f"query_insights_{user_id}"]

        for key in keys_to_clear:
            await self.store.adelete(key)

    def _log_call(self, method: str, params: dict[str, Any]) -> None:
        """Log method call for testing verification."""
        self.call_history.append(
            {"method": method, "params": params, "timestamp": datetime.now().isoformat()}
        )

    # Test utilities

    def reset_call_history(self) -> None:
        """Reset call history for testing."""
        self.call_history.clear()
        self.store.reset_call_history()
        self.checkpointer.reset_call_history()

    def get_call_count(self, method_name: Optional[str] = None) -> int:
        """Get number of calls made."""
        if method_name:
            return len([call for call in self.call_history if call["method"] == method_name])
        return len(self.call_history)

    def add_test_user_data(
        self, user_id: str, preferences: dict[str, Any] = None, insights: dict[str, Any] = None
    ) -> None:
        """Add test user data."""
        if preferences:
            self.store._store[f"user_prefs_{user_id}"] = preferences

        if insights:
            self.store._store[f"query_insights_{user_id}"] = insights

    def add_test_conversation(self, thread_id: str, messages: list[BaseMessage]) -> None:
        """Add test conversation history."""
        self.checkpointer._checkpoints[thread_id] = {
            "messages": messages,
            "session_metadata": {
                "user_id": "test_user",
                "session_start": datetime.now().isoformat(),
                "query_count": len([m for m in messages if isinstance(m, HumanMessage)]),
            },
        }


class MockStreamingManager:
    """Mock implementation of StreamingManager for testing."""

    def __init__(self):
        self.stream_writer = None
        self.emitted_events: list[dict[str, Any]] = []

    def set_stream_writer(self, writer):
        """Set the stream writer."""
        self.stream_writer = writer

    async def emit_thinking(
        self, agent_name: str, thought: str, metadata: dict[str, Any] = None
    ) -> None:
        """Mock thinking emission."""
        event = {
            "type": "thinking",
            "agent": agent_name,
            "content": thought,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.emitted_events.append(event)

        if self.stream_writer:
            await self.stream_writer(
                {"thinking": thought, "agent": agent_name, "metadata": metadata or {}}
            )

    async def emit_progress(
        self, agent_name: str, progress: str, percentage: Optional[float] = None
    ) -> None:
        """Mock progress emission."""
        event = {
            "type": "progress",
            "agent": agent_name,
            "content": progress,
            "percentage": percentage,
            "timestamp": datetime.now().isoformat(),
        }
        self.emitted_events.append(event)

        if self.stream_writer:
            await self.stream_writer(
                {
                    "progress": progress,
                    "agent": agent_name,
                    "percentage": percentage,
                    "event_type": "progress",
                }
            )

    async def emit_agent_transition(self, from_agent: str, to_agent: str, reason: str = "") -> None:
        """Mock agent transition emission."""
        event = {
            "type": "agent_transition",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
        self.emitted_events.append(event)

        if self.stream_writer:
            await self.stream_writer(
                {
                    "transition": f"Transitioning from {from_agent} to {to_agent}",
                    "from_agent": from_agent,
                    "to_agent": to_agent,
                    "reason": reason,
                    "event_type": "agent_transition",
                }
            )

    async def emit_tool_execution(
        self, agent_name: str, tool_name: str, status: str, result_preview: str = ""
    ) -> None:
        """Mock tool execution emission."""
        event = {
            "type": "tool_execution",
            "agent": agent_name,
            "tool_name": tool_name,
            "status": status,
            "result_preview": result_preview,
            "timestamp": datetime.now().isoformat(),
        }
        self.emitted_events.append(event)

        if self.stream_writer:
            await self.stream_writer(
                {
                    "tool_execution": f"Executing {tool_name}: {status}",
                    "agent": agent_name,
                    "tool_name": tool_name,
                    "status": status,
                    "result_preview": result_preview,
                    "event_type": "tool_execution",
                }
            )

    async def emit_error(
        self, agent_name: str, error_message: str, error_type: str = "error"
    ) -> None:
        """Mock error emission."""
        event = {
            "type": "error",
            "agent": agent_name,
            "error_message": error_message,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat(),
        }
        self.emitted_events.append(event)

        if self.stream_writer:
            await self.stream_writer(
                {
                    "error": error_message,
                    "agent": agent_name,
                    "error_type": error_type,
                    "event_type": "error",
                }
            )

    # Test utilities

    def get_emitted_events(self, event_type: Optional[str] = None) -> list[dict[str, Any]]:
        """Get emitted events for testing."""
        if event_type:
            return [e for e in self.emitted_events if e["type"] == event_type]
        return self.emitted_events.copy()

    def clear_events(self) -> None:
        """Clear all emitted events."""
        self.emitted_events.clear()

    def get_event_count(self, event_type: Optional[str] = None) -> int:
        """Get count of emitted events."""
        if event_type:
            return len([e for e in self.emitted_events if e["type"] == event_type])
        return len(self.emitted_events)


# Global instances for testing
mock_memory_manager = MockMemoryManager()
mock_streaming_manager = MockStreamingManager()
