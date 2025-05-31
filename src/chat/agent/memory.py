"""Memory management interfaces for multi-agent system."""

import logging
from typing import Any, Optional

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

logger = logging.getLogger(__name__)


class MemoryManager:
    """Centralized memory management for multi-agent system."""

    def __init__(self):
        # Short-term memory (conversation history)
        self.checkpointer = InMemorySaver()

        # Long-term memory (user preferences, patterns)
        self.store = InMemoryStore()

        # Configuration
        self.max_conversation_tokens = 4000
        self.summary_model = None  # Will be set later

    async def get_conversation_context(
        self, thread_id: str, max_tokens: int = None
    ) -> list[BaseMessage]:
        """
        Get conversation context with automatic trimming.

        Args:
            thread_id: Conversation thread identifier
            max_tokens: Maximum tokens to include (default: self.max_conversation_tokens)

        Returns:
            List of messages within token limit
        """
        max_tokens = max_tokens or self.max_conversation_tokens

        try:
            # Get full conversation history from checkpointer
            checkpoint = await self.checkpointer.aget({"configurable": {"thread_id": thread_id}})

            if not checkpoint or "messages" not in checkpoint:
                return []

            messages = checkpoint["messages"]

            # Simple message trimming - keep last N messages if too many
            if len(messages) > 20:  # Simple heuristic instead of token counting
                trimmed_messages = messages[-20:]
            else:
                trimmed_messages = messages

            return trimmed_messages

        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return []

    async def save_conversation_message(self, thread_id: str, message: BaseMessage) -> None:
        """Save a new message to conversation history."""
        try:
            # This integrates with LangGraph's checkpointing system
            # Implementation will depend on how we set up the graph
            pass
        except Exception as e:
            logger.error(f"Error saving conversation message: {e}")

    async def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        """Get user preferences from long-term memory."""
        try:
            item = await self.store.aget(("user_prefs",), user_id)
            return item.value if item else {}
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {}

    async def update_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """Update a specific user preference."""
        try:
            prefs = await self.get_user_preferences(user_id)
            prefs[key] = value
            await self.store.aput(("user_prefs",), user_id, prefs)
        except Exception as e:
            logger.error(f"Error updating user preference: {e}")

    async def get_learned_patterns(self, pattern_type: str) -> list[dict[str, Any]]:
        """Get learned patterns for optimization."""
        try:
            item = await self.store.aget(("patterns",), pattern_type)
            return item.value if item else []
        except Exception as e:
            logger.error(f"Error getting learned patterns: {e}")
            return []

    async def save_learned_pattern(self, pattern_type: str, pattern_data: dict[str, Any]) -> None:
        """Save a learned pattern for future optimization."""
        try:
            patterns = await self.get_learned_patterns(pattern_type)
            patterns.append(pattern_data)

            # Keep only last 100 patterns per type
            if len(patterns) > 100:
                patterns = patterns[-100:]

            await self.store.aput(("patterns",), pattern_type, patterns)
        except Exception as e:
            logger.error(f"Error saving learned pattern: {e}")

    async def analyze_user_conversation_patterns(self, user_id: str) -> dict[str, Any]:
        """Analyze user conversation patterns for personalization."""
        try:
            default_patterns = {
                "common_intents": {},
                "preferred_detail_level": "medium",
                "response_format_preference": "structured",
                "question_complexity_distribution": {"simple": 0.4, "medium": 0.5, "complex": 0.1},
                "topic_interests": {},
                "interaction_time_patterns": {},
                "feedback_patterns": {"positive": 0, "negative": 0},
            }
            item = await self.store.aget(("user_conversation_patterns",), user_id)
            return item.value if item else default_patterns
        except Exception as e:
            logger.error(f"Error analyzing conversation patterns: {e}")
            return {
                "common_intents": {},
                "preferred_detail_level": "medium",
                "response_format_preference": "structured",
                "question_complexity_distribution": {"simple": 0.4, "medium": 0.5, "complex": 0.1},
                "topic_interests": {},
                "interaction_time_patterns": {},
                "feedback_patterns": {"positive": 0, "negative": 0},
            }

    async def update_user_conversation_patterns(
        self,
        user_id: str,
        query: str,
        intent: str,
        complexity: str,
        satisfaction_rating: float,
        response_time: float,
    ) -> None:
        """Update user conversation patterns based on interaction."""
        try:
            patterns = await self.analyze_user_conversation_patterns(user_id)

            # Update intent frequency
            intents = patterns["common_intents"]
            intents[intent] = intents.get(intent, 0) + 1

            # Update complexity distribution
            complexity_dist = patterns["question_complexity_distribution"]
            total_questions = sum(complexity_dist.values()) + 1

            for level in complexity_dist:
                if level == complexity:
                    complexity_dist[level] = (
                        complexity_dist[level] * (total_questions - 1) + 1
                    ) / total_questions
                else:
                    complexity_dist[level] = (
                        complexity_dist[level] * (total_questions - 1) / total_questions
                    )

            # Update satisfaction feedback
            if satisfaction_rating >= 3.5:
                patterns["feedback_patterns"]["positive"] += 1
            else:
                patterns["feedback_patterns"]["negative"] += 1

            # Analyze response time patterns
            time_patterns = patterns["interaction_time_patterns"]
            if satisfaction_rating >= 4.0:
                time_patterns["preferred_response_time"] = time_patterns.get(
                    "preferred_response_time", response_time
                )
                # Moving average
                time_patterns["preferred_response_time"] = (
                    time_patterns["preferred_response_time"] * 0.8 + response_time * 0.2
                )

            await self.store.aput(("user_conversation_patterns",), user_id, patterns)

        except Exception as e:
            logger.error(f"Error updating conversation patterns: {e}")

    async def get_personalization_recommendations(self, user_id: str) -> dict[str, Any]:
        """Get personalization recommendations based on user patterns."""
        try:
            patterns = await self.analyze_user_conversation_patterns(user_id)

            # Determine preferred thinking speed
            feedback_ratio = patterns["feedback_patterns"]["positive"] / max(
                1,
                patterns["feedback_patterns"]["positive"]
                + patterns["feedback_patterns"]["negative"],
            )

            thinking_speed = "normal"
            if feedback_ratio > 0.8:
                thinking_speed = "fast"  # User is satisfied, can go faster
            elif feedback_ratio < 0.6:
                thinking_speed = "detailed"  # User needs more explanation

            # Determine preferred response format
            most_common_intent = max(
                patterns["common_intents"].items(),
                key=lambda x: x[1],
                default=("information_seeking", 0),
            )[0]

            response_format = "structured"
            if most_common_intent in ["troubleshooting", "how_to"]:
                response_format = "step_by_step"
            elif most_common_intent in ["research", "analysis"]:
                response_format = "comprehensive"

            return {
                "thinking_speed": thinking_speed,
                "response_format": response_format,
                "detail_level": patterns.get("preferred_detail_level", "medium"),
                "complexity_comfort": max(
                    patterns["question_complexity_distribution"].items(), key=lambda x: x[1]
                )[0]
                if patterns["question_complexity_distribution"]
                else "medium",
                "satisfaction_trend": "improving" if feedback_ratio > 0.7 else "needs_attention",
            }

        except Exception as e:
            logger.error(f"Error getting personalization recommendations: {e}")
            return {"thinking_speed": "normal", "response_format": "structured"}

    async def get_tool_performance_history(self, tool_name: str) -> dict[str, Any]:
        """Get historical performance data for a tool."""
        try:
            default_history = {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "common_errors": [],
            }
            item = await self.store.aget(("tool_perf",), tool_name)
            return item.value if item else default_history
        except Exception as e:
            logger.error(f"Error getting tool performance history: {e}")
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "common_errors": [],
            }

    async def update_tool_performance(
        self, tool_name: str, success: bool, execution_time: float, error: Optional[str] = None
    ) -> None:
        """Update tool performance metrics."""
        try:
            history = await self.get_tool_performance_history(tool_name)

            # Update metrics
            history["total_executions"] += 1

            # Update success rate
            if success:
                current_successes = history["success_rate"] * (history["total_executions"] - 1)
                history["success_rate"] = (current_successes + 1) / history["total_executions"]
            else:
                current_successes = history["success_rate"] * (history["total_executions"] - 1)
                history["success_rate"] = current_successes / history["total_executions"]

            # Update average execution time
            current_total_time = history["avg_execution_time"] * (history["total_executions"] - 1)
            history["avg_execution_time"] = (current_total_time + execution_time) / history[
                "total_executions"
            ]

            # Track errors
            if error and error not in history["common_errors"]:
                history["common_errors"].append(error)
                # Keep only last 10 unique errors
                if len(history["common_errors"]) > 10:
                    history["common_errors"] = history["common_errors"][-10:]

            await self.store.aput(("tool_perf",), tool_name, history)

        except Exception as e:
            logger.error(f"Error updating tool performance: {e}")

    async def get_query_insights(self, user_id: str) -> dict[str, Any]:
        """Get insights about user's query patterns."""
        try:
            default_insights = {
                "common_intents": [],
                "frequent_entities": [],
                "preferred_detail_level": "medium",
                "typical_query_complexity": "medium",
            }
            item = await self.store.aget(("query_insights",), user_id)
            return item.value if item else default_insights
        except Exception as e:
            logger.error(f"Error getting query insights: {e}")
            return {
                "common_intents": [],
                "frequent_entities": [],
                "preferred_detail_level": "medium",
                "typical_query_complexity": "medium",
            }

    async def learn_from_query(
        self,
        user_id: str,
        query: str,
        intent: str,
        entities: list[str],
        satisfaction_rating: Optional[float] = None,
    ) -> None:
        """Learn from user query patterns."""
        try:
            insights = await self.get_query_insights(user_id)

            # Update common intents
            intent_counts = dict(insights.get("common_intents", []))
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            insights["common_intents"] = list(intent_counts.items())

            # Update frequent entities
            entity_counts = dict(insights.get("frequent_entities", []))
            for entity in entities:
                entity_counts[entity] = entity_counts.get(entity, 0) + 1
            insights["frequent_entities"] = list(entity_counts.items())

            # Learn satisfaction if provided
            if satisfaction_rating is not None:
                insights["last_satisfaction"] = satisfaction_rating

            await self.store.aput(("query_insights",), user_id, insights)

        except Exception as e:
            logger.error(f"Error learning from query: {e}")

    async def clear_user_data(self, user_id: str) -> None:
        """Clear all user data (GDPR compliance)."""
        try:
            keys_to_clear = [
                ("user_prefs", user_id),
                ("query_insights", user_id),
                ("user_conversation_patterns", user_id),
            ]

            for namespace, key in keys_to_clear:
                try:
                    await self.store.adelete((namespace,), key)
                except:
                    pass  # Key might not exist

        except Exception as e:
            logger.error(f"Error clearing user data: {e}")


