"""Memory management for chat agent sessions."""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory stored by the agent."""
    ENTITY_CACHE = "entity_cache"
    QUERY_HISTORY = "query_history"
    RELATIONSHIP_CACHE = "relationship_cache"
    USER_PREFERENCES = "user_preferences"
    CONTEXT_STACK = "context_stack"
    TOOL_RESULTS = "tool_results"


@dataclass
class MemoryEntry:
    """A single memory entry."""
    key: str
    data: Any
    timestamp: datetime
    memory_type: MemoryType
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.last_accessed is None:
            self.last_accessed = self.timestamp


@dataclass
class QueryContext:
    """Context for a user query and its processing."""
    query: str
    query_type: str
    entities_mentioned: List[str]
    tools_used: List[str]
    timestamp: datetime
    results_summary: str = ""
    user_satisfaction: Optional[int] = None  # 1-5 rating if available
    

@dataclass
class EntityMemory:
    """Cached information about an entity."""
    name: str
    entity_type: Optional[str]
    key_facts: List[str]
    relationships: List[Dict[str, Any]]
    last_updated: datetime
    access_count: int = 0
    confidence_score: float = 0.0


class AgentMemory:
    """Memory management system for the chat agent."""
    
    def __init__(self, max_memory_entries: int = 1000, 
                 cache_duration_hours: int = 24):
        """Initialize the memory system."""
        self.max_entries = max_memory_entries
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self._memory: Dict[str, MemoryEntry] = {}
        self._query_history: List[QueryContext] = []
        self._entity_cache: Dict[str, EntityMemory] = {}
        self._current_session_id = self._generate_session_id()
        self._session_start = datetime.now()
        
        logger.info(f"Initialized agent memory with session {self._current_session_id}")
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().isoformat()
        hash_obj = hashlib.md5(timestamp.encode())
        return hash_obj.hexdigest()[:8]
    
    def store_memory(self, key: str, data: Any, memory_type: MemoryType, 
                    metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store data in memory."""
        # Check if we need to clean up old entries
        if len(self._memory) >= self.max_entries:
            self._cleanup_old_entries()
        
        entry = MemoryEntry(
            key=key,
            data=data,
            timestamp=datetime.now(),
            memory_type=memory_type,
            metadata=metadata or {}
        )
        
        self._memory[key] = entry
        logger.debug(f"Stored memory entry: {key} ({memory_type.value})")
    
    def retrieve_memory(self, key: str) -> Optional[Any]:
        """Retrieve data from memory."""
        entry = self._memory.get(key)
        if not entry:
            return None
        
        # Check if entry has expired
        if self._is_expired(entry):
            del self._memory[key]
            return None
        
        # Update access statistics
        entry.access_count += 1
        entry.last_accessed = datetime.now()
        
        logger.debug(f"Retrieved memory entry: {key}")
        return entry.data
    
    def cache_entity(self, entity_name: str, entity_type: Optional[str] = None,
                    facts: Optional[List[str]] = None,
                    relationships: Optional[List[Dict[str, Any]]] = None) -> None:
        """Cache entity information for quick retrieval."""
        entity_memory = EntityMemory(
            name=entity_name,
            entity_type=entity_type,
            key_facts=facts or [],
            relationships=relationships or [],
            last_updated=datetime.now()
        )
        
        self._entity_cache[entity_name.lower()] = entity_memory
        
        # Also store in general memory
        self.store_memory(
            f"entity:{entity_name.lower()}",
            entity_memory,
            MemoryType.ENTITY_CACHE,
            {"entity_type": entity_type}
        )
    
    def get_cached_entity(self, entity_name: str) -> Optional[EntityMemory]:
        """Retrieve cached entity information."""
        entity_memory = self._entity_cache.get(entity_name.lower())
        if entity_memory:
            entity_memory.access_count += 1
            return entity_memory
        return None
    
    def add_query_to_history(self, query: str, query_type: str, 
                           entities: List[str], tools_used: List[str],
                           results_summary: str = "") -> None:
        """Add a query to the conversation history."""
        context = QueryContext(
            query=query,
            query_type=query_type,
            entities_mentioned=entities,
            tools_used=tools_used,
            timestamp=datetime.now(),
            results_summary=results_summary
        )
        
        self._query_history.append(context)
        
        # Keep only recent history
        if len(self._query_history) > 50:
            self._query_history = self._query_history[-50:]
        
        # Store in memory for persistence
        self.store_memory(
            f"query_history:{len(self._query_history)}",
            context,
            MemoryType.QUERY_HISTORY
        )
    
    def get_recent_queries(self, limit: int = 10) -> List[QueryContext]:
        """Get recent queries from history."""
        return self._query_history[-limit:]
    
    def get_related_queries(self, entity_name: str) -> List[QueryContext]:
        """Get queries related to a specific entity."""
        related = []
        entity_lower = entity_name.lower()
        
        for query_context in self._query_history:
            if any(entity_lower in entity.lower() for entity in query_context.entities_mentioned):
                related.append(query_context)
        
        return related[-10:]  # Return last 10 related queries
    
    def cache_tool_result(self, tool_name: str, args: Dict[str, Any], 
                         result: str, ttl_minutes: int = 30) -> None:
        """Cache tool results to avoid redundant calls."""
        # Create a hash of the tool call for caching
        tool_call_hash = self._hash_tool_call(tool_name, args)
        
        self.store_memory(
            f"tool_result:{tool_call_hash}",
            {
                "tool_name": tool_name,
                "args": args,
                "result": result,
                "ttl_minutes": ttl_minutes
            },
            MemoryType.TOOL_RESULTS,
            {"expires_at": datetime.now() + timedelta(minutes=ttl_minutes)}
        )
    
    def get_cached_tool_result(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """Retrieve cached tool result if available and not expired."""
        tool_call_hash = self._hash_tool_call(tool_name, args)
        cached = self.retrieve_memory(f"tool_result:{tool_call_hash}")
        
        if cached:
            # Check TTL
            expires_at = cached.get("metadata", {}).get("expires_at")
            if expires_at and datetime.now() > expires_at:
                return None
            return cached["result"]
        
        return None
    
    def update_context_stack(self, context_type: str, context_data: Dict[str, Any]) -> None:
        """Update the conversation context stack."""
        context_stack = self.retrieve_memory("context_stack") or []
        
        # Add new context
        context_stack.append({
            "type": context_type,
            "data": context_data,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only recent context (last 20 items)
        if len(context_stack) > 20:
            context_stack = context_stack[-20:]
        
        self.store_memory("context_stack", context_stack, MemoryType.CONTEXT_STACK)
    
    def get_conversation_context(self) -> Dict[str, Any]:
        """Get current conversation context for the agent."""
        context = {
            "session_id": self._current_session_id,
            "session_duration": str(datetime.now() - self._session_start),
            "recent_queries": [
                {
                    "query": q.query,
                    "type": q.query_type,
                    "entities": q.entities_mentioned,
                    "timestamp": q.timestamp.isoformat()
                }
                for q in self.get_recent_queries(5)
            ],
            "frequently_accessed_entities": self._get_frequent_entities(),
            "context_stack": self.retrieve_memory("context_stack") or []
        }
        
        return context
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about current memory usage."""
        total_entries = len(self._memory)
        entries_by_type = {}
        expired_count = 0
        
        for entry in self._memory.values():
            mem_type = entry.memory_type.value
            entries_by_type[mem_type] = entries_by_type.get(mem_type, 0) + 1
            
            if self._is_expired(entry):
                expired_count += 1
        
        return {
            "total_entries": total_entries,
            "entries_by_type": entries_by_type,
            "expired_entries": expired_count,
            "entity_cache_size": len(self._entity_cache),
            "query_history_size": len(self._query_history),
            "session_id": self._current_session_id,
            "session_duration": str(datetime.now() - self._session_start),
            "memory_utilization": f"{(total_entries / self.max_entries) * 100:.1f}%"
        }
    
    def suggest_entities_from_context(self, limit: int = 5) -> List[str]:
        """Suggest entities based on recent conversation context."""
        entity_counts = {}
        
        # Count entity mentions in recent queries
        for query_context in self.get_recent_queries(10):
            for entity in query_context.entities_mentioned:
                entity_counts[entity] = entity_counts.get(entity, 0) + 1
        
        # Sort by frequency and return top entities
        sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)
        return [entity for entity, _ in sorted_entities[:limit]]
    
    def clear_session_memory(self) -> None:
        """Clear memory for the current session."""
        logger.info(f"Clearing session memory for {self._current_session_id}")
        
        # Keep only persistent data
        persistent_keys = []
        for key, entry in self._memory.items():
            if entry.memory_type in [MemoryType.USER_PREFERENCES]:
                persistent_keys.append(key)
        
        # Clear most memory
        self._memory = {k: self._memory[k] for k in persistent_keys}
        self._query_history = []
        self._entity_cache = {}
        
        # Start new session
        self._current_session_id = self._generate_session_id()
        self._session_start = datetime.now()
    
    def _cleanup_old_entries(self) -> None:
        """Clean up expired and least-used memory entries."""
        # Remove expired entries first
        expired_keys = []
        for key, entry in self._memory.items():
            if self._is_expired(entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._memory[key]
        
        # If still over limit, remove least-used entries
        if len(self._memory) >= self.max_entries:
            # Sort by access count (ascending) and last access time
            sorted_entries = sorted(
                self._memory.items(),
                key=lambda x: (x[1].access_count, x[1].last_accessed or x[1].timestamp)
            )
            
            # Remove oldest 20%
            remove_count = max(1, len(sorted_entries) // 5)
            for key, _ in sorted_entries[:remove_count]:
                del self._memory[key]
        
        logger.debug(f"Cleaned up memory, now {len(self._memory)} entries")
    
    def _is_expired(self, entry: MemoryEntry) -> bool:
        """Check if a memory entry has expired."""
        age = datetime.now() - entry.timestamp
        return age > self.cache_duration
    
    def _hash_tool_call(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Create a hash for tool call caching."""
        # Sort args to ensure consistent hashing
        sorted_args = json.dumps(args, sort_keys=True)
        content = f"{tool_name}:{sorted_args}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _get_frequent_entities(self) -> List[Dict[str, Any]]:
        """Get frequently accessed entities."""
        entities = []
        for entity_name, entity_memory in self._entity_cache.items():
            entities.append({
                "name": entity_name,
                "type": entity_memory.entity_type,
                "access_count": entity_memory.access_count,
                "last_updated": entity_memory.last_updated.isoformat()
            })
        
        # Sort by access count
        entities.sort(key=lambda x: x["access_count"], reverse=True)
        return entities[:10]


# Global memory instance
memory = AgentMemory()