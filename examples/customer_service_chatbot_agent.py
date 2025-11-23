"""
Customer Service Chatbot Agent

Intelligent customer service automation with natural language understanding.

Features:
- Answer common customer questions (FAQs)
- Handle product inquiries and troubleshooting
- Process returns, refunds, and complaints
- Escalate complex issues to human agents
- Track customer satisfaction
- Multi-language support
- Context-aware conversations
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional
from src.domain.models import Agent, Tool, ToolParameter
from src.infrastructure.llm_providers import OpenAIProvider
from src.infrastructure.repositories import InMemoryAgentRepository, InMemoryToolRegistry
from src.infrastructure.observability import StructuredLogger
from src.application.orchestrator import AgentOrchestrator


# Tool: Search knowledge base
def search_knowledge_base(query: str, category: Optional[str] = None) -> Dict:
    """Search the knowledge base for relevant information."""
    
    # Simulate knowledge base search
    # In production, use vector database or full-text search
    
    kb_articles = {
        "pricing": {
            "title": "Pricing Information",
            "content": "Our AI automation services start at $499/month for the Starter plan, $1,499/month for Professional, and custom pricing for Enterprise. All plans include setup, training, and ongoing support.",
            "relevant": True
        },
        "features": {
            "title": "Feature Overview",
            "content": "We offer Email Automation, Data Processing, Appointment Booking, and Customer Service Chatbots. Each solution is customized to your business needs.",
            "relevant": True
        },
        "setup_time": {
            "title": "Implementation Timeline",
            "content": "Typical setup takes 2-4 weeks from kickoff to launch. We handle all technical implementation while you provide business requirements.",
            "relevant": True
        },
        "support": {
            "title": "Customer Support",
            "content": "24/7 email support for all plans. Professional and Enterprise plans include priority phone support and dedicated account manager.",
            "relevant": True
        }
    }
    
    # Simple keyword matching
    query_lower = query.lower()
    results = []
    
    for key, article in kb_articles.items():
        if any(word in query_lower for word in key.split("_")):
            results.append(article)
    
    if not results:
        results = [kb_articles["features"]]  # Default fallback
    
    return {
        "query": query,
        "category": category,
        "results_found": len(results),
        "articles": results,
        "search_timestamp": datetime.now().isoformat()
    }


# Tool: Check order status
def check_order_status(order_id: str) -> Dict:
    """Check the status of a customer order."""
    
    # Simulate order lookup
    # In production, query actual order management system
    
    return {
        "order_id": order_id,
        "status": "in_progress",
        "ordered_date": "2024-01-15",
        "estimated_completion": "2024-02-05",
        "current_stage": "Development",
        "progress_percentage": 65,
        "next_milestone": "Testing phase starts Jan 30",
        "contact_person": "Sarah Johnson, Account Manager",
        "last_updated": datetime.now().isoformat()
    }


# Tool: Create support ticket
def create_support_ticket(
    customer_name: str,
    customer_email: str,
    issue_type: str,
    priority: str,
    description: str
) -> Dict:
    """Create a support ticket for complex issues."""
    
    ticket_id = f"TK-{datetime.now().strftime('%Y%m%d')}-{hash(customer_email) % 10000:04d}"
    
    return {
        "ticket_id": ticket_id,
        "status": "open",
        "customer": {
            "name": customer_name,
            "email": customer_email
        },
        "issue": {
            "type": issue_type,
            "priority": priority,
            "description": description
        },
        "assigned_to": "Support Team",
        "sla_response_time": "4 hours" if priority == "high" else "24 hours",
        "created_at": datetime.now().isoformat(),
        "tracking_url": f"https://support.softsystems.studio/ticket/{ticket_id}",
        "email_confirmation_sent": True
    }


# Tool: Escalate to human
def escalate_to_human(
    reason: str,
    customer_context: str,  # Changed from Dict to str
    urgency: str = "medium"
) -> Dict:
    """Escalate conversation to a human agent."""
    
    return {
        "escalated": True,
        "reason": reason,
        "urgency": urgency,
        "estimated_wait_time": "2-5 minutes" if urgency == "high" else "10-15 minutes",
        "customer_notified": True,
        "human_agent_alerted": True,
        "context_transferred": True,
        "conversation_history_saved": True,
        "timestamp": datetime.now().isoformat()
    }


# Tool: Process refund request
def process_refund_request(
    order_id: str,
    reason: str,
    amount: Optional[float] = None
) -> Dict:
    """Process a customer refund request."""
    
    return {
        "refund_id": f"REF-{datetime.now().strftime('%Y%m%d')}-{hash(order_id) % 10000:04d}",
        "order_id": order_id,
        "status": "approved",
        "reason": reason,
        "refund_amount": amount or 499.00,
        "processing_time": "3-5 business days",
        "refund_method": "Original payment method",
        "approval_required": amount and amount > 1000,
        "customer_notified": True,
        "processed_at": datetime.now().isoformat()
    }


# Tool: Track customer satisfaction
def track_customer_satisfaction(
    conversation_id: str,
    satisfaction_score: int,
    feedback: Optional[str] = None
) -> Dict:
    """Track customer satisfaction after interaction."""
    
    return {
        "conversation_id": conversation_id,
        "satisfaction_score": satisfaction_score,
        "rating": "Excellent" if satisfaction_score >= 4 else "Good" if satisfaction_score >= 3 else "Needs Improvement",
        "feedback": feedback,
        "recorded_at": datetime.now().isoformat(),
        "follow_up_required": satisfaction_score < 3,
        "manager_notified": satisfaction_score < 2
    }


# Tool: Get account information
def get_account_information(email: str) -> Dict:
    """Retrieve customer account information."""
    
    return {
        "email": email,
        "account_status": "active",
        "customer_since": "2023-06-15",
        "current_plan": "Professional",
        "subscription_status": "active",
        "next_billing_date": "2024-02-15",
        "total_services": 3,
        "services": [
            "Email Automation",
            "Appointment Booking",
            "Data Processing"
        ],
        "payment_method": "Visa ending in 4242",
        "support_level": "Priority",
        "account_manager": "Sarah Johnson"
    }


async def main():
    """Run the Customer Service Chatbot Agent."""
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Please set OPENAI_API_KEY environment variable")
        return
    
    print("=" * 80)
    print("💬 CUSTOMER SERVICE CHATBOT AGENT")
    print("=" * 80)
    print()
    
    # Initialize infrastructure
    llm_provider = OpenAIProvider(api_key=api_key)
    agent_repo = InMemoryAgentRepository()
    tool_registry = InMemoryToolRegistry()
    logger = StructuredLogger()
    
    # Register tools
    print("🛠️  Registering tools...")
    
    kb_tool = Tool(
        name="search_knowledge_base",
        description="Search the knowledge base for answers to customer questions (pricing, features, setup, support, etc.)",
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="The customer's question or search query",
                required=True
            ),
            ToolParameter(
                name="category",
                type="string",
                description="Optional category: pricing, features, support, technical, billing",
                required=False
            )
        ],
        handler_module="examples.customer_service_chatbot_agent",
        handler_function="search_knowledge_base"
    )
    tool_registry.register_tool(kb_tool)
    
    order_tool = Tool(
        name="check_order_status",
        description="Check the current status and progress of a customer's order",
        parameters=[
            ToolParameter(
                name="order_id",
                type="string",
                description="The order ID to look up",
                required=True
            )
        ],
        handler_module="examples.customer_service_chatbot_agent",
        handler_function="check_order_status"
    )
    tool_registry.register_tool(order_tool)
    
    account_tool = Tool(
        name="get_account_information",
        description="Retrieve customer account details, subscription info, and services",
        parameters=[
            ToolParameter(
                name="email",
                type="string",
                description="Customer's email address",
                required=True
            )
        ],
        handler_module="examples.customer_service_chatbot_agent",
        handler_function="get_account_information"
    )
    tool_registry.register_tool(account_tool)
    
    ticket_tool = Tool(
        name="create_support_ticket",
        description="Create a support ticket for complex technical issues that require human assistance",
        parameters=[
            ToolParameter(
                name="customer_name",
                type="string",
                description="Customer's name",
                required=True
            ),
            ToolParameter(
                name="customer_email",
                type="string",
                description="Customer's email",
                required=True
            ),
            ToolParameter(
                name="issue_type",
                type="string",
                description="Type: technical, billing, feature_request, bug_report",
                required=True
            ),
            ToolParameter(
                name="priority",
                type="string",
                description="Priority: low, medium, high, urgent",
                required=True
            ),
            ToolParameter(
                name="description",
                type="string",
                description="Detailed issue description",
                required=True
            )
        ],
        handler_module="examples.customer_service_chatbot_agent",
        handler_function="create_support_ticket"
    )
    tool_registry.register_tool(ticket_tool)
    
    escalate_tool = Tool(
        name="escalate_to_human",
        description="Escalate the conversation to a human agent for complex or sensitive issues",
        parameters=[
            ToolParameter(
                name="reason",
                type="string",
                description="Why escalation is needed",
                required=True
            ),
            ToolParameter(
                name="customer_context",
                type="string",
                description="Customer information and conversation context (JSON string)",
                required=True
            ),
            ToolParameter(
                name="urgency",
                type="string",
                description="Urgency level: low, medium, high",
                required=False,
                default="medium"
            )
        ],
        handler_module="examples.customer_service_chatbot_agent",
        handler_function="escalate_to_human"
    )
    tool_registry.register_tool(escalate_tool)
    
    refund_tool = Tool(
        name="process_refund_request",
        description="Process a customer refund or cancellation request",
        parameters=[
            ToolParameter(
                name="order_id",
                type="string",
                description="Order ID for refund",
                required=True
            ),
            ToolParameter(
                name="reason",
                type="string",
                description="Reason for refund request",
                required=True
            ),
            ToolParameter(
                name="amount",
                type="number",
                description="Optional refund amount (defaults to full order amount)",
                required=False
            )
        ],
        handler_module="examples.customer_service_chatbot_agent",
        handler_function="process_refund_request"
    )
    tool_registry.register_tool(refund_tool)
    
    satisfaction_tool = Tool(
        name="track_customer_satisfaction",
        description="Record customer satisfaction score and feedback after interaction",
        parameters=[
            ToolParameter(
                name="conversation_id",
                type="string",
                description="Unique conversation ID",
                required=True
            ),
            ToolParameter(
                name="satisfaction_score",
                type="integer",
                description="Score from 1 (poor) to 5 (excellent)",
                required=True
            ),
            ToolParameter(
                name="feedback",
                type="string",
                description="Optional customer feedback comments",
                required=False
            )
        ],
        handler_module="examples.customer_service_chatbot_agent",
        handler_function="track_customer_satisfaction"
    )
    tool_registry.register_tool(satisfaction_tool)
    
    tools = [kb_tool, order_tool, account_tool, ticket_tool, escalate_tool, refund_tool, satisfaction_tool]
    
    print("🛠️  Registered Tools:")
    for tool in tools:
        print(f"   • {tool.name}")
    print()
    
    # Initialize orchestrator
    orchestrator = AgentOrchestrator(
        llm_provider=llm_provider,
        agent_repository=agent_repo,
        tool_registry=tool_registry,
        observability=logger
    )
    
    # Create agent
    agent = Agent(
        name="Customer Support Assistant",
        description="Intelligent customer service chatbot with natural language understanding and multi-tool capabilities",
        system_prompt="""You are a helpful, empathetic, and professional customer support assistant for Soft Systems Studio.

