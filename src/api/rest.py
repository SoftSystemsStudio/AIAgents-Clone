"""
REST API Layer - FastAPI application for the AI Agents platform.

Provides HTTP endpoints for:
- Agent management (CRUD)
- Agent execution
- Tool management
- Health checks and metrics
"""

from contextlib import asynccontextmanager
from typing import List, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel, Field

from src.config import get_config
from src.domain.models import Agent, AgentCapability, AgentStatus, ExecutionResult
from src.domain.exceptions import AgentNotFoundError, AgentExecutionError
from src.infrastructure.llm_providers import OpenAIProvider
from src.infrastructure.repositories import InMemoryAgentRepository, InMemoryToolRegistry
from src.infrastructure.observability import StructuredLogger, PrometheusObservability
from src.infrastructure.dashboard import get_dashboard_metrics
from src.application.orchestrator import AgentOrchestrator
from src.application.use_cases import (
    CreateAgentUseCase,
    ExecuteAgentUseCase,
    GetAgentUseCase,
    ListAgentsUseCase,
    DeleteAgentUseCase,
)

# Import Gmail cleanup router
from src.api.routers.gmail_cleanup import router as gmail_cleanup_router


# Global dependencies (initialized in lifespan)
_dependencies = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Initializes dependencies on startup and cleans up on shutdown.
    """
    # Startup
    config = get_config()
    
    # Initialize observability
    if config.observability.enable_metrics:
        observability = PrometheusObservability(
            log_level=config.observability.log_level,
            metrics_port=config.observability.metrics_port,
        )
    else:
        observability = StructuredLogger(log_level=config.observability.log_level)
    
    observability.log("info", "Starting AI Agents API server", {"env": config.app_env})
    
    # Initialize LLM provider
    if config.llm.openai_api_key:
        llm_provider = OpenAIProvider(api_key=config.llm.openai_api_key)
    else:
        raise ValueError("No LLM provider API key configured")
    
    # Initialize repositories
    agent_repo = InMemoryAgentRepository()
    tool_registry = InMemoryToolRegistry()
    
    # Create orchestrator
    orchestrator = AgentOrchestrator(
        llm_provider=llm_provider,
        tool_registry=tool_registry,
        agent_repository=agent_repo,
        observability=observability,
    )
    
    # Store in global dependencies
    _dependencies.update({
        "config": config,
        "observability": observability,
        "llm_provider": llm_provider,
        "agent_repo": agent_repo,
        "tool_registry": tool_registry,
        "orchestrator": orchestrator,
    })
    
    observability.log("info", "API server initialized successfully")
    
    yield
    
    # Shutdown
    observability.log("info", "Shutting down API server")


# Create FastAPI app
app = FastAPI(
    title="AI Agents Platform API",
    description="Production-grade AI agents with clean architecture",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(gmail_cleanup_router)


# Request/Response Models

class CreateAgentRequest(BaseModel):
    """Request model for creating an agent."""
    
    name: str = Field(..., description="Unique agent name")
    description: str = Field(..., description="Agent description")
    system_prompt: str = Field(..., description="System prompt defining agent behavior")
    model_provider: str = Field(..., description="LLM provider (openai, anthropic)")
    model_name: str = Field(..., description="Model identifier (e.g., gpt-4)")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(4000, gt=0, description="Maximum tokens per response")
    capabilities: List[AgentCapability] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    max_iterations: int = Field(10, gt=0, description="Maximum execution iterations")
    timeout_seconds: int = Field(300, gt=0, description="Execution timeout")


class AgentResponse(BaseModel):
    """Response model for agent data."""
    
    id: UUID
    name: str
    description: str
    model_provider: str
    model_name: str
    status: AgentStatus
    capabilities: List[AgentCapability]
    allowed_tools: List[str]
    created_at: str
    updated_at: str


class ExecuteAgentRequest(BaseModel):
    """Request model for agent execution."""
    
    user_input: str = Field(..., description="User input message")
    stream: bool = Field(False, description="Stream response in real-time")


class ExecutionResultResponse(BaseModel):
    """Response model for execution results."""
    
    agent_id: UUID
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    duration_seconds: float
    iterations: int
    estimated_cost: float
    final_status: AgentStatus


class HealthResponse(BaseModel):
    """Response model for health checks."""
    
    status: str
    version: str
    environment: str
    services: dict


# API Endpoints

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AI Agents Platform API",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Verifies that all critical services are operational.
    """
    config = _dependencies["config"]
    observability = _dependencies["observability"]
    
    # Check observability health
    obs_health = await observability.health_check()
    
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=config.app_env,
        services={
            "observability": obs_health,
            "llm_provider": "operational",
            "agent_repository": "operational",
        },
    )


