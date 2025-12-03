"""
Rate limiting utilities for polite web crawling.

Provides async-aware rate limiting, domain-based throttling,
and robots.txt compliance.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import aiohttp
import structlog

logger = structlog.get_logger()


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiting."""

    # Request delays
    request_delay_seconds: float = 1.5
    min_delay_seconds: float = 0.5
    max_delay_seconds: float = 5.0

    # Concurrency
    max_concurrent_requests: int = 3
    max_requests_per_minute: int = 30

    # Timeouts
    request_timeout_seconds: int = 30

    # Behavior
    respect_robots_txt: bool = True
    respect_retry_after: bool = True

    # Backoff settings
    backoff_factor: float = 2.0
    max_retries: int = 3


@dataclass
class DomainState:
    """State tracking for a single domain."""

    domain: str
    last_request_time: float = 0.0
    request_count: int = 0
    error_count: int = 0
    current_delay: float = 1.5
    robots_txt_content: Optional[str] = None
    robots_txt_checked: bool = False
    disallowed_paths: list[str] = field(default_factory=list)


class RateLimiter:
    """Async-aware rate limiter for polite web crawling.

    Features:
    - Per-domain rate limiting
    - Exponential backoff on errors
    - Optional robots.txt compliance
    - Concurrent request limiting via semaphore
    """

    def __init__(self, config: Optional[RateLimiterConfig] = None):
        """Initialize the rate limiter.

        Args:
            config: Rate limiting configuration
        """
        self.config = config or RateLimiterConfig()
        self._domain_states: dict[str, DomainState] = {}
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        self._request_times: list[float] = []

        logger.info(
            "Initialized RateLimiter",
            delay=self.config.request_delay_seconds,
            max_concurrent=self.config.max_concurrent_requests,
        )

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")

    def _get_domain_state(self, domain: str) -> DomainState:
        """Get or create state for a domain."""
        if domain not in self._domain_states:
            self._domain_states[domain] = DomainState(
                domain=domain,
                current_delay=self.config.request_delay_seconds,
            )
        return self._domain_states[domain]

    async def acquire(self, url: str) -> None:
        """Acquire permission to make a request.

        This method:
        1. Waits for semaphore slot
        2. Enforces per-domain delay
        3. Enforces global rate limit

        Args:
            url: URL about to be requested
        """
        domain = self._get_domain(url)
        state = self._get_domain_state(domain)

        # Wait for semaphore slot
        await self._semaphore.acquire()

        try:
            # Calculate required delay
            now = time.time()
            elapsed = now - state.last_request_time

            if elapsed < state.current_delay:
                wait_time = state.current_delay - elapsed
                logger.debug(
                    f"Rate limiting: waiting {wait_time:.2f}s",
                    domain=domain,
                    delay=state.current_delay,
                )
                await asyncio.sleep(wait_time)

            # Enforce global rate limit (requests per minute)
            await self._enforce_global_rate_limit()

            # Update state
            state.last_request_time = time.time()
            state.request_count += 1
            self._request_times.append(time.time())

        except Exception:
            self._semaphore.release()
            raise

    def release(self) -> None:
        """Release the semaphore slot."""
        self._semaphore.release()

    async def _enforce_global_rate_limit(self) -> None:
        """Enforce global requests per minute limit."""
        now = time.time()

        # Clean old request times
        cutoff = now - 60
        self._request_times = [t for t in self._request_times if t > cutoff]

        # Check if we've exceeded the limit
        if len(self._request_times) >= self.config.max_requests_per_minute:
            oldest = self._request_times[0]
            wait_time = 60 - (now - oldest) + 0.1  # Small buffer
            if wait_time > 0:
                logger.info(
                    f"Global rate limit: waiting {wait_time:.2f}s",
                    requests_in_minute=len(self._request_times),
                )
                await asyncio.sleep(wait_time)

    def mark_success(self, url: str) -> None:
        """Mark a successful request to reduce delay.

        Args:
            url: URL that was successfully requested
        """
        domain = self._get_domain(url)
        state = self._get_domain_state(domain)

        # Gradually reduce delay on success (min bounded)
        state.current_delay = max(
            self.config.min_delay_seconds,
            state.current_delay * 0.95,
        )

    def mark_error(self, url: str, status_code: Optional[int] = None) -> None:
        """Mark a failed request to increase delay.

        Args:
            url: URL that failed
            status_code: HTTP status code if available
        """
        domain = self._get_domain(url)
        state = self._get_domain_state(domain)

        state.error_count += 1

        # Exponential backoff on errors (max bounded)
        state.current_delay = min(
            self.config.max_delay_seconds,
            state.current_delay * self.config.backoff_factor,
        )

        logger.warning(
            f"Request error, increasing delay",
            domain=domain,
            new_delay=state.current_delay,
            error_count=state.error_count,
            status_code=status_code,
        )

    def mark_rate_limited(self, url: str, retry_after: Optional[int] = None) -> None:
        """Mark that we've been rate limited (429 response).

        Args:
            url: URL that returned 429
            retry_after: Retry-After header value in seconds
        """
        domain = self._get_domain(url)
        state = self._get_domain_state(domain)

        if retry_after and self.config.respect_retry_after:
            state.current_delay = max(state.current_delay, float(retry_after))
        else:
            # Double the delay on rate limiting
            state.current_delay = min(
                self.config.max_delay_seconds,
                state.current_delay * 2.0,
            )

        logger.warning(
            f"Rate limited by server",
            domain=domain,
            new_delay=state.current_delay,
            retry_after=retry_after,
        )

    async def check_robots_txt(
        self,
        domain: str,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> bool:
        """Fetch and parse robots.txt for a domain.

        Args:
            domain: Domain to check
            session: Optional aiohttp session

        Returns:
            True if robots.txt was successfully fetched
        """
        if not self.config.respect_robots_txt:
            return True

        state = self._get_domain_state(domain)

        if state.robots_txt_checked:
            return state.robots_txt_content is not None

        robots_url = f"https://{domain}/robots.txt"

        try:
            if session is None:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as temp_session:
                    async with temp_session.get(robots_url) as response:
                        if response.status == 200:
                            state.robots_txt_content = await response.text()
                            self._parse_robots_txt(state)
            else:
                async with session.get(robots_url) as response:
                    if response.status == 200:
                        state.robots_txt_content = await response.text()
                        self._parse_robots_txt(state)

            state.robots_txt_checked = True
            logger.info(
                f"Fetched robots.txt",
                domain=domain,
                disallowed_paths=len(state.disallowed_paths),
            )
            return True

        except Exception as e:
            state.robots_txt_checked = True
            logger.warning(f"Failed to fetch robots.txt", domain=domain, error=str(e))
            return False

    def _parse_robots_txt(self, state: DomainState) -> None:
        """Parse robots.txt content and extract disallowed paths.

        Args:
            state: Domain state to update
        """
        if not state.robots_txt_content:
            return

        # Simple parser - looks for Disallow rules applicable to all agents
        in_relevant_section = False
        disallowed = []

        for line in state.robots_txt_content.split("\n"):
            line = line.strip().lower()

            if line.startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip()
                in_relevant_section = agent in ("*", "policytracker")
            elif in_relevant_section and line.startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if path:
                    disallowed.append(path)

        state.disallowed_paths = disallowed

    def is_allowed(self, url: str) -> bool:
        """Check if a URL is allowed by robots.txt.

        Args:
            url: URL to check

        Returns:
            True if URL is allowed (or robots.txt not checked)
        """
        if not self.config.respect_robots_txt:
            return True

        domain = self._get_domain(url)
        state = self._get_domain_state(domain)

        if not state.robots_txt_checked:
            # Haven't checked yet, assume allowed
            return True

        parsed = urlparse(url)
        path = parsed.path.lower()

        for disallowed in state.disallowed_paths:
            if path.startswith(disallowed):
                logger.debug(f"URL disallowed by robots.txt", url=url, rule=disallowed)
                return False

        return True

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "domains_tracked": len(self._domain_states),
            "total_requests": sum(s.request_count for s in self._domain_states.values()),
            "total_errors": sum(s.error_count for s in self._domain_states.values()),
            "requests_last_minute": len(self._request_times),
            "domain_stats": {
                domain: {
                    "request_count": state.request_count,
                    "error_count": state.error_count,
                    "current_delay": state.current_delay,
                }
                for domain, state in self._domain_states.items()
            },
        }


