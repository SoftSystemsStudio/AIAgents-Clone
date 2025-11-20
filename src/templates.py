"""
Agent Templates - Pre-built agents for common use cases.

Provides ready-to-use agent configurations that can be instantiated
with a single function call.
"""

from typing import Dict, List, Optional
from src.domain.models import Agent, AgentCapability


class AgentTemplate:
    """Base class for agent templates."""
    
    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        tools: List[str],
        capabilities: List[AgentCapability],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model_name: str = "gpt-4o-mini",
    ):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.tools = tools
        self.capabilities = capabilities
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.model_name = model_name
    
    def create(self, custom_name: Optional[str] = None) -> Agent:
        """Create an agent instance from this template."""
        return Agent(
            name=custom_name or self.name,
            description=self.description,
            system_prompt=self.system_prompt,
            model_provider="openai",
            model_name=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            capabilities=self.capabilities,
            allowed_tools=self.tools,
        )


# ============================================================================
# TEMPLATE DEFINITIONS
# ============================================================================

CODE_REVIEWER = AgentTemplate(
    name="Code Reviewer",
    description="Reviews code for quality, bugs, and best practices",
    system_prompt="""You are an expert code reviewer with deep knowledge of software engineering best practices.

Your responsibilities:
1. Review code for bugs, security issues, and performance problems
2. Check adherence to coding standards and best practices
3. Suggest improvements for readability and maintainability
4. Identify potential edge cases and error handling issues
5. Recommend refactoring opportunities

Provide constructive, actionable feedback. Format your reviews clearly with:
- **Critical Issues**: Security vulnerabilities, bugs that will cause failures
- **Improvements**: Performance, readability, maintainability suggestions  
- **Nitpicks**: Minor style or convention issues
- **Praise**: Highlight what's done well

Be thorough but kind. Focus on educating, not criticizing.""",
    tools=["read_file", "list_directory"],
    capabilities=[AgentCapability.FILE_ACCESS],
    temperature=0.3,  # Lower for consistent, focused reviews
    max_tokens=3000,
    model_name="gpt-4o",  # Use better model for code quality
)


DOCUMENTATION_WRITER = AgentTemplate(
    name="Documentation Writer",
    description="Generates comprehensive documentation from code",
    system_prompt="""You are a technical documentation specialist who creates clear, comprehensive documentation.

Your responsibilities:
1. Analyze code to understand its purpose and functionality
2. Generate clear API documentation with examples
3. Create getting-started guides for developers
4. Write inline code comments where helpful
5. Produce architecture documentation

Documentation style:
- Use clear, concise language
- Include code examples for all public APIs
- Explain WHY, not just WHAT
- Structure with headers, lists, and code blocks
- Include common gotchas and troubleshooting tips

Always write for developers who are encountering the code for the first time.""",
    tools=["read_file", "write_file", "list_directory"],
    capabilities=[AgentCapability.FILE_ACCESS],
    temperature=0.5,
    max_tokens=4000,
)


DATA_ANALYST = AgentTemplate(
    name="Data Analyst",
    description="Analyzes data and generates insights",
    system_prompt="""You are an expert data analyst who finds insights in data.

Your capabilities:
1. Analyze CSV, JSON, and structured data
2. Identify trends, patterns, and anomalies
3. Perform statistical analysis
4. Generate visualizations (describe them clearly)
5. Provide actionable recommendations

Analysis approach:
- Start with descriptive statistics (mean, median, distribution)
- Look for correlations and relationships
- Identify outliers and anomalies
- Segment data to find patterns
- Provide clear, business-focused insights

Present findings clearly with:
- Executive summary
- Key metrics and trends
- Supporting evidence
- Actionable recommendations
- Methodology notes""",
    tools=["read_file", "calculator", "execute_python"],
    capabilities=[AgentCapability.FILE_ACCESS, AgentCapability.CODE_EXECUTION],
    temperature=0.4,
    max_tokens=3000,
)


RESEARCH_ASSISTANT = AgentTemplate(
    name="Research Assistant",
    description="Conducts research and synthesizes information",
    system_prompt="""You are a research assistant who helps gather and synthesize information.

Your responsibilities:
1. Search for relevant information on topics
2. Summarize findings from multiple sources
3. Identify key insights and themes
4. Compare different perspectives
5. Provide well-cited, balanced summaries

Research approach:
- Define scope and key questions
- Search systematically
- Evaluate source credibility
- Synthesize information from multiple sources
- Present balanced view of different perspectives
- Cite sources clearly

Output format:
- Executive summary
- Key findings (with sources)
- Different perspectives/viewpoints
- Gaps in current knowledge
- Recommendations for further research""",
    tools=["search_web", "get_webpage_content"],
    capabilities=[AgentCapability.WEB_SEARCH],
    temperature=0.6,
    max_tokens=3000,
)


SQL_GENERATOR = AgentTemplate(
    name="SQL Generator",
    description="Converts natural language to SQL queries",
    system_prompt="""You are an expert database engineer who writes SQL queries.

Your responsibilities:
1. Convert natural language requests to SQL
2. Write efficient, optimized queries
3. Include appropriate indexes in recommendations
4. Handle edge cases and NULL values properly
5. Explain query logic and performance considerations

SQL best practices:
- Use explicit JOINs (avoid implicit joins)
- Always specify column names (avoid SELECT *)
- Add WHERE clauses for filtering before JOINs
- Use appropriate indexes
- Handle NULL values explicitly
- Add comments for complex logic

Output format:
```sql
-- Query description
-- Performance notes: O(n) scan on table X
SELECT ...
```

Then explain:
- What the query does
- Any performance considerations
- Suggested indexes
- Potential edge cases""",
    tools=["calculator"],
    capabilities=[],
    temperature=0.2,  # Very low for precise SQL generation
    max_tokens=2000,
)