class ConversationSummarizer:
    """Handles conversation summarization for long contexts."""

    def __init__(self, summarization_model=None):
        self.model = summarization_model
        self.max_tokens_before_summary = 3000
        self.max_summary_tokens = 500

    async def should_summarize(self, messages: list[BaseMessage]) -> bool:
        """Check if conversation should be summarized."""
        # Simple heuristic: estimate 50 tokens per message
        estimated_tokens = len(messages) * 50
        return estimated_tokens > self.max_tokens_before_summary

    async def summarize_conversation(
        self, messages: list[BaseMessage], preserve_recent: int = 5
    ) -> list[BaseMessage]:
        """
        Summarize conversation while preserving recent messages.

        Args:
            messages: Full conversation history
            preserve_recent: Number of recent messages to keep unchanged

        Returns:
            Summarized conversation with recent messages preserved
        """
        if not self.model or len(messages) <= preserve_recent:
            return messages

        try:
            # Split messages into to-summarize and to-preserve
            to_summarize = messages[:-preserve_recent] if preserve_recent > 0 else messages
            to_preserve = messages[-preserve_recent:] if preserve_recent > 0 else []

            # Create summary of older messages
            summary_text = await self._create_summary(to_summarize)

            # Create summary message
            summary_message = BaseMessage(
                role="system", content=f"[Conversation Summary: {summary_text}]"
            )

            # Return summary + recent messages
            return [summary_message] + to_preserve

        except Exception as e:
            logger.error(f"Error summarizing conversation: {e}")
            # Fallback to simple truncation
            return messages[-preserve_recent:] if preserve_recent > 0 else messages

    async def _create_summary(self, messages: list[BaseMessage]) -> str:
        """Create a summary of messages using the summarization model."""
        if not self.model:
            # Fallback summary
            return (
                f"Conversation with {len(messages)} messages about political and regulatory topics."
            )

        try:
            # Format messages for summarization
            conversation_text = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])

            summary_prompt = f"""
            Summarize this political/regulatory conversation, preserving:
            - Key entities mentioned (companies, policies, politicians)
            - Main topics and questions discussed
            - Important facts or findings
            - User preferences or interests shown

            Conversation:
            {conversation_text}

            Summary:
            """

            response = await self.model.ainvoke(summary_prompt)
            return response.content[: self.max_summary_tokens]

        except Exception as e:
            logger.error(f"Error creating AI summary: {e}")
            return (
                f"Conversation with {len(messages)} messages about political and regulatory topics."
            )
