"""
Appointment & Booking Automation Agent

Automates scheduling, calendar management, and booking workflows.

Features:
- Check availability across multiple calendars
- Schedule appointments automatically
- Send booking confirmations and reminders
- Handle rescheduling and cancellations
- Integrate with Google Calendar, Outlook, Calendly
- Time zone conversions
- Buffer time management
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from src.domain.models import Agent, Tool
from src.infrastructure.llm_providers import OpenAIProvider
from src.infrastructure.repositories import InMemoryAgentRepository, InMemoryToolRegistry
from src.infrastructure.observability import StructuredLogger
from src.application.orchestrator import AgentOrchestrator


# Tool: Check availability
def check_availability(
    date: str,
    duration_minutes: int = 60,
    time_zone: str = "America/Los_Angeles"
) -> Dict:
    """Check calendar availability for a specific date."""
    
    # Simulate checking calendar availability
    # In production, integrate with Google Calendar, Outlook, etc.
    
    available_slots = [
        {"start": "09:00", "end": "10:00", "available": True},
        {"start": "10:00", "end": "11:00", "available": False, "reason": "Meeting with John"},
        {"start": "11:00", "end": "12:00", "available": True},
        {"start": "13:00", "end": "14:00", "available": True},
        {"start": "14:00", "end": "15:00", "available": True},
        {"start": "15:00", "end": "16:00", "available": False, "reason": "Team standup"},
        {"start": "16:00", "end": "17:00", "available": True}
    ]
    
    return {
        "date": date,
        "time_zone": time_zone,
        "requested_duration": duration_minutes,
        "available_slots": [slot for slot in available_slots if slot["available"]],
        "total_available": sum(1 for slot in available_slots if slot["available"]),
        "recommended_times": ["09:00", "11:00", "13:00"]
    }


# Tool: Create booking
def create_booking(
    client_name: str,
    client_email: str,
    date: str,
    time: str,
    duration_minutes: int,
    service_type: str,
    notes: Optional[str] = None
) -> Dict:
    """Create a new booking/appointment."""
    
    booking_id = f"BK-{datetime.now().strftime('%Y%m%d')}-{hash(client_email) % 10000:04d}"
    
    return {
        "booking_id": booking_id,
        "status": "confirmed",
        "client": {
            "name": client_name,
            "email": client_email
        },
        "appointment": {
            "date": date,
            "time": time,
            "duration_minutes": duration_minutes,
            "end_time": (datetime.strptime(time, "%H:%M") + timedelta(minutes=duration_minutes)).strftime("%H:%M")
        },
        "service": service_type,
        "notes": notes,
        "confirmation_sent": True,
        "calendar_event_created": True,
        "reminder_scheduled": True,
        "cancellation_link": f"https://bookings.softsystems.studio/cancel/{booking_id}"
    }


# Tool: Send booking confirmation
def send_booking_confirmation(
    booking_id: str,
    client_email: str,
    appointment_details: Dict
) -> Dict:
    """Send booking confirmation email to client."""
    
    email_content = f"""
Dear {appointment_details.get('client_name', 'Valued Customer')},

Your appointment has been confirmed!

📅 Date: {appointment_details['date']}
🕐 Time: {appointment_details['time']}
⏱️  Duration: {appointment_details['duration_minutes']} minutes
🔧 Service: {appointment_details['service']}

Location: Virtual (Zoom link will be sent 15 minutes before)

Need to reschedule? Click here: [Reschedule Link]
Need to cancel? Click here: [Cancel Link]

We look forward to meeting with you!

