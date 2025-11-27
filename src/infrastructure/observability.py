"""
Observability - Structured logging, tracing, and metrics.

Provides production-ready observability with:
- Structured JSON logging (via structlog)
- Distributed tracing (OpenTelemetry)
- Metrics (Prometheus)
"""

from typing import Any, Dict, Optional
import structlog
from contextlib import contextmanager

from src.domain.interfaces import IObservabilityService


# Backwards-compatible factory for obtaining an observability provider.
def ObservabilityProvider(
    service_name: str = "app",
    environment: str = "dev",
    provider: str = "structured",
    **kwargs,
) -> IObservabilityService:
    """
    Simple factory that returns an `IObservabilityService` implementation.

    Tests and lightweight deployments expect to call `ObservabilityProvider(...)`.
    Default implementation returns `StructuredLogger`. Advanced setups may
    inspect `provider` and return `OpenTelemetryObservability` or
    `PrometheusObservability` when configured.
    """
    # For now default to structured logger which has no external deps.
    return StructuredLogger(log_level=kwargs.get("log_level", "INFO"))


class StructuredLogger(IObservabilityService):
    """
    Structured logging implementation using structlog.
    
    Provides JSON-formatted logs with context and correlation IDs.
    Integrates with log aggregation systems (ELK, Splunk, DataDog).
    """

    def __init__(self, log_level: str = "INFO"):
        """
        Initialize structured logger.
        
        Args:
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
        """
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                self._parse_log_level(log_level)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        self.logger = structlog.get_logger()

    def log(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a structured message.
        
        Args:
            level: Log level (debug, info, warning, error)
            message: Log message
            context: Additional context as key-value pairs
        """
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        
        if context:
            log_func(message, **context)
        else:
            log_func(message)

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Any:
        """
        Start a trace span (no-op in basic implementation).
        
        For full tracing, use OpenTelemetryObservability.
        """
        return None

    def record_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Record a metric (logged as structured log).
        
        For proper metrics, use PrometheusObservability.
        """
        self.log(
            "info",
            f"metric: {name}",
            {"metric_name": name, "metric_value": value, "labels": labels},
        )

    async def health_check(self) -> Dict[str, Any]:
        """Health check for logging system."""
        return {"status": "healthy", "service": "structured_logger"}

    def _parse_log_level(self, level: str) -> int:
        """Convert string log level to structlog level."""
        import logging
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        return levels.get(level.upper(), logging.INFO)


class OpenTelemetryObservability(IObservabilityService):
    """
    OpenTelemetry-based observability.
    
    Provides distributed tracing with support for multiple backends:
    - Jaeger
    - Zipkin
    - DataDog
    - New Relic
    
    TODO: Add automatic instrumentation for HTTP/Redis/Database
    """

    def __init__(
        self,
        service_name: str,
        exporter_endpoint: str,
        log_level: str = "INFO",
    ):
        """
        Initialize OpenTelemetry observability.
        
        Args:
            service_name: Name of this service
            exporter_endpoint: OTLP exporter endpoint
            log_level: Log level
        """
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
        except ImportError:
            raise ImportError(
                "OpenTelemetry not installed. "
                "Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp"
            )

        # Set up tracing
        resource = Resource(attributes={"service.name": service_name})
        
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint=exporter_endpoint)
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        
        self.tracer = trace.get_tracer(__name__)
        
        # Also include structured logging
        self.logger = StructuredLogger(log_level)

    def log(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log with tracing context."""
        self.logger.log(level, message, context)

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Any:
        """
        Start a distributed trace span.
        
        Use as context manager:
        ```python
        with observability.start_span("agent_execution") as span:
            # Do work
            span.set_attribute("agent_id", agent_id)
        ```
        """
        return self.tracer.start_as_current_span(
            name,
            attributes=attributes or {},
        )

    def record_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record metric via logging."""
        self.logger.record_metric(name, value, labels)

    async def health_check(self) -> Dict[str, Any]:
        """Health check for observability system."""
        return {
            "status": "healthy",
            "service": "opentelemetry",
            "tracer": "active",
        }


class PrometheusObservability(StructuredLogger):
    """
    Prometheus metrics with structured logging.
    
    Exposes metrics endpoint for Prometheus scraping.
    
    Common metrics:
    - agent_execution_duration_seconds
    - agent_execution_total
    - llm_tokens_total
    - llm_cost_usd
    - tool_invocation_total
    """

    def __init__(
        self,
        log_level: str = "INFO",
        metrics_port: int = 9090,
    ):
        """
        Initialize Prometheus metrics.
        
        Args:
            log_level: Log level for structured logging
            metrics_port: Port to expose metrics on
        """
        super().__init__(log_level)
        
        try:
            from prometheus_client import Counter, Histogram, Gauge, start_http_server
        except ImportError:
            raise ImportError(
                "Prometheus client not installed. "
                "Install with: pip install prometheus-client"
            )

        # Define metrics
        self.execution_duration = Histogram(
            "agent_execution_duration_seconds",
            "Agent execution duration",
            ["agent_id", "status"],
        )
        
        self.execution_total = Counter(
            "agent_execution_total",
            "Total agent executions",
            ["agent_id", "status"],
        )
        
        self.tokens_total = Counter(
            "llm_tokens_total",
            "Total LLM tokens used",
            ["agent_id", "model", "token_type"],
        )
        
        self.cost_usd = Counter(
            "llm_cost_usd_total",
            "Total LLM cost in USD",
            ["agent_id", "model"],
        )
        
        self.tool_invocations = Counter(
            "tool_invocation_total",
            "Total tool invocations",
            ["tool_name", "status"],
        )

        # Start metrics server
        start_http_server(metrics_port)
        self.log("info", f"Prometheus metrics exposed on port {metrics_port}")

    def record_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Record a metric to Prometheus.
        
        Maps metric names to Prometheus collectors.
        """
        labels = labels or {}
        
        # Route to appropriate metric
        if name == "agent_execution_duration":
            self.execution_duration.labels(**labels).observe(value)
        elif name == "agent_execution":
            self.execution_total.labels(**labels).inc()
        elif name == "llm_tokens":
            self.tokens_total.labels(**labels).inc(value)
        elif name == "llm_cost":
            self.cost_usd.labels(**labels).inc(value)
        elif name == "tool_invocation":
            self.tool_invocations.labels(**labels).inc()
        
        # Also log
        super().record_metric(name, value, labels)

    async def health_check(self) -> Dict[str, Any]:
        """Health check for Prometheus metrics."""
        return {
            "status": "healthy",
            "service": "prometheus",
            "metrics_endpoint": f"http://localhost:9090/metrics",
        }
