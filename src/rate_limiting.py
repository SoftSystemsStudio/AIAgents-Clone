"""
Rate Limiting - Prevent runaway costs and abuse.

Provides token budgets, cost caps, and request throttling to ensure
safe operation of AI agents.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import deque
import structlog

logger = structlog.get_logger()


@dataclass
class UsageStats:
    """Track usage statistics for rate limiting."""
    
    requests_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    window_start: datetime = field(default_factory=datetime.utcnow)
    recent_requests: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def reset(self):
        """Reset statistics for new time window."""
        self.requests_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.window_start = datetime.utcnow()
        self.recent_requests.clear()


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    
    # Request limits
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000
    max_requests_per_day: int = 10000
    
    # Token limits
    max_tokens_per_request: int = 4000
    max_tokens_per_minute: int = 100000
    max_tokens_per_day: int = 1000000
    
    # Cost limits (USD)
    max_cost_per_request: float = 1.0
    max_cost_per_hour: float = 10.0
    max_cost_per_day: float = 100.0
    
    # Burst allowance
    burst_multiplier: float = 1.5  # Allow 50% burst above limits


class RateLimiter:
    """
    Rate limiter with token budgets and cost caps.
    
    Tracks usage across multiple time windows and enforces limits
    to prevent runaway costs.
    
    Usage:
        limiter = RateLimiter(config)
        await limiter.check_and_record(
            tokens=500,
            estimated_cost=0.01,
            user_id="user123"
        )
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limit configuration (uses defaults if None)
        """
        self.config = config or RateLimitConfig()
        
        # Per-user stats
        self.user_stats: Dict[str, Dict[str, UsageStats]] = {}
        
        # Global stats
        self.global_stats = {
            "minute": UsageStats(),
            "hour": UsageStats(),
            "day": UsageStats(),
        }
        
        # Emergency kill switch
        self.emergency_stop = False
        
        logger.info("Rate limiter initialized", config=self.config)
    
    async def check_and_record(
        self,
        tokens: int,
        estimated_cost: float,
        user_id: str = "default",
    ) -> None:
        """
        Check rate limits and record usage.
        
        Args:
            tokens: Number of tokens for this request
            estimated_cost: Estimated cost in USD
            user_id: User identifier for per-user limits
            
        Raises:
            RateLimitError: If any rate limit is exceeded
        """
        # Emergency stop check
        if self.emergency_stop:
            raise RateLimitError(
                "Emergency stop activated - all requests blocked",
                "emergency_stop",
            )
        
        # Initialize user stats if needed
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {
                "minute": UsageStats(),
                "hour": UsageStats(),
                "day": UsageStats(),
            }
        
        user_stats = self.user_stats[user_id]
        
        # Rotate time windows
        self._rotate_windows()
        
        # Check per-request limits
        if tokens > self.config.max_tokens_per_request:
            raise RateLimitError(
                f"Request exceeds token limit: {tokens} > {self.config.max_tokens_per_request}",
                "tokens_per_request",
            )
        
        if estimated_cost > self.config.max_cost_per_request:
            raise RateLimitError(
                f"Request exceeds cost limit: ${estimated_cost:.2f} > ${self.config.max_cost_per_request:.2f}",
                "cost_per_request",
            )
        
        # Check rate limits (with burst allowance)
        burst_limit = lambda x: x * self.config.burst_multiplier
        
        # Requests per minute
        if user_stats["minute"].requests_count >= burst_limit(self.config.max_requests_per_minute):
            raise RateLimitError(
                f"Too many requests per minute: {user_stats['minute'].requests_count}",
                "requests_per_minute",
                retry_after=60,
            )
        
        # Tokens per minute
        if user_stats["minute"].total_tokens + tokens > burst_limit(self.config.max_tokens_per_minute):
            raise RateLimitError(
                f"Token limit exceeded (per minute): {user_stats['minute'].total_tokens + tokens}",
                "tokens_per_minute",
                retry_after=60,
            )
        
        # Cost per hour
        if user_stats["hour"].total_cost + estimated_cost > self.config.max_cost_per_hour:
            raise RateLimitError(
                f"Cost limit exceeded (per hour): ${user_stats['hour'].total_cost + estimated_cost:.2f}",
                "cost_per_hour",
                retry_after=3600,
            )
        
        # Cost per day
        if user_stats["day"].total_cost + estimated_cost > self.config.max_cost_per_day:
            raise RateLimitError(
                f"Daily cost limit exceeded: ${user_stats['day'].total_cost + estimated_cost:.2f}",
                "cost_per_day",
                retry_after=86400,
            )
        
        # Record usage
        now = datetime.utcnow()
        for window in ["minute", "hour", "day"]:
            stats = user_stats[window]
            stats.requests_count += 1
            stats.total_tokens += tokens
            stats.total_cost += estimated_cost
            stats.recent_requests.append({
                "timestamp": now,
                "tokens": tokens,
                "cost": estimated_cost,
            })
            
            # Also update global stats
            global_stats = self.global_stats[window]
            global_stats.requests_count += 1
            global_stats.total_tokens += tokens
            global_stats.total_cost += estimated_cost
        
        logger.debug(
            "Rate limit check passed",
            user_id=user_id,
            tokens=tokens,
            cost=estimated_cost,
            minute_usage=user_stats["minute"].requests_count,
        )
    
    def _rotate_windows(self):
        """Rotate time windows and reset expired stats."""
        now = datetime.utcnow()
        
        # Check each user's windows
        for user_id, stats in self.user_stats.items():
            # Minute window (60 seconds)
            if now - stats["minute"].window_start > timedelta(seconds=60):
                stats["minute"].reset()
            
            # Hour window (3600 seconds)
            if now - stats["hour"].window_start > timedelta(seconds=3600):
                stats["hour"].reset()
            
            # Day window (86400 seconds)
            if now - stats["day"].window_start > timedelta(seconds=86400):
                stats["day"].reset()
        
        # Rotate global windows
        for window_name, window_seconds in [("minute", 60), ("hour", 3600), ("day", 86400)]:
            stats = self.global_stats[window_name]
            if now - stats.window_start > timedelta(seconds=window_seconds):
                stats.reset()
    
    def get_usage(self, user_id: str = "default") -> Dict:
        """
        Get current usage statistics for a user.
        
        Returns:
            Dictionary with usage stats for each time window
        """
        if user_id not in self.user_stats:
            return {
                "minute": {"requests": 0, "tokens": 0, "cost": 0.0},
                "hour": {"requests": 0, "tokens": 0, "cost": 0.0},
                "day": {"requests": 0, "tokens": 0, "cost": 0.0},
            }
        
        stats = self.user_stats[user_id]
        return {
            "minute": {
                "requests": stats["minute"].requests_count,
                "tokens": stats["minute"].total_tokens,
                "cost": round(stats["minute"].total_cost, 4),
                "limit": self.config.max_requests_per_minute,
            },
            "hour": {
                "requests": stats["hour"].requests_count,
                "tokens": stats["hour"].total_tokens,
                "cost": round(stats["hour"].total_cost, 4),
                "limit": self.config.max_requests_per_hour,
            },
            "day": {
                "requests": stats["day"].requests_count,
                "tokens": stats["day"].total_tokens,
                "cost": round(stats["day"].total_cost, 4),
                "limit": self.config.max_requests_per_day,
            },
        }
    
    def get_global_usage(self) -> Dict:
        """Get global usage statistics across all users."""
        return {
            "minute": {
                "requests": self.global_stats["minute"].requests_count,
                "tokens": self.global_stats["minute"].total_tokens,
                "cost": round(self.global_stats["minute"].total_cost, 4),
            },
            "hour": {
                "requests": self.global_stats["hour"].requests_count,
                "tokens": self.global_stats["hour"].total_tokens,
                "cost": round(self.global_stats["hour"].total_cost, 4),
            },
            "day": {
                "requests": self.global_stats["day"].requests_count,
                "tokens": self.global_stats["day"].total_tokens,
                "cost": round(self.global_stats["day"].total_cost, 4),
            },
        }
    
    def reset_user(self, user_id: str):
        """Reset usage stats for a specific user."""
        if user_id in self.user_stats:
            del self.user_stats[user_id]
            logger.info("Reset rate limits for user", user_id=user_id)
    
    def activate_emergency_stop(self):
        """Activate emergency stop - blocks all requests."""
        self.emergency_stop = True
        logger.critical("EMERGENCY STOP ACTIVATED - All requests blocked")
    
    def deactivate_emergency_stop(self):
        """Deactivate emergency stop."""
        self.emergency_stop = False
        logger.info("Emergency stop deactivated")


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str, limit_type: str, retry_after: Optional[int] = None):
        """
        Initialize rate limit error.
        
        Args:
            message: Error message
            limit_type: Type of limit exceeded
            retry_after: Seconds until retry is allowed
        """
        super().__init__(message)
        self.limit_type = limit_type
        self.retry_after = retry_after