@app.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED, tags=["Agents"])
async def create_agent(request: CreateAgentRequest):
    """
    Create a new agent.
    
    Creates and persists a new AI agent with the specified configuration.
    """
    agent_repo = _dependencies["agent_repo"]
    observability = _dependencies["observability"]
    
    observability.log("info", "Creating new agent", {"name": request.name})
    
    try:
        use_case = CreateAgentUseCase(agent_repo)
        agent = await use_case.execute(
            name=request.name,
            description=request.description,
            system_prompt=request.system_prompt,
            model_provider=request.model_provider,
            model_name=request.model_name,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            capabilities=request.capabilities,
            allowed_tools=request.allowed_tools,
            max_iterations=request.max_iterations,
            timeout_seconds=request.timeout_seconds,
        )
        
        observability.log("info", "Agent created successfully", {"agent_id": str(agent.id)})
        
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            model_provider=agent.model_provider,
            model_name=agent.model_name,
            status=agent.status,
            capabilities=agent.capabilities,
            allowed_tools=agent.allowed_tools,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat(),
        )
        
    except ValueError as e:
        observability.log("error", "Agent creation failed", {"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        observability.log("error", "Unexpected error creating agent", {"error": str(e)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@app.get("/agents", response_model=List[AgentResponse], tags=["Agents"])
async def list_agents(limit: int = 100, offset: int = 0):
    """
    List all agents with pagination.
    
    Returns a paginated list of all agents in the system.
    """
    agent_repo = _dependencies["agent_repo"]
    
    use_case = ListAgentsUseCase(agent_repo)
    agents = await use_case.execute(limit=limit, offset=offset)
    
    return [
        AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            model_provider=agent.model_provider,
            model_name=agent.model_name,
            status=agent.status,
            capabilities=agent.capabilities,
            allowed_tools=agent.allowed_tools,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat(),
        )
        for agent in agents
    ]


@app.get("/agents/{agent_id}", response_model=AgentResponse, tags=["Agents"])
async def get_agent(agent_id: UUID):
    """
    Get an agent by ID.
    
    Retrieves detailed information about a specific agent.
    """
    agent_repo = _dependencies["agent_repo"]
    
    try:
        use_case = GetAgentUseCase(agent_repo)
        agent = await use_case.execute_by_id(agent_id)
        
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            model_provider=agent.model_provider,
            model_name=agent.model_name,
            status=agent.status,
            capabilities=agent.capabilities,
            allowed_tools=agent.allowed_tools,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat(),
        )
        
    except AgentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")


@app.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Agents"])
async def delete_agent(agent_id: UUID):
    """
    Delete an agent.
    
    Permanently removes an agent from the system.
    """
    agent_repo = _dependencies["agent_repo"]
    observability = _dependencies["observability"]
    
    try:
        use_case = DeleteAgentUseCase(agent_repo)
        await use_case.execute(agent_id)
        
        observability.log("info", "Agent deleted", {"agent_id": str(agent_id)})
        
    except AgentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")


