"""MCP Client for communicating with the remote MCP server via SSE.

Implements the MCP protocol:
1. Connect to /sse - establishes SSE stream and returns session endpoint
2. Send initialize request
3. POST tool calls to /messages/?session_id=XXX
4. Responses come back via the SSE stream
"""

import asyncio
import json
import logging

import httpx

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for communicating with the remote MCP server via SSE.

    Implements the MCP protocol:
    1. Connect to /sse - establishes SSE stream and returns session endpoint
    2. Send initialize request
    3. POST tool calls to /messages/?session_id=XXX
    4. Responses come back via the SSE stream
    """

    def __init__(self, server_url: str):
        self.server_url = server_url
        self._base_url = server_url.replace("/sse", "")
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a tool on the MCP server and return the result.

        Opens an SSE connection, initializes the session, calls the tool,
        and returns the result.
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                result_text = None
                session_id = None
                waiting_for_init = False
                waiting_for_tool = False
                init_id = None
                tool_id = None

                async with client.stream(
                    "GET",
                    self.server_url,
                    headers={"Accept": "text/event-stream"},
                    timeout=60.0
                ) as sse_response:

                    async for line in sse_response.aiter_lines():
                        line = line.strip()

                        # Get session ID from first data event
                        if line.startswith("data:") and session_id is None:
                            data = line[5:].strip()
                            if "session_id=" in data:
                                session_id = data.split("session_id=")[1].split("&")[0]
                                logger.info(f"Got MCP session ID: {session_id}")

                                # Send initialize request
                                init_id = self._next_id()
                                init_payload = {
                                    "jsonrpc": "2.0",
                                    "id": init_id,
                                    "method": "initialize",
                                    "params": {
                                        "protocolVersion": "2024-11-05",
                                        "capabilities": {},
                                        "clientInfo": {
                                            "name": "policytracker-claude-agent",
                                            "version": "1.0.0"
                                        }
                                    }
                                }

                                messages_url = f"{self._base_url}/messages/?session_id={session_id}"
                                asyncio.create_task(
                                    client.post(messages_url, json=init_payload, headers={"Content-Type": "application/json"})
                                )
                                waiting_for_init = True
                                continue

                        # Process JSON-RPC responses
                        if line.startswith("data:") and session_id is not None:
                            data = line[5:].strip()
                            try:
                                json_data = json.loads(data)
                                response_id = json_data.get("id")

                                # Handle initialization response
                                if waiting_for_init and response_id == init_id:
                                    if "result" in json_data:
                                        logger.info("MCP session initialized")
                                        waiting_for_init = False

                                        # Now send the tool call
                                        tool_id = self._next_id()
                                        tool_payload = {
                                            "jsonrpc": "2.0",
                                            "id": tool_id,
                                            "method": "tools/call",
                                            "params": {
                                                "name": tool_name,
                                                "arguments": arguments
                                            }
                                        }
                                        logger.info(f"Calling tool: {tool_name} with args: {arguments}")
                                        messages_url = f"{self._base_url}/messages/?session_id={session_id}"
                                        asyncio.create_task(
                                            client.post(messages_url, json=tool_payload, headers={"Content-Type": "application/json"})
                                        )
                                        waiting_for_tool = True
                                    elif "error" in json_data:
                                        return f"MCP initialization error: {json_data['error']}"
                                    continue

                                # Handle tool call response
                                if waiting_for_tool and response_id == tool_id:
                                    if "result" in json_data:
                                        content = json_data["result"].get("content", [])
                                        if content and len(content) > 0:
                                            result_text = content[0].get("text", str(json_data))
                                        else:
                                            result_text = str(json_data)
                                        logger.info(f"Got MCP result: {result_text[:100]}...")
                                        return result_text
                                    elif "error" in json_data:
                                        return f"MCP tool error: {json_data['error']}"

                            except json.JSONDecodeError:
                                continue

                return result_text or "Error: No response received from MCP server"

        except httpx.TimeoutException:
            return "Error: MCP server request timed out"
        except Exception as e:
            logger.error(f"MCP call failed: {e}", exc_info=True)
            return f"Error calling MCP server: {str(e)}"

    async def close(self):
        """Close the client (no-op since connections are per-call)."""
        pass