class RateLimitedSession:
    """Wrapper around aiohttp session with built-in rate limiting.

    Provides a convenient interface for making rate-limited requests.
    """

    def __init__(
        self,
        rate_limiter: RateLimiter,
        session: Optional[aiohttp.ClientSession] = None,
        user_agent: str = "PolicyTracker/1.0 (Political Monitoring Research)",
    ):
        self.rate_limiter = rate_limiter
        self._session = session
        self._owns_session = session is None
        self.user_agent = user_agent

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(
                total=self.rate_limiter.config.request_timeout_seconds
            )
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": self.user_agent},
            )
        return self._session

    async def close(self) -> None:
        """Close the session if we own it."""
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def get(
        self,
        url: str,
        **kwargs,
    ) -> Optional[aiohttp.ClientResponse]:
        """Make a rate-limited GET request.

        Args:
            url: URL to fetch
            **kwargs: Additional arguments for aiohttp

        Returns:
            Response object, or None if failed
        """
        # Check robots.txt
        if not self.rate_limiter.is_allowed(url):
            logger.info(f"Skipping URL disallowed by robots.txt", url=url)
            return None

        # Acquire rate limit slot
        await self.rate_limiter.acquire(url)

        try:
            session = await self.get_session()
            response = await session.get(url, **kwargs)

            # Handle response status
            if response.status == 429:
                retry_after = response.headers.get("Retry-After")
                self.rate_limiter.mark_rate_limited(
                    url,
                    int(retry_after) if retry_after and retry_after.isdigit() else None,
                )
                return None
            elif response.status >= 400:
                self.rate_limiter.mark_error(url, response.status)
                return response
            else:
                self.rate_limiter.mark_success(url)
                return response

        except Exception as e:
            self.rate_limiter.mark_error(url)
            logger.error(f"Request failed", url=url, error=str(e))
            return None

        finally:
            self.rate_limiter.release()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