Your responsibilities:
1. Answer customer questions using the knowledge base
2. Check order status and account information
3. Process refund and cancellation requests
4. Create support tickets for technical issues
5. Escalate complex or sensitive issues to human agents
6. Track customer satisfaction after interactions
7. Provide clear, concise, and friendly responses

Guidelines:
- Always greet customers warmly
- Search the knowledge base first for answers
- Be empathetic, especially with complaints
- Explain processes clearly and set expectations
- Offer proactive help and next steps
- Apologize sincerely when issues occur
- Create tickets for technical problems
- Escalate when you're unsure or the issue is sensitive
- End conversations by asking if there's anything else you can help with
- Track satisfaction before ending

For pricing questions: Search KB, provide clear pricing, offer consultation
For technical issues: Create support ticket with details
For complaints: Apologize, acknowledge issue, offer solution or escalate
For refunds: Process if within policy, explain timeline, confirm
For general questions: Search KB, provide helpful answer, offer more help

Escalate to human when:
- Customer is angry or frustrated
- Issue is complex or technical
- Request is outside your capability
- Customer specifically asks for a human
- Refund amount exceeds $1000

Soft Systems Studio Services:
- Email & Social Media Automation
- Data Entry & Processing
- Appointment & Booking Automation
- Customer Service Chatbots
- Custom AI Solutions

