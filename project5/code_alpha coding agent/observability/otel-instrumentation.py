# OpenTelemetry Instrumentation for Code Alpha
# Add to your application code for automatic telemetry collection

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.resources import Resource
from prometheus_client import start_http_server
import os
import logging


def setup_otel_tracing(service_name: str, environment: str = "production"):
    """
    Set up OpenTelemetry tracing for a service.
    
    Args:
        service_name: Name of the service (e.g., "api", "orchestrator")
        environment: Deployment environment (e.g., "dev", "prod")
    """
    
    # Create resource
    resource = Resource.create({
        "service.name": service_name,
        "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
        "deployment.environment": environment,
        "service.instance_id": os.getenv("POD_NAME", "unknown"),
    })
    
    # Set up OTLP trace exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "false").lower() == "true",
    )
    
    # Create tracer provider with OTLP exporter
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(trace_provider)
    
    # Set up metrics
    prometheus_reader = PrometheusMetricReader()
    metric_provider = MeterProvider(
        resource=resource,
        metric_readers=[prometheus_reader],
    )
    metrics.set_meter_provider(metric_provider)
    
    # Start Prometheus metrics server
    metrics_port = int(os.getenv("METRICS_PORT", "8000"))
    try:
        start_http_server(port=metrics_port, addr="0.0.0.0")
        logging.info(f"Prometheus metrics server started on port {metrics_port}")
    except Exception as e:
        logging.warning(f"Could not start Prometheus metrics server: {e}")
    
    return trace_provider, metric_provider


def instrument_fastapi(app, service_name: str):
    """Instrument FastAPI application with OpenTelemetry"""
    FastAPIInstrumentor.instrument_app(app)
    logging.info(f"FastAPI instrumented for service: {service_name}")


def instrument_flask(app, service_name: str):
    """Instrument Flask application with OpenTelemetry"""
    FlaskInstrumentor().instrument_app(app)
    logging.info(f"Flask instrumented for service: {service_name}")


def instrument_libraries():
    """Instrument common libraries with OpenTelemetry"""
    
    # Instrument HTTP requests
    RequestsInstrumentor().instrument()
    logging.debug("Instrumented: requests")
    
    # Instrument database drivers
    try:
        Psycopg2Instrumentor().instrument()
        logging.debug("Instrumented: psycopg2 (PostgreSQL)")
    except Exception as e:
        logging.debug(f"Could not instrument psycopg2: {e}")
    
    try:
        SQLAlchemyInstrumentor().instrument()
        logging.debug("Instrumented: sqlalchemy")
    except Exception as e:
        logging.debug(f"Could not instrument sqlalchemy: {e}")
    
    # Instrument Redis
    try:
        RedisInstrumentor().instrument()
        logging.debug("Instrumented: redis")
    except Exception as e:
        logging.debug(f"Could not instrument redis: {e}")
    
    # Instrument logging
    LoggingInstrumentor().instrument()
    logging.debug("Instrumented: logging")


def create_custom_metrics(service_name: str):
    """Create custom metrics for Code Alpha services"""
    
    meter = metrics.get_meter(service_name)
    
    # API metrics
    http_requests = meter.create_counter(
        "http_requests_total",
        description="Total HTTP requests",
        unit="1",
    )
    
    http_request_duration = meter.create_histogram(
        "http_request_duration_seconds",
        description="HTTP request duration",
        unit="s",
    )
    
    # Task metrics
    tasks_total = meter.create_counter(
        "tasks_total",
        description="Total tasks processed",
        unit="1",
    )
    
    tasks_duration = meter.create_histogram(
        "task_duration_seconds",
        description="Task processing duration",
        unit="s",
    )
    
    tasks_failed = meter.create_counter(
        "tasks_failed_total",
        description="Total failed tasks",
        unit="1",
    )
    
    # Safety metrics
    blocked_actions = meter.create_counter(
        "safety_blocked_actions_total",
        description="Total blocked actions",
        unit="1",
    )
    
    # Queue metrics
    queue_depth = meter.create_observable_gauge(
        "queue_depth",
        description="Current queue depth",
        unit="1",
    )
    
    # Memory metrics
    memory_usage = meter.create_observable_gauge(
        "memory_usage_bytes",
        description="Current memory usage",
        unit="By",
    )
    
    return {
        "http_requests": http_requests,
        "http_request_duration": http_request_duration,
        "tasks_total": tasks_total,
        "task_duration": tasks_duration,
        "tasks_failed": tasks_failed,
        "blocked_actions": blocked_actions,
        "queue_depth": queue_depth,
        "memory_usage": memory_usage,
    }


class OTelContext:
    """Context manager for span creation with automatic attribute handling"""
    
    def __init__(self, span_name: str, attributes: dict = None):
        self.span_name = span_name
        self.attributes = attributes or {}
        self.span = None
    
    def __enter__(self):
        tracer = trace.get_tracer(__name__)
        self.span = tracer.start_span(self.span_name)
        
        # Add attributes
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.span.set_attribute("error", True)
            self.span.set_attribute("error.type", exc_type.__name__)
            self.span.set_attribute("error.message", str(exc_val))
        
        self.span.end()


# Usage example in FastAPI application:
"""
from fastapi import FastAPI
from observability.otel_instrumentation import (
    setup_otel_tracing,
    instrument_fastapi,
    instrument_libraries,
    create_custom_metrics,
    OTelContext
)

app = FastAPI()

# Initialize OpenTelemetry
trace_provider, metric_provider = setup_otel_tracing("api", "production")
instrument_fastapi(app, "api")
instrument_libraries()
metrics = create_custom_metrics("api")

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    with OTelContext("get_task", {"task_id": task_id}):
        # Your code here
        pass
"""
