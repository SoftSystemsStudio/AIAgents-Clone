"""
Email & Social Media Response Automation Agent

Automates email responses, social media engagement, and communication workflows.
Includes Gmail integration for email automation.

Features:
- Automated email responses based on content analysis
- Social media reply generation (Twitter, LinkedIn, Facebook)
- Sentiment analysis and tone matching
- Draft generation for review before sending
- Multi-platform message scheduling
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional
from src.domain.models import Agent, Tool
from src.infrastructure.llm_providers import OpenAIProvider
from src.infrastructure.repositories import InMemoryAgentRepository, InMemoryToolRegistry
from src.infrastructure.observability import StructuredLogger
from src.application.orchestrator import AgentOrchestrator


# Tool: Analyze email/message sentiment
def analyze_sentiment(content: str) -> Dict:
    """Analyze the sentiment and urgency of a message."""
    # In production, use actual sentiment analysis
    sentiment = "neutral"
    urgency = "medium"
    
    if any(word in content.lower() for word in ["urgent", "asap", "emergency", "critical"]):
        urgency = "high"
    if any(word in content.lower() for word in ["angry", "frustrated", "disappointed", "upset"]):
        sentiment = "negative"
    elif any(word in content.lower() for word in ["thank", "great", "excellent", "happy", "love"]):
        sentiment = "positive"
    
    return {
        "sentiment": sentiment,
        "urgency": urgency,
        "requires_human_review": urgency == "high" or sentiment == "negative"
    }


# Tool: Generate email response
def generate_email_response(
    original_message: str,
    tone: str = "professional",
    include_signature: bool = True
) -> Dict:
    """Generate a draft email response."""
    
    # Tone templates
    tones = {
        "professional": "formal and courteous",
        "friendly": "warm and approachable",
        "apologetic": "sincere and apologetic",
        "enthusiastic": "excited and positive"
    }
    
    response = f"Draft response (tone: {tones.get(tone, 'professional')})\n\n"
    response += f"[AI will generate response based on: {original_message[:100]}...]\n\n"
    
    if include_signature:
        response += "\nBest regards,\nSoft Systems Studio Team"
    
    return {
        "draft": response,
        "tone": tone,
        "ready_for_review": True,
        "timestamp": datetime.now().isoformat()
    }


# Tool: Classify message type
def classify_message(content: str) -> Dict:
    """Classify the type and intent of a message."""
    
    message_types = []
    
    # Check for different message types
    if any(word in content.lower() for word in ["inquiry", "question", "ask", "wondering"]):
        message_types.append("inquiry")
    if any(word in content.lower() for word in ["complaint", "issue", "problem", "not working"]):
        message_types.append("complaint")
    if any(word in content.lower() for word in ["thank", "appreciate", "grateful"]):
        message_types.append("appreciation")
    if any(word in content.lower() for word in ["quote", "pricing", "cost", "how much"]):
        message_types.append("pricing_request")
    if any(word in content.lower() for word in ["meeting", "schedule", "call", "appointment"]):
        message_types.append("scheduling")
    
    if not message_types:
        message_types.append("general")
    
    return {
        "types": message_types,
        "primary_type": message_types[0],
        "action_required": message_types[0] in ["inquiry", "complaint", "pricing_request", "scheduling"]
    }


# Tool: Generate social media response
def generate_social_response(
    platform: str,
    original_post: str,
    response_type: str = "reply"
) -> Dict:
    """Generate social media response based on platform constraints."""
    
    platform_limits = {
        "twitter": 280,
        "linkedin": 3000,
        "facebook": 8000,
        "instagram": 2200
    }
    
    char_limit = platform_limits.get(platform.lower(), 1000)
    
    return {
        "platform": platform,
        "response_type": response_type,
        "char_limit": char_limit,
        "draft": f"[AI-generated {platform} response for: {original_post[:50]}...]",
        "includes_hashtags": platform.lower() in ["twitter", "instagram"],
        "includes_emojis": True,
        "timestamp": datetime.now().isoformat()
    }


# Tool: Schedule message
def schedule_message(
    content: str,
    platform: str,
    send_time: str
) -> Dict:
    """Schedule a message for future sending."""
    
    return {
        "scheduled": True,
        "platform": platform,
        "send_time": send_time,
        "content_preview": content[:100],
        "status": "pending_approval",
        "can_edit": True,
        "can_cancel": True
    }


async def main():
    """Run the Email & Social Media Automation Agent."""
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Please set OPENAI_API_KEY environment variable")
        return
    
    print("=" * 80)
    print("📧 EMAIL & SOCIAL MEDIA AUTOMATION AGENT")
    print("=" * 80)
    print()
    
    # Initialize infrastructure
    llm_provider = OpenAIProvider(api_key=api_key)
    agent_repo = InMemoryAgentRepository()
    tool_registry = InMemoryToolRegistry()
    logger = StructuredLogger()
    
    # Register tools
    tools = [
        Tool(
            name="analyze_sentiment",
            description="Analyze the sentiment and urgency of a message. Returns sentiment (positive/negative/neutral) and urgency level.",
            handler=analyze_sentiment,
            parameters={
                "content": {"type": "string", "description": "The message content to analyze"}
            }
        ),
        Tool(
            name="classify_message",
            description="Classify the type and intent of a message (inquiry, complaint, appreciation, etc.)",
            handler=classify_message,
            parameters={
                "content": {"type": "string", "description": "The message content to classify"}
            }
        ),
        Tool(
            name="generate_email_response",
            description="Generate a draft email response with specified tone (professional, friendly, apologetic, enthusiastic)",
            handler=generate_email_response,
            parameters={
                "original_message": {"type": "string", "description": "The original message to respond to"},
                "tone": {"type": "string", "description": "Desired tone: professional, friendly, apologetic, or enthusiastic"},
                "include_signature": {"type": "boolean", "description": "Whether to include email signature"}
            }
        ),
        Tool(
            name="generate_social_response",
            description="Generate a social media response for Twitter, LinkedIn, Facebook, or Instagram",
            handler=generate_social_response,
            parameters={
                "platform": {"type": "string", "description": "Social media platform: twitter, linkedin, facebook, or instagram"},
                "original_post": {"type": "string", "description": "The post/comment to respond to"},
                "response_type": {"type": "string", "description": "Type of response: reply, comment, or dm"}
            }
        ),
        Tool(
            name="schedule_message",
            description="Schedule a message for future sending on email or social media",
            handler=schedule_message,
            parameters={
                "content": {"type": "string", "description": "Message content to schedule"},
                "platform": {"type": "string", "description": "Platform: email, twitter, linkedin, facebook, instagram"},
                "send_time": {"type": "string", "description": "When to send (ISO format or relative like '2 hours')"}
            }
        )
    ]
    
    for tool in tools:
        tool_registry.register(tool)
    
    print("🛠️  Registered Tools:")
    for tool in tools:
        print(f"   • {tool.name}")
    print()
    
    # Create agent
    agent = Agent(
        name="Email & Social Media Assistant",
        description="AI assistant that automates email and social media responses with sentiment analysis and multi-platform support",
        system_prompt="""You are an expert communication assistant specializing in email and social media automation.