Tone: Friendly, professional, empathetic, solution-oriented""",
        model_provider="openai",
        model_name="gpt-4o",
        temperature=0.7,  # Balanced for natural conversation
        allowed_tools=[tool.name for tool in tools],
        max_iterations=5,
        timeout_seconds=60
    )
    
    await agent_repo.save(agent)
    
    print(f"✅ Created agent: {agent.name}")
    print(f"   Model: {agent.model_name}")
    print(f"   Temperature: {agent.temperature}")
    print(f"   Tools: {len(agent.allowed_tools)}")
    print()
    
    # Test scenarios
    scenarios = [
        {
            "title": "Pricing Inquiry",
            "task": "Hi! I'm interested in your AI automation services. Can you tell me about your pricing plans and what's included? I run a small e-commerce business with about 100 customers."
        },
        {
            "title": "Order Status Check",
            "task": "Hello, I ordered your email automation service 2 weeks ago (Order #ORD-20240115-001) and wanted to check on the status. When will it be ready?"
        },
        {
            "title": "Technical Issue / Support Ticket",
            "task": "I'm having trouble with my chatbot integration. It's not responding to customer messages on my website. This is urgent as it's affecting my business. Can you help?"
        },
        {
            "title": "Complaint / Refund Request",
            "task": "I'm very disappointed with the service. The email automation isn't working as promised and I've lost several leads. I want a refund for my $499 subscription."
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print("=" * 80)
        print(f"💬 Scenario {i}: {scenario['title']}")
        print("=" * 80)
        print(f"\n👤 Customer: {scenario['task']}\n")
        
        result = await orchestrator.execute_agent(
            agent=agent,
            user_input=scenario['task']
        )
        
        if result.success:
            print(f"🤖 Support Agent:\n")
            print(result.output)
            print()
            
            print(f"📊 Execution Metrics:")
            print(f"   • Tokens: {result.total_tokens}")
            print(f"   • Duration: {result.duration_seconds:.2f}s")
            print(f"   • Iterations: {result.iterations}")
            print(f"   • Cost: ${result.estimated_cost:.4f}")
            print()
        else:
            print(f"❌ Error: {result.error}\n")
    
    print("=" * 80)
    print("✨ Customer Service Chatbot Demo Complete!")
    print()
    print("💡 Integration Options:")
    print("   • Website widget (JavaScript embed)")
    print("   • Facebook Messenger integration")
    print("   • WhatsApp Business API")
    print("   • Slack for internal support")
    print("   • Zendesk / Intercom integration")
    print("   • Email support automation")
    print("   • SMS support via Twilio")
    print()
    print("🎯 Key Features:")
    print("   • 24/7 instant responses")
    print("   • Knowledge base search")
    print("   • Order tracking")
    print("   • Refund processing")
    print("   • Smart escalation to humans")
    print("   • Multi-language support")
    print("   • Satisfaction tracking")
    print("   • Context-aware conversations")
    print()
    print("📈 Business Impact:")
    print("   • Reduce support costs by 60-80%")
    print("   • Instant response time (vs hours)")
    print("   • Handle 10x more inquiries")
    print("   • 24/7 availability")
    print("   • Consistent, high-quality responses")
    print("   • Free human agents for complex issues")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
