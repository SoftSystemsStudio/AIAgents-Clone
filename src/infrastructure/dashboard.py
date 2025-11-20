"""
Dashboard Metrics - Real-time metrics aggregation and statistics.

Provides dashboard-friendly metrics collection for visualization.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
from threading import Lock


@dataclass
class AgentStats:
    """Statistics for a single agent."""
    agent_id: str
    name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_duration: float = 0.0
    last_execution: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_executions == 0:
            return 0.0
        return (self.successful_executions / self.total_executions) * 100


@dataclass
class SystemMetrics:
    """System-wide metrics."""
    total_agents: int = 0
    total_executions: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    active_agents: int = 0
    avg_response_time: float = 0.0
    uptime_seconds: float = 0.0
    
    # Recent activity (last hour)
    executions_last_hour: int = 0
    tokens_last_hour: int = 0
    cost_last_hour: float = 0.0


@dataclass
class TimeSeriesPoint:
    """Single data point in time series."""
    timestamp: str
    value: float
    label: str = ""


class DashboardMetrics:
    """
    Aggregates and tracks metrics for dashboard visualization.
    
    Collects real-time stats on:
    - Agent executions (success/failure rates)
    - Token usage over time
    - Cost tracking
    - Performance metrics
    - System health
    
    Thread-safe for concurrent access.
    """
    
    def __init__(self, max_history: int = 100):
        """
        Initialize dashboard metrics.
        
        Args:
            max_history: Maximum number of historical data points to keep
        """
        self.max_history = max_history
        self.lock = Lock()
        
        # Agent-specific stats
        self.agent_stats: Dict[str, AgentStats] = {}
        
        # Time series data (for charts)
        self.token_history: deque = deque(maxlen=max_history)
        self.cost_history: deque = deque(maxlen=max_history)
        self.execution_history: deque = deque(maxlen=max_history)
        self.duration_history: deque = deque(maxlen=max_history)
        
        # Recent executions (last 24 hours)
        self.recent_executions: deque = deque(maxlen=1000)
        
        # System start time
        self.start_time = datetime.utcnow()
        
        # Active executions
        self.active_executions: set = set()
    
    def record_execution(
        self,
        agent_id: str,
        agent_name: str,
        tokens: int,
        cost: float,
        duration: float,
        success: bool,
    ) -> None:
        """
        Record an agent execution.
        
        Args:
            agent_id: Agent identifier
            agent_name: Human-readable agent name
            tokens: Tokens used
            cost: Cost in USD
            duration: Execution duration in seconds
            success: Whether execution succeeded
        """
        with self.lock:
            timestamp = datetime.utcnow().isoformat()
            
            # Update agent-specific stats
            if agent_id not in self.agent_stats:
                self.agent_stats[agent_id] = AgentStats(
                    agent_id=agent_id,
                    name=agent_name,
                )
            
            stats = self.agent_stats[agent_id]
            stats.total_executions += 1
            if success:
                stats.successful_executions += 1
            else:
                stats.failed_executions += 1
            
            stats.total_tokens += tokens
            stats.total_cost += cost
            
            # Update rolling average duration
            n = stats.total_executions
            stats.avg_duration = ((stats.avg_duration * (n - 1)) + duration) / n
            stats.last_execution = timestamp
            
            # Add to time series
            self.token_history.append(
                TimeSeriesPoint(timestamp=timestamp, value=float(tokens), label=agent_name)
            )
            self.cost_history.append(
                TimeSeriesPoint(timestamp=timestamp, value=cost, label=agent_name)
            )
            self.execution_history.append(
                TimeSeriesPoint(timestamp=timestamp, value=1.0, label=agent_name)
            )
            self.duration_history.append(
                TimeSeriesPoint(timestamp=timestamp, value=duration, label=agent_name)
            )
            
            # Add to recent executions
            self.recent_executions.append({
                "timestamp": timestamp,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "tokens": tokens,
                "cost": cost,
                "duration": duration,
                "success": success,
            })
    
    def start_execution(self, agent_id: str) -> None:
        """Mark an agent as actively executing."""
        with self.lock:
            self.active_executions.add(agent_id)
    
    def end_execution(self, agent_id: str) -> None:
        """Mark an agent execution as complete."""
        with self.lock:
            self.active_executions.discard(agent_id)
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get overall system metrics."""
        with self.lock:
            total_tokens = sum(s.total_tokens for s in self.agent_stats.values())
            total_cost = sum(s.total_cost for s in self.agent_stats.values())
            total_executions = sum(s.total_executions for s in self.agent_stats.values())
            
            # Calculate average response time
            if self.agent_stats:
                avg_duration = sum(s.avg_duration for s in self.agent_stats.values()) / len(self.agent_stats)
            else:
                avg_duration = 0.0
            
            # Calculate last hour metrics
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent = [
                e for e in self.recent_executions
                if datetime.fromisoformat(e["timestamp"]) > one_hour_ago
            ]
            
            executions_last_hour = len(recent)
            tokens_last_hour = sum(e["tokens"] for e in recent)
            cost_last_hour = sum(e["cost"] for e in recent)
            
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            
            return SystemMetrics(
                total_agents=len(self.agent_stats),
                total_executions=total_executions,
                total_tokens=total_tokens,
                total_cost=total_cost,
                active_agents=len(self.active_executions),
                avg_response_time=avg_duration,
                uptime_seconds=uptime,
                executions_last_hour=executions_last_hour,
                tokens_last_hour=tokens_last_hour,
                cost_last_hour=cost_last_hour,
            )
    
    def get_agent_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all agents."""
        with self.lock:
            return [asdict(stats) for stats in self.agent_stats.values()]
    
    def get_time_series(
        self,
        metric: str = "tokens",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for a metric.
        
        Args:
            metric: Metric type (tokens, cost, executions, duration)
            limit: Maximum number of points to return
        
        Returns:
            List of time series points
        """
        with self.lock:
            if metric == "tokens":
                data = list(self.token_history)
            elif metric == "cost":
                data = list(self.cost_history)
            elif metric == "executions":
                data = list(self.execution_history)
            elif metric == "duration":
                data = list(self.duration_history)
            else:
                return []
            
            # Return most recent points
            return [asdict(point) for point in data[-limit:]]
    
    def get_recent_executions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent agent executions."""
        with self.lock:
            return list(self.recent_executions)[-limit:]
    
    def get_top_agents(
        self,
        by: str = "executions",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get top agents by a metric.
        
        Args:
            by: Sort metric (executions, tokens, cost)
            limit: Number of agents to return
        
        Returns:
            List of top agent stats
        """
        with self.lock:
            agents = list(self.agent_stats.values())
            
            if by == "executions":
                agents.sort(key=lambda x: x.total_executions, reverse=True)
            elif by == "tokens":
                agents.sort(key=lambda x: x.total_tokens, reverse=True)
            elif by == "cost":
                agents.sort(key=lambda x: x.total_cost, reverse=True)
            
            return [asdict(agent) for agent in agents[:limit]]
    
    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        with self.lock:
            self.agent_stats.clear()
            self.token_history.clear()
            self.cost_history.clear()
            self.execution_history.clear()
            self.duration_history.clear()
            self.recent_executions.clear()
            self.active_executions.clear()
            self.start_time = datetime.utcnow()


# Global dashboard instance
_dashboard_metrics: Optional[DashboardMetrics] = None


def get_dashboard_metrics() -> DashboardMetrics:
    """Get or create the global dashboard metrics instance."""
    global _dashboard_metrics
    if _dashboard_metrics is None:
        _dashboard_metrics = DashboardMetrics()
    return _dashboard_metrics