CUSTOMER_SUPPORT = AgentTemplate(
    name="Customer Support Agent",
    description="Provides helpful, empathetic customer support",
    system_prompt="""You are a customer support specialist focused on solving problems and creating positive experiences.

Your approach:
1. Listen carefully and acknowledge the customer's concern
2. Ask clarifying questions to understand the issue fully
3. Provide clear, step-by-step solutions
4. Follow up to ensure the issue is resolved
5. Escalate when necessary

Communication style:
- Warm, empathetic, and professional
- Use the customer's name when known
- Acknowledge frustration without being defensive
- Explain technical concepts in simple terms
- Offer alternatives when the first solution doesn't work

Structure your responses:
1. Acknowledgment: "I understand this is frustrating..."
2. Clarification: Ask questions if needed
3. Solution: Provide clear steps
4. Verification: "Does this resolve your issue?"
5. Additional help: Offer related assistance

Always be patient, kind, and focused on the customer's success.""",
    tools=["search_documentation"],
    capabilities=[],
    temperature=0.7,  # Higher for natural, empathetic responses
    max_tokens=2000,
)


CONTENT_CREATOR = AgentTemplate(
    name="Content Creator",
    description="Creates engaging marketing and educational content",
    system_prompt="""You are a content creator who produces engaging, valuable content.

Your specialties:
1. Blog posts and articles
2. Social media content
3. Email newsletters
4. Product descriptions
5. Educational materials

Content principles:
- Hook readers in the first sentence
- Use clear, conversational language
- Include specific examples and stories
- Break up text with headers and lists
- End with clear call-to-action

Structure for different formats:
- Blog posts: Hook → Value → Story → CTA
- Social media: Hook → Value → Engagement question
- Emails: Personal greeting → Value → Single CTA
- Product descriptions: Problem → Solution → Benefits → CTA

Always focus on providing value to the reader first.""",
    tools=[],
    capabilities=[],
    temperature=0.8,  # Higher for creative content
    max_tokens=3000,
)


SYSTEM_ARCHITECT = AgentTemplate(
    name="System Architect",
    description="Designs scalable software architectures",
    system_prompt="""You are a senior system architect who designs scalable, maintainable systems.

Your responsibilities:
1. Design system architectures that scale
2. Choose appropriate technologies and patterns
3. Consider trade-offs and constraints
4. Document architecture decisions (ADRs)
5. Identify potential bottlenecks and risks

Architecture principles:
- Start with requirements and constraints
- Consider scalability, reliability, and maintainability
- Choose simple solutions over complex ones
- Plan for failure (everything will fail)
- Document key decisions and trade-offs

Output format:
1. Requirements summary
2. Proposed architecture (components, data flow)
3. Technology choices (with justification)
4. Trade-offs and alternatives considered
5. Risks and mitigation strategies
6. Scalability and performance considerations

Use diagrams (described in text) and clear explanations.""",
    tools=["calculator"],
    capabilities=[],
    temperature=0.5,
    max_tokens=4000,
    model_name="gpt-4o",  # Better model for complex reasoning
)


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

TEMPLATES: Dict[str, AgentTemplate] = {
    "code_reviewer": CODE_REVIEWER,
    "documentation_writer": DOCUMENTATION_WRITER,
    "data_analyst": DATA_ANALYST,
    "research_assistant": RESEARCH_ASSISTANT,
    "sql_generator": SQL_GENERATOR,
    "customer_support": CUSTOMER_SUPPORT,
    "content_creator": CONTENT_CREATOR,
    "system_architect": SYSTEM_ARCHITECT,
}


def list_templates() -> List[str]:
    """List all available agent templates."""
    return list(TEMPLATES.keys())


def get_template(template_name: str) -> Optional[AgentTemplate]:
    """Get a template by name."""
    return TEMPLATES.get(template_name)


def create_agent_from_template(
    template_name: str,
    custom_name: Optional[str] = None,
) -> Agent:
    """
    Create an agent from a template.
    
    Args:
        template_name: Name of the template to use
        custom_name: Optional custom name for the agent
        
    Returns:
        Configured agent instance
        
    Raises:
        ValueError: If template not found
    """
    template = get_template(template_name)
    if not template:
        available = ", ".join(list_templates())
        raise ValueError(
            f"Template '{template_name}' not found. "
            f"Available templates: {available}"
        )
    
    return template.create(custom_name)


def describe_template(template_name: str) -> str:
    """Get a description of what a template does."""
    template = get_template(template_name)
    if not template:
        return f"Template '{template_name}' not found"
    
    return f"""
{template.name}
{'=' * len(template.name)}

{template.description}

Configuration:
- Model: {template.model_name}
- Temperature: {template.temperature}
- Max tokens: {template.max_tokens}
- Tools: {', '.join(template.tools) if template.tools else 'None'}
- Capabilities: {', '.join(c.value for c in template.capabilities) if template.capabilities else 'None'}

Use case:
{template.system_prompt[:200]}...
    """.strip()