@app.post("/agents/{agent_id}/execute", response_model=ExecutionResultResponse, tags=["Execution"])
async def execute_agent(agent_id: UUID, request: ExecuteAgentRequest, background_tasks: BackgroundTasks):
    """
    Execute an agent with user input.
    
    Runs the agent with the provided input and returns the result.
    For long-running tasks, consider using background execution.
    """
    agent_repo = _dependencies["agent_repo"]
    orchestrator = _dependencies["orchestrator"]
    observability = _dependencies["observability"]
    
    observability.log("info", "Executing agent", {
        "agent_id": str(agent_id),
        "input_length": len(request.user_input)
    })
    
    try:
        use_case = ExecuteAgentUseCase(agent_repo, orchestrator)
        result = await use_case.execute(
            agent_id=agent_id,
            user_input=request.user_input,
        )
        
        # Record metrics
        observability.record_metric(
            "agent_execution",
            1.0,
            {"agent_id": str(agent_id), "status": "success" if result.success else "failed"},
        )
        
        if result.success:
            observability.log("info", "Agent execution completed", {
                "agent_id": str(agent_id),
                "duration": result.duration_seconds,
                "tokens": result.total_tokens,
            })
        
        return ExecutionResultResponse(
            agent_id=result.agent_id,
            success=result.success,
            output=result.output,
            error=result.error,
            total_tokens=result.total_tokens,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            duration_seconds=result.duration_seconds,
            iterations=result.iterations,
            estimated_cost=result.estimated_cost,
            final_status=result.final_status,
        )
        
    except AgentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
    except AgentExecutionError as e:
        observability.log("error", "Agent execution error", {"agent_id": str(agent_id), "error": str(e)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        observability.log("error", "Unexpected execution error", {"agent_id": str(agent_id), "error": str(e)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@app.post("/agents/{agent_id}/stream", tags=["Execution"])
async def stream_agent_response(agent_id: UUID, request: ExecuteAgentRequest):
    """
    Stream agent response in real-time.
    
    Returns a server-sent events (SSE) stream with tokens as they arrive.
    Provides better UX for chat interfaces.
    
    Note: Tool calling is not supported in streaming mode.
    """
    agent_repo = _dependencies["agent_repo"]
    orchestrator = _dependencies["orchestrator"]
    observability = _dependencies["observability"]
    
    observability.log("info", "Starting streaming execution", {
        "agent_id": str(agent_id),
        "input_length": len(request.user_input)
    })
    
    try:
        # Get agent
        use_case = GetAgentUseCase(agent_repo)
        agent = await use_case.execute_by_id(agent_id)
        
        async def event_generator():
            """Generate SSE events for streaming."""
            try:
                async for token in orchestrator.stream_agent_response(
                    agent=agent,
                    user_input=request.user_input,
                ):
                    # Send token as SSE
                    yield f"data: {token}\n\n"
                
                # Send completion marker
                yield "data: [DONE]\n\n"
                
                observability.log("info", "Streaming execution completed", {
                    "agent_id": str(agent_id),
                })
                
            except Exception as e:
                observability.log("error", "Streaming execution failed", {
                    "agent_id": str(agent_id),
                    "error": str(e)
                })
                yield f"data: [ERROR] {str(e)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )
        
    except AgentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
    except Exception as e:
        observability.log("error", "Failed to start streaming", {
            "agent_id": str(agent_id),
            "error": str(e)
        })
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """
    Get application metrics.
    
    Returns Prometheus-compatible metrics if enabled.
    """
    config = _dependencies["config"]
    
    if not config.observability.enable_metrics:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metrics not enabled")
    
    return {
        "message": "Metrics available at Prometheus endpoint",
        "endpoint": f"http://localhost:{config.observability.metrics_port}/metrics",
    }


@app.get("/api/dashboard/stats", tags=["Dashboard"])
async def get_dashboard_stats():
    """
    Get current dashboard statistics.
    
    Returns:
        System metrics, agent stats, and time series data
    """
    dashboard = get_dashboard_metrics()
    
    return {
        "system": dashboard.get_system_metrics(),
        "agents": dashboard.get_agent_stats(),
        "top_agents": dashboard.get_top_agents(by="executions", limit=5),
        "recent_executions": dashboard.get_recent_executions(limit=10),
    }


@app.get("/api/dashboard/timeseries/{metric}", tags=["Dashboard"])
async def get_time_series(metric: str, limit: int = 50):
    """
    Get time series data for a metric.
    
    Args:
        metric: Metric type (tokens, cost, executions, duration)
        limit: Maximum number of points
    
    Returns:
        Time series data points
    """
    dashboard = get_dashboard_metrics()
    
    if metric not in ["tokens", "cost", "executions", "duration"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric: {metric}. Must be one of: tokens, cost, executions, duration"
        )
    
    return {
        "metric": metric,
        "data": dashboard.get_time_series(metric, limit),
    }


@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard():
    """
    Real-time dashboard for monitoring agent activity.
    
    Shows:
    - System metrics (total executions, tokens, costs)
    - Agent performance statistics
    - Live charts (token usage, costs over time)
    - Recent execution history
    """
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agents Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        
        h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #666;
            font-size: 1.1em;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .stat-label {
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-change {
            font-size: 0.9em;
            color: #51cf66;
            margin-top: 5px;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .chart-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .chart-title {
            font-size: 1.3em;
            color: #333;
            margin-bottom: 20px;
            font-weight: 600;
        }
        
        .table-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th {
            background: #f8f9fa;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #495057;
            border-bottom: 2px solid #dee2e6;
        }
        
        td {
            padding: 15px;
            border-bottom: 1px solid #dee2e6;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        
        .badge-success {
            background: #d3f9d8;
            color: #2b8a3e;
        }
        
        .badge-danger {
            background: #ffe3e3;
            color: #c92a2a;
        }
        
        .loading {
            text-align: center;
            padding: 50px;
            color: white;
            font-size: 1.5em;
        }
        
        .refresh-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            padding: 10px 20px;
            border-radius: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            font-size: 0.9em;
            color: #667eea;
            font-weight: 600;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="refresh-indicator">
        <span class="pulse">●</span> Live Updates
    </div>
    
    <div class="container">
        <header>
            <h1>🤖 AI Agents Dashboard</h1>
            <p class="subtitle">Real-time monitoring and analytics</p>
        </header>
        
        <div class="stats-grid" id="statsGrid">
            <div class="loading">Loading statistics...</div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-card">
                <h2 class="chart-title">📊 Token Usage</h2>
                <canvas id="tokenChart"></canvas>
            </div>
            <div class="chart-card">
                <h2 class="chart-title">💰 Cost Tracking</h2>
                <canvas id="costChart"></canvas>
            </div>
        </div>
        
        <div class="table-card">
            <h2 class="chart-title">🏆 Top Performing Agents</h2>
            <table id="topAgentsTable">
                <thead>
                    <tr>
                        <th>Agent</th>
                        <th>Executions</th>
                        <th>Success Rate</th>
                        <th>Tokens Used</th>
                        <th>Total Cost</th>
                        <th>Avg Duration</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td colspan="6" style="text-align: center; color: #999;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
        
        <div class="table-card">
            <h2 class="chart-title">📝 Recent Executions</h2>
            <table id="recentExecutionsTable">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Agent</th>
                        <th>Status</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td colspan="6" style="text-align: center; color: #999;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // Chart configurations
        let tokenChart, costChart;
        
        function initCharts() {
            const chartConfig = {
                type: 'line',
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            };
            
            tokenChart = new Chart(
                document.getElementById('tokenChart'),
                {
                    ...chartConfig,
                    data: {
                        labels: [],
                        datasets: [{
                            label: 'Tokens',
                            data: [],
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            tension: 0.4,
                            fill: true
                        }]
                    }
                }
            );
            
            costChart = new Chart(
                document.getElementById('costChart'),
                {
                    ...chartConfig,
                    data: {
                        labels: [],
                        datasets: [{
                            label: 'Cost (USD)',
                            data: [],
                            borderColor: '#51cf66',
                            backgroundColor: 'rgba(81, 207, 102, 0.1)',
                            tension: 0.4,
                            fill: true
                        }]
                    },
                    options: {
                        ...chartConfig.options,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        return '$' + value.toFixed(4);
                                    }
                                }
                            }
                        }
                    }
                }
            );
        }
        
        async function fetchDashboardData() {
            try {
                const response = await fetch('/api/dashboard/stats');
                const data = await response.json();
                
                updateStats(data.system);
                updateTopAgents(data.top_agents);
                updateRecentExecutions(data.recent_executions);
                
                // Fetch time series data
                const [tokensRes, costRes] = await Promise.all([
                    fetch('/api/dashboard/timeseries/tokens?limit=30'),
                    fetch('/api/dashboard/timeseries/cost?limit=30')
                ]);
                
                const tokensData = await tokensRes.json();
                const costData = await costRes.json();
                
                updateChart(tokenChart, tokensData.data);
                updateChart(costChart, costData.data);
                
            } catch (error) {
                console.error('Failed to fetch dashboard data:', error);
            }
        }
        
        function updateStats(system) {
            const statsGrid = document.getElementById('statsGrid');
            
            const uptime = formatDuration(system.uptime_seconds);
            
            statsGrid.innerHTML = `
                <div class="stat-card">
                    <div class="stat-label">Total Executions</div>
                    <div class="stat-value">${system.total_executions.toLocaleString()}</div>
                    <div class="stat-change">↑ ${system.executions_last_hour} last hour</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Tokens</div>
                    <div class="stat-value">${(system.total_tokens / 1000).toFixed(1)}K</div>
                    <div class="stat-change">↑ ${(system.tokens_last_hour / 1000).toFixed(1)}K last hour</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Cost</div>
                    <div class="stat-value">$${system.total_cost.toFixed(2)}</div>
                    <div class="stat-change">↑ $${system.cost_last_hour.toFixed(4)} last hour</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Active Agents</div>
                    <div class="stat-value">${system.active_agents}</div>
                    <div class="stat-change">${system.total_agents} total agents</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Avg Response Time</div>
                    <div class="stat-value">${system.avg_response_time.toFixed(1)}s</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Uptime</div>
                    <div class="stat-value" style="font-size: 1.8em;">${uptime}</div>
                </div>
            `;
        }
        
        function updateTopAgents(agents) {
            const tbody = document.querySelector('#topAgentsTable tbody');
            
            if (agents.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #999;">No agents yet</td></tr>';
                return;
            }
            
            tbody.innerHTML = agents.map(agent => `
                <tr>
                    <td><strong>${agent.name}</strong></td>
                    <td>${agent.total_executions}</td>
                    <td><span class="badge ${agent.success_rate >= 90 ? 'badge-success' : 'badge-danger'}">${agent.success_rate.toFixed(1)}%</span></td>
                    <td>${agent.total_tokens.toLocaleString()}</td>
                    <td>$${agent.total_cost.toFixed(4)}</td>
                    <td>${agent.avg_duration.toFixed(2)}s</td>
                </tr>
            `).join('');
        }
        
        function updateRecentExecutions(executions) {
            const tbody = document.querySelector('#recentExecutionsTable tbody');
            
            if (executions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #999;">No executions yet</td></tr>';
                return;
            }
            
            tbody.innerHTML = executions.map(exec => {
                const time = new Date(exec.timestamp).toLocaleTimeString();
                return `
                    <tr>
                        <td>${time}</td>
                        <td>${exec.agent_name}</td>
                        <td><span class="badge ${exec.success ? 'badge-success' : 'badge-danger'}">${exec.success ? 'Success' : 'Failed'}</span></td>
                        <td>${exec.tokens}</td>
                        <td>$${exec.cost.toFixed(4)}</td>
                        <td>${exec.duration.toFixed(2)}s</td>
                    </tr>
                `;
            }).join('');
        }
        
        function updateChart(chart, data) {
            if (data.length === 0) return;
            
            chart.data.labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());
            chart.data.datasets[0].data = data.map(d => d.value);
            chart.update('none'); // No animation for smoother updates
        }
        
        function formatDuration(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            
            if (hours > 0) {
                return `${hours}h ${minutes}m`;
            }
            return `${minutes}m`;
        }
        
        // Initialize
        initCharts();
        fetchDashboardData();
        
        // Auto-refresh every 5 seconds
        setInterval(fetchDashboardData, 5000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    
    config = get_config()
    
    uvicorn.run(
        "src.api.rest:app",
        host="0.0.0.0",
        port=8000,
        reload=config.is_development(),
        log_level=config.observability.log_level.lower(),
    )