Best regards,
Soft Systems Studio Team
"""
    
    return {
        "confirmation_sent": True,
        "booking_id": booking_id,
        "recipient": client_email,
        "email_content": email_content,
        "sent_at": datetime.now().isoformat(),
        "includes_calendar_invite": True,
        "includes_zoom_link": True
    }


# Tool: Reschedule appointment
def reschedule_appointment(
    booking_id: str,
    new_date: str,
    new_time: str,
    reason: Optional[str] = None
) -> Dict:
    """Reschedule an existing appointment."""
    
    return {
        "booking_id": booking_id,
        "status": "rescheduled",
        "previous_appointment": {
            "date": "2024-01-20",
            "time": "10:00"
        },
        "new_appointment": {
            "date": new_date,
            "time": new_time
        },
        "reason": reason,
        "notifications_sent": {
            "client": True,
            "staff": True
        },
        "calendar_updated": True,
        "timestamp": datetime.now().isoformat()
    }


# Tool: Cancel appointment
def cancel_appointment(
    booking_id: str,
    reason: Optional[str] = None,
    cancelled_by: str = "client"
) -> Dict:
    """Cancel an existing appointment."""
    
    return {
        "booking_id": booking_id,
        "status": "cancelled",
        "cancelled_at": datetime.now().isoformat(),
        "cancelled_by": cancelled_by,
        "reason": reason,
        "refund_applicable": True,
        "cancellation_fee": 0.00,
        "notifications_sent": {
            "client": True,
            "staff": True
        },
        "calendar_event_deleted": True,
        "slot_now_available": True
    }


# Tool: Send appointment reminders
def send_appointment_reminder(
    booking_id: str,
    reminder_type: str = "24_hours"
) -> Dict:
    """Send appointment reminder to client."""
    
    reminder_messages = {
        "24_hours": "Your appointment is tomorrow at {time}. We look forward to seeing you!",
        "2_hours": "Your appointment is in 2 hours at {time}. Zoom link: [link]",
        "15_minutes": "Your appointment starts in 15 minutes! Join here: [Zoom link]"
    }
    
    return {
        "booking_id": booking_id,
        "reminder_type": reminder_type,
        "message": reminder_messages.get(reminder_type, "Reminder about your appointment"),
        "sent_at": datetime.now().isoformat(),
        "delivery_method": ["email", "sms"],
        "includes_zoom_link": reminder_type in ["2_hours", "15_minutes"],
        "includes_cancel_link": True
    }


# Tool: Find available slots
def find_available_slots(
    start_date: str,
    end_date: str,
    duration_minutes: int = 60,
    preferred_times: Optional[List[str]] = None
) -> Dict:
    """Find all available appointment slots in a date range."""
    
    # Simulate finding available slots
    available_slots = []
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    while current_date <= end:
        # Skip weekends
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            for hour in [9, 10, 11, 13, 14, 15, 16]:
                available_slots.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "time": f"{hour:02d}:00",
                    "duration_minutes": duration_minutes,
                    "available": True
                })
        current_date += timedelta(days=1)
    
    # Filter by preferred times if specified
    if preferred_times:
        available_slots = [
            slot for slot in available_slots
            if slot["time"] in preferred_times
        ]
    
    return {
        "date_range": {"start": start_date, "end": end_date},
        "duration_minutes": duration_minutes,
        "total_slots_found": len(available_slots),
        "available_slots": available_slots[:20],  # Return first 20
        "earliest_available": available_slots[0] if available_slots else None,
        "preferred_times_applied": preferred_times is not None
    }


async def main():
    """Run the Appointment & Booking Automation Agent."""
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Please set OPENAI_API_KEY environment variable")
        return
    
    print("=" * 80)
    print("📅 APPOINTMENT & BOOKING AUTOMATION AGENT")
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
            name="check_availability",
            description="Check calendar availability for a specific date and duration",
            handler=check_availability,
            parameters={
                "date": {"type": "string", "description": "Date to check in YYYY-MM-DD format"},
                "duration_minutes": {"type": "integer", "description": "Appointment duration in minutes (default: 60)"},
                "time_zone": {"type": "string", "description": "Time zone (default: America/Los_Angeles)"}
            }
        ),
        Tool(
            name="find_available_slots",
            description="Find all available appointment slots within a date range",
            handler=find_available_slots,
            parameters={
                "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                "duration_minutes": {"type": "integer", "description": "Required duration in minutes"},
                "preferred_times": {"type": "array", "description": "Optional preferred time slots (e.g., ['09:00', '14:00'])"}
            }
        ),
        Tool(
            name="create_booking",
            description="Create a new appointment booking",
            handler=create_booking,
            parameters={
                "client_name": {"type": "string", "description": "Client's full name"},
                "client_email": {"type": "string", "description": "Client's email address"},
                "date": {"type": "string", "description": "Appointment date (YYYY-MM-DD)"},
                "time": {"type": "string", "description": "Appointment time (HH:MM)"},
                "duration_minutes": {"type": "integer", "description": "Duration in minutes"},
                "service_type": {"type": "string", "description": "Type of service/consultation"},
                "notes": {"type": "string", "description": "Additional notes or requirements"}
            }
        ),
        Tool(
            name="send_booking_confirmation",
            description="Send booking confirmation email with appointment details",
            handler=send_booking_confirmation,
            parameters={
                "booking_id": {"type": "string", "description": "Booking ID"},
                "client_email": {"type": "string", "description": "Client's email"},
                "appointment_details": {"type": "object", "description": "Appointment details"}
            }
        ),
        Tool(
            name="reschedule_appointment",
            description="Reschedule an existing appointment to a new date/time",
            handler=reschedule_appointment,
            parameters={
                "booking_id": {"type": "string", "description": "Booking ID to reschedule"},
                "new_date": {"type": "string", "description": "New date (YYYY-MM-DD)"},
                "new_time": {"type": "string", "description": "New time (HH:MM)"},
                "reason": {"type": "string", "description": "Optional reason for rescheduling"}
            }
        ),
        Tool(
            name="cancel_appointment",
            description="Cancel an existing appointment",
            handler=cancel_appointment,
            parameters={
                "booking_id": {"type": "string", "description": "Booking ID to cancel"},
                "reason": {"type": "string", "description": "Optional cancellation reason"},
                "cancelled_by": {"type": "string", "description": "Who cancelled: client or staff"}
            }
        ),
        Tool(
            name="send_appointment_reminder",
            description="Send appointment reminder (24 hours, 2 hours, or 15 minutes before)",
            handler=send_appointment_reminder,
            parameters={
                "booking_id": {"type": "string", "description": "Booking ID"},
                "reminder_type": {"type": "string", "description": "24_hours, 2_hours, or 15_minutes"}
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
        name="Booking Assistant",
        description="AI assistant that automates appointment scheduling, calendar management, and booking workflows",
        system_prompt="""You are an expert booking and scheduling assistant specializing in appointment automation.