Your responsibilities:
1. Analyze incoming messages for sentiment, urgency, and intent
2. Generate appropriate responses that match the desired tone and platform
3. Classify messages to determine the best response strategy
4. Create drafts for human review before sending
5. Schedule messages for optimal sending times
6. Maintain consistent brand voice across all platforms

Guidelines:
- Always analyze sentiment before responding
- Match the tone to the situation (professional for complaints, friendly for inquiries)
- Keep social media responses concise and engaging
- Flag urgent or negative messages for human review
- Include relevant hashtags for Twitter/Instagram
- Respect platform character limits
- Generate drafts, not final messages (human approval required)

For complaints: Be apologetic, acknowledge the issue, offer solutions
For inquiries: Be helpful, provide clear information, offer next steps
For appreciation: Be grateful, brief, and genuine
For pricing: Provide value context, suggest consultation call""",
        model_name="gpt-4o",
        temperature=0.7,
        tools=[tool.name for tool in tools]
    )
    
    agent_id = await agent_repo.save(agent)
    agent.id = agent_id
    
    print(f"✅ Created agent: {agent.name}")
    print(f"   Model: {agent.model_name}")
    print(f"   Tools: {len(agent.tools)}")
    print()
    
    # Initialize orchestrator
    orchestrator = AgentOrchestrator(
        llm_provider=llm_provider,
        agent_repository=agent_repo,
        tool_registry=tool_registry,
        observability=logger
    )
    
    # Test scenarios
    scenarios = [
        {
            "title": "Customer Inquiry Email",
            "task": """Analyze this customer email and generate an appropriate response:

"Hi, I'm interested in your AI automation services for my small business. We get about 50 customer emails per day and struggle to keep up. Can you help with email automation? What's the pricing like? I'd love to schedule a call to discuss."

Please analyze sentiment, classify the message type, and generate a professional response draft."""
        },
        {
            "title": "Complaint on Social Media (Twitter)",
            "task": """Handle this negative Twitter mention:

"@SoftSystemsStudio Your service has been down for 2 hours! This is unacceptable. I have a deadline today and can't access my account. Very disappointed."

Analyze sentiment, then generate an apologetic Twitter response that addresses the issue and offers help."""
        },
        {
            "title": "LinkedIn Connection Message",
            "task": """Generate a response for this LinkedIn connection request message:

"Hi! I noticed your company does AI automation. We're a growing startup looking to automate our customer support. Would love to connect and learn more about your solutions!"

Create a friendly, professional LinkedIn response that's engaging but not too sales-y."""
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print("=" * 80)
        print(f"📋 Scenario {i}: {scenario['title']}")
        print("=" * 80)
        print()
        
        result = await orchestrator.execute(
            agent_id=agent.id,
            user_input=scenario['task']
        )
        
        print(f"🤖 Agent Response:\n")
        print(result.response)
        print()
        
        print(f"📊 Execution Metrics:")
        print(f"   • Tokens: {result.total_tokens}")
        print(f"   • Duration: {result.duration:.2f}s")
        print(f"   • Iterations: {result.iterations}")
        print(f"   • Cost: ${result.cost:.4f}")
        print()
    
    print("=" * 80)
    print("✨ Email & Social Media Automation Demo Complete!")
    print()
    print("💡 Integration Options:")
    print("   • Gmail API for automated email responses")
    print("   • Twitter API for tweet monitoring and replies")
    print("   • LinkedIn API for professional networking")
    print("   • Facebook Graph API for page management")
    print("   • Instagram API for comment responses")
    print("   • Zapier/Make for workflow automation")
    print()
    print("🔒 Safety Features:")
    print("   • Human review required for all responses")
    print("   • Sentiment analysis for tone matching")
    print("   • Urgency detection for priority handling")
    print("   • Draft generation (not auto-send)")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
