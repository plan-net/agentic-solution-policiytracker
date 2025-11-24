"""
Pagination utilities for Bundestag DIP API.

Handles cursor-based pagination for API responses, yielding results as they arrive.
"""

from collections.abc import AsyncGenerator
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class PaginationHelper:
    """
    Helper class for handling Bundestag API pagination.

    The Bundestag DIP API uses cursor-based pagination with cursor metadata
    in the response. This helper manages the pagination flow and yields
    results incrementally.

    Attributes:
        api_client: Instance of BundestagAPIClient for making requests
        max_items: Maximum number of items to retrieve (None for unlimited)
    """

    def __init__(self, api_client, max_items: Optional[int] = None):
        """
        Initialize the pagination helper.

        Args:
            api_client: BundestagAPIClient instance for making API requests
            max_items: Maximum number of items to retrieve (None for unlimited)
        """
        self.api_client = api_client
        self.max_items = max_items

        logger.debug("Initialized PaginationHelper", max_items=max_items)

    async def paginate(
        self, endpoint: str, params: Optional[dict[str, Any]] = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Paginate through API results yielding items as they arrive.

        Args:
            endpoint: API endpoint to paginate through
            params: Query parameters for the initial request

        Yields:
            Individual result items from the API response

        Example:
            >>> helper = PaginationHelper(client, max_items=100)
            >>> async for item in helper.paginate("vorgang", {"f.wahlperiode": "20"}):
            ...     process_item(item)
        """
        params = params or {}
        cursor = None
        items_retrieved = 0
        page_number = 0

        logger.info(
            "Starting pagination",
            endpoint=endpoint,
            max_items=self.max_items,
            initial_params=params,
        )

        while True:
            page_number += 1

            # Add cursor to params if we have one
            if cursor:
                params["cursor"] = cursor

            try:
                # Make API request
                logger.debug(
                    "Fetching page",
                    page=page_number,
                    cursor=cursor,
                    items_retrieved=items_retrieved,
                )

                response = await self.api_client.get(endpoint, params=params)

                # Extract results and cursor
                documents = response.get("documents", [])

                # Cursor is a string token, not a dict
                next_cursor = response.get("cursor")

                logger.info(
                    "Retrieved page",
                    page=page_number,
                    items_in_page=len(documents),
                    total_retrieved=items_retrieved + len(documents),
                    has_next=bool(next_cursor),
                )

                # Stop if no documents in this page (prevents infinite loop)
                if not documents:
                    logger.info("No more documents to retrieve", total_retrieved=items_retrieved)
                    return

                # Yield results
                for doc in documents:
                    # Check max_items limit
                    if self.max_items and items_retrieved >= self.max_items:
                        logger.info(
                            "Reached max_items limit",
                            max_items=self.max_items,
                            total_retrieved=items_retrieved,
                        )
                        return

                    yield doc
                    items_retrieved += 1

                # Check if there are more pages
                if not next_cursor:
                    logger.info(
                        "Pagination complete", total_pages=page_number, total_items=items_retrieved
                    )
                    break

                # Update cursor for next iteration
                cursor = next_cursor

            except Exception as e:
                logger.error(
                    "Error during pagination",
                    page=page_number,
                    error=str(e),
                    items_retrieved=items_retrieved,
                )
                raise

    async def paginate_all(
        self, endpoint: str, params: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """
        Paginate through all results and return as a list.

        This is a convenience method that collects all results into memory.
        Use paginate() for streaming results when dealing with large datasets.

        Args:
            endpoint: API endpoint to paginate through
            params: Query parameters for the initial request

        Returns:
            List of all result items
        """
        results = []

        async for item in self.paginate(endpoint, params):
            results.append(item)

        logger.info("Collected all paginated results", endpoint=endpoint, total_items=len(results))

        return results

    async def count_items(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> int:
        """
        Count the total number of items without retrieving them.

        Makes a single API request to get the total count from cursor metadata.

        Args:
            endpoint: API endpoint to count items from
            params: Query parameters for the request

        Returns:
            Total number of items matching the query
        """
        params = params or {}

        # Request just one item to get the count
        params["num"] = 1

        try:
            response = await self.api_client.get(endpoint, params=params)
            cursor_metadata = response.get("cursor", {})

            # The 'numFound' field contains the total count
            total_count = cursor_metadata.get("numFound", 0)

            logger.info("Retrieved item count", endpoint=endpoint, total_count=total_count)

            return total_count

        except Exception as e:
            logger.error("Error counting items", endpoint=endpoint, error=str(e))
            raise

    async def paginate_with_progress(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        progress_callback: Optional[callable] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Paginate with progress updates via callback.

        Args:
            endpoint: API endpoint to paginate through
            params: Query parameters for the request
            progress_callback: Async function called with (current, total) for progress updates

        Yields:
            Individual result items from the API response
        """
        # Get total count if progress callback provided
        total_items = None
        if progress_callback:
            try:
                total_items = await self.count_items(endpoint, params)
            except Exception as e:
                logger.warning("Could not retrieve item count for progress", error=str(e))

        items_retrieved = 0

        async for item in self.paginate(endpoint, params):
            items_retrieved += 1

            # Call progress callback
            if progress_callback:
                try:
                    await progress_callback(items_retrieved, total_items)
                except Exception as e:
                    logger.warning("Progress callback failed", error=str(e))

            yield item