Your responsibilities:
1. Check calendar availability across multiple calendars
2. Find optimal time slots based on preferences and constraints
3. Create bookings with all necessary details
4. Send professional booking confirmations
5. Handle rescheduling requests efficiently
6. Process cancellations with proper notifications
7. Send timely reminders (24 hours, 2 hours, 15 minutes before)
8. Manage time zones and buffer times

Guidelines:
- Always check availability before booking
- Confirm all booking details (date, time, duration, service)
- Send confirmation immediately after booking
- Include calendar invites and meeting links
- Schedule automated reminders
- Handle rescheduling requests gracefully
- Process cancellations with empathy
- Respect buffer times between appointments
- Convert time zones when needed
- Provide clear cancellation/reschedule instructions

For new bookings: Confirm details, check availability, create booking, send confirmation
For rescheduling: Check new slot availability, update booking, notify all parties
For cancellations: Process immediately, send confirmations, open slot for rebooking
For reminders: Send at appropriate intervals with relevant information (Zoom links, preparation notes)

Business hours: Monday-Friday, 9 AM - 5 PM (exclude lunch 12-1 PM)
Default appointment duration: 60 minutes
Buffer time between appointments: 15 minutes
Time zone: PST/PDT (America/Los_Angeles)""",
        model_name="gpt-4o",
        temperature=0.4,  # Balanced for scheduling accuracy
        tools=[tool.name for tool in tools]
    )
    
    agent_id = await agent_repo.save(agent)
    agent.id = agent_id
    
    print(f"✅ Created agent: {agent.name}")
    print(f"   Model: {agent.model_name}")
    print(f"   Temperature: {agent.temperature}")
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
            "title": "New Appointment Booking",
            "task": """A client named Sarah Martinez (sarah.m@example.com) wants to book a consultation about AI automation services. She's available next week, preferably Tuesday or Wednesday afternoon. The consultation should be 60 minutes.

Please check availability and create a booking for her."""
        },
        {
            "title": "Reschedule Request",
            "task": """Client John Smith (booking ID: BK-20240120-1234) needs to reschedule his appointment from January 20th at 10:00 AM. He can do any time Thursday or Friday this week. Please find available slots and reschedule him."""
        },
        {
            "title": "Find Available Slots",
            "task": """I need to find all available appointment slots for the next 5 business days. The appointments are 60 minutes each, and the client prefers morning times (9 AM - 12 PM). Please provide a list of available options."""
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
    print("✨ Appointment & Booking Automation Demo Complete!")
    print()
    print("💡 Integration Options:")
    print("   • Google Calendar API for calendar management")
    print("   • Microsoft Outlook API for enterprise calendars")
    print("   • Calendly API for scheduling pages")
    print("   • Zoom API for meeting links")
    print("   • Twilio API for SMS reminders")
    print("   • SendGrid API for email confirmations")
    print("   • Stripe API for payment processing")
    print()
    print("🔧 Automation Features:")
    print("   • Smart availability checking")
    print("   • Automatic confirmations")
    print("   • Multi-reminder system (24h, 2h, 15min)")
    print("   • One-click rescheduling")
    print("   • Time zone conversion")
    print("   • Buffer time management")
    print("   • No-show tracking")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
