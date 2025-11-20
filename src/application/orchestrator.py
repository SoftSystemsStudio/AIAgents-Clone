"""
Agent Orchestrator - Core execution engine.

Orchestrates agent execution, tool calls, and conversation flow.
"""

import asyncio
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import UUID

from src.domain.exceptions import (
    AgentExecutionError,
    AgentTimeoutError,
    ToolPermissionError,
)
from src.domain.interfaces import (
    IAgentRepository,
    ILLMProvider,
    IObservabilityService,
    IToolRegistry,
)
from src.domain.models import (
    Agent,
    AgentCapability,
    AgentStatus,
    ExecutionResult,
    Message,
    MessageRole,
)
from src.infrastructure.dashboard import get_dashboard_metrics


class AgentOrchestrator:
    """
    Orchestrates agent execution with tool calling and iteration management.
    
    This is the core execution engine that:
    1. Manages agent conversation flow
    2. Handles LLM calls and tool invocations
    3. Enforces constraints (timeouts, max iterations)
    4. Tracks metrics and costs
    
    RISK: Long-running agents can consume significant resources.
    Mitigation: Enforced timeouts and iteration limits.
    
    TODO: Add checkpoint/resume capability for long-running tasks
    TODO: Add parallel tool execution when tools are independent
    """

    def __init__(
        self,
        llm_provider: ILLMProvider,
        tool_registry: IToolRegistry,
        agent_repository: IAgentRepository,
        observability: Optional[IObservabilityService] = None,
    ):
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry
        self.agent_repository = agent_repository
        self.observability = observability

    async def execute_agent(
        self,
        agent: Agent,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute an agent with user input.
        
        This orchestrates the full agent execution cycle:
        - Add user message to history
        - Loop: LLM call → Tool execution → LLM call (until done or limit)
        - Return execution result with metrics
        
        Args:
            agent: Agent to execute
            user_input: User's input message
            context: Optional context (e.g., from RAG)
            
        Returns:
            ExecutionResult with output and metrics
        """
        start_time = datetime.utcnow()
        total_tokens = 0
        prompt_tokens = 0
        completion_tokens = 0
        iteration_count = 0
        
        # Mark agent as active in dashboard
        dashboard = get_dashboard_metrics()
        dashboard.start_execution(str(agent.id))

        try:
            # Update agent status
            agent.update_status(AgentStatus.RUNNING)
            await self.agent_repository.save(agent)

            # Log execution start
            if self.observability:
                self.observability.log(
                    "info",
                    f"Starting agent execution: {agent.name}",
                    {"agent_id": str(agent.id), "user_input": user_input},
                )

            # Add user message
            user_message = Message(role=MessageRole.USER, content=user_input)
            agent.add_message(user_message)

            # Get available tools for this agent
            tools = self._get_agent_tools(agent)
            tool_schemas = [tool.to_llm_schema() for tool in tools] if tools else None

            # Execution loop with timeout
            try:
                result = await asyncio.wait_for(
                    self._execution_loop(
                        agent,
                        tools,
                        tool_schemas,
                        total_tokens,
                        prompt_tokens,
                        completion_tokens,
                        iteration_count,
                    ),
                    timeout=agent.timeout_seconds,
                )
                
                # Unpack results
                final_output, total_tokens, prompt_tokens, completion_tokens, iteration_count = result

            except asyncio.TimeoutError:
                agent.update_status(AgentStatus.FAILED)
                await self.agent_repository.save(agent)
                raise AgentTimeoutError(str(agent.id), agent.timeout_seconds)

            # Calculate metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            estimated_cost = self._estimate_cost(
                agent.model_provider, agent.model_name, prompt_tokens, completion_tokens
            )

            # Update agent status
            agent.update_status(AgentStatus.COMPLETED)
            await self.agent_repository.save(agent)

            # Log completion
            if self.observability:
                self.observability.log(
                    "info",
                    f"Agent execution completed: {agent.name}",
                    {
                        "agent_id": str(agent.id),
                        "duration": duration,
                        "iterations": iteration_count,
                        "total_tokens": total_tokens,
                    },
                )
                self.observability.record_metric(
                    "agent_execution_duration",
                    duration,
                    {"agent_id": str(agent.id)},
                )
            
            # Record to dashboard
            dashboard = get_dashboard_metrics()
            dashboard.record_execution(
                agent_id=str(agent.id),
                agent_name=agent.name,
                tokens=total_tokens,
                cost=estimated_cost,
                duration=duration,
                success=True,
            )
            dashboard.end_execution(str(agent.id))

            return ExecutionResult(
                agent_id=agent.id,
                success=True,
                output=final_output,
                total_tokens=total_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_seconds=duration,
                iterations=iteration_count,
                estimated_cost=estimated_cost,
                final_status=AgentStatus.COMPLETED,
            )

        except Exception as e:
            # Handle errors
            agent.update_status(AgentStatus.FAILED)
            await self.agent_repository.save(agent)

            duration = (datetime.utcnow() - start_time).total_seconds()
            estimated_cost = self._estimate_cost(
                agent.model_provider, agent.model_name, prompt_tokens, completion_tokens
            )

            if self.observability:
                self.observability.log(
                    "error",
                    f"Agent execution failed: {agent.name}",
                    {"agent_id": str(agent.id), "error": str(e)},
                )
            
            # Record failure to dashboard
            dashboard = get_dashboard_metrics()
            dashboard.record_execution(
                agent_id=str(agent.id),
                agent_name=agent.name,
                tokens=total_tokens,
                cost=estimated_cost,
                duration=duration,
                success=False,
            )
            dashboard.end_execution(str(agent.id))

            return ExecutionResult(
                agent_id=agent.id,
                success=False,
                error=str(e),
                duration_seconds=duration,
                iterations=iteration_count,
                total_tokens=total_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                final_status=AgentStatus.FAILED,
            )

    async def _execution_loop(
        self,
        agent: Agent,
        tools: List[Any],
        tool_schemas: Optional[List[Dict[str, Any]]],
        total_tokens: int,
        prompt_tokens: int,
        completion_tokens: int,
        iteration_count: int,
    ) -> tuple:
        """
        Main execution loop: LLM → Tools → LLM → ...
        
        Continues until:
        - LLM provides final answer (no tool calls)
        - Max iterations reached
        - Error occurs
        """
        final_output = None

        for iteration in range(agent.max_iterations):
            iteration_count += 1

            # Call LLM
            response_message = await self.llm_provider.generate_completion(
                messages=agent.conversation_history,
                model=agent.model_name,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens,
                tools=tool_schemas,
            )

            # Track tokens
            metadata = response_message.metadata
            total_tokens += metadata.get("total_tokens", 0)
            prompt_tokens += metadata.get("prompt_tokens", 0)
            completion_tokens += metadata.get("completion_tokens", 0)

            # Add assistant message to history
            agent.add_message(response_message)

            # Check if agent wants to call tools
            if response_message.tool_calls:
                # Execute tool calls
                for tool_call in response_message.tool_calls:
                    tool_result = await self._execute_tool_call(agent, tool_call, tools)
                    
                    # Add tool result to conversation
                    tool_message = Message(
                        role=MessageRole.TOOL,
                        content=str(tool_result),
                        tool_call_id=tool_call["id"],
                    )
                    agent.add_message(tool_message)

                # Continue loop to let LLM process tool results
                continue

            else:
                # No tool calls - agent has final answer
                final_output = response_message.content
                break

        # If we exhausted iterations without final answer
        if final_output is None:
            final_output = agent.conversation_history[-1].content

        return final_output, total_tokens, prompt_tokens, completion_tokens, iteration_count

    async def _execute_tool_call(
        self,
        agent: Agent,
        tool_call: Dict[str, Any],
        tools: List[Any],
    ) -> Dict[str, Any]:
        """
        Execute a single tool call.
        
        Validates permissions and invokes the tool.
        """
        import json

        function_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])

        # Get tool definition
        tool = self.tool_registry.get_tool(function_name)
        if not tool:
            return {"error": f"Tool {function_name} not found"}

        # Check permissions
        if tool.required_capability:
            if tool.required_capability not in agent.capabilities:
                raise ToolPermissionError(
                    function_name,
                    str(agent.id),
                    tool.required_capability.value,
                )

        # Log tool invocation
        if self.observability:
            self.observability.log(
                "info",
                f"Invoking tool: {function_name}",
                {"agent_id": str(agent.id), "tool": function_name, "args": arguments},
            )

        # Execute tool
        try:
            result = await self.tool_registry.invoke_tool(function_name, arguments)
            return result
        except Exception as e:
            return {"error": str(e)}

    def _get_agent_tools(self, agent: Agent) -> List[Any]:
        """Get tools available to this agent based on capabilities and allowed list."""
        if not agent.allowed_tools:
            return []

        tools = []
        for tool_name in agent.allowed_tools:
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                # Check if agent has required capability
                if tool.required_capability:
                    if tool.required_capability in agent.capabilities:
                        tools.append(tool)
                else:
                    tools.append(tool)

        return tools

    def _estimate_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Estimate cost in USD based on token usage.
        
        Pricing as of 2024 (update regularly):
        - GPT-4: $0.03/1K prompt, $0.06/1K completion
        - GPT-3.5-turbo: $0.001/1K prompt, $0.002/1K completion
        - Claude-3-opus: $0.015/1K prompt, $0.075/1K completion
        
        TODO: Move pricing to configuration
        TODO: Track actual costs from API responses
        """
        pricing = {
            "openai": {
                "gpt-4": (0.03, 0.06),
                "gpt-4-turbo": (0.01, 0.03),
                "gpt-3.5-turbo": (0.001, 0.002),
            },
            "anthropic": {
                "claude-3-opus": (0.015, 0.075),
                "claude-3-sonnet": (0.003, 0.015),
            },
        }

        if provider in pricing and model in pricing[provider]:
            prompt_price, completion_price = pricing[provider][model]
            return (prompt_tokens / 1000 * prompt_price) + (
                completion_tokens / 1000 * completion_price
            )

        return 0.0

    async def stream_agent_response(
        self,
        agent: Agent,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream agent response in real-time.
        
        Similar to execute_agent but yields tokens as they arrive.
        
        Note: Tool calling is not supported in streaming mode.
        Returns only the first LLM response without tool execution.
        
        Args:
            agent: Agent to execute
            user_input: User's input message
            context: Optional context
            
        Yields:
            Response tokens as they arrive
        """
        try:
            # Update agent status
            agent.update_status(AgentStatus.RUNNING)
            await self.agent_repository.save(agent)

            # Log execution start
            if self.observability:
                self.observability.log(
                    "info",
                    f"Starting streaming agent execution: {agent.name}",
                    {"agent_id": str(agent.id), "user_input": user_input},
                )

            # Add user message
            user_message = Message(role=MessageRole.USER, content=user_input)
            agent.add_message(user_message)

            # Stream LLM response (no tool support)
            full_response = []
            async for token in self.llm_provider.stream_completion(
                messages=agent.conversation_history,
                model=agent.model_name,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens,
            ):
                full_response.append(token)
                yield token

            # Add complete response to history
            response_content = "".join(full_response)
            response_message = Message(
                role=MessageRole.ASSISTANT,
                content=response_content,
            )
            agent.add_message(response_message)

            # Update agent status
            agent.update_status(AgentStatus.COMPLETED)
            await self.agent_repository.save(agent)

            if self.observability:
                self.observability.log(
                    "info",
                    f"Streaming agent execution completed: {agent.name}",
                    {"agent_id": str(agent.id)},
                )

        except Exception as e:
            agent.update_status(AgentStatus.FAILED)
            await self.agent_repository.save(agent)

            if self.observability:
                self.observability.log(
                    "error",
                    f"Streaming agent execution failed: {agent.name}",
                    {"agent_id": str(agent.id), "error": str(e)},
                )
            raise AgentExecutionError(str(agent.id), str(e))
