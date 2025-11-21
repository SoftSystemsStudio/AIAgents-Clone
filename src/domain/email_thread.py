"""
Email Thread Domain Models - Core business entities for email management.

These models represent the fundamental concepts in email organization,
independent of any external API or infrastructure.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class EmailCategory(str, Enum):
    """Gmail category classifications."""
    PRIMARY = "primary"
    SOCIAL = "social"
    PROMOTIONS = "promotions"
    UPDATES = "updates"
    FORUMS = "forums"
    UNKNOWN = "unknown"


class EmailImportance(str, Enum):
    """Importance level for prioritization."""
    CRITICAL = "critical"  # Important personal/work emails
    HIGH = "high"  # Regular correspondence
    MEDIUM = "medium"  # Newsletters, notifications
    LOW = "low"  # Bulk, promotional
    SPAM = "spam"  # Suspected spam


@dataclass
class EmailAddress:
    """Email address with optional display name."""
    address: str
    name: Optional[str] = None
    
    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.address}>"
        return self.address
    
    @property
    def domain(self) -> str:
        """Extract domain from email address."""
        return self.address.split('@')[-1] if '@' in self.address else ""


@dataclass
class EmailMessage:
    """
    Single email message entity.
    
    Represents the core attributes of an email message needed for
    cleanup and organization decisions.
    """
    id: str
    thread_id: str
    subject: str
    from_address: EmailAddress
    to_addresses: List[EmailAddress]
    cc_addresses: List[EmailAddress] = field(default_factory=list)
    date: datetime = field(default_factory=datetime.utcnow)
    snippet: str = ""
    labels: List[str] = field(default_factory=list)
    size_bytes: int = 0
    has_attachments: bool = False
    is_unread: bool = False
    is_starred: bool = False
    category: EmailCategory = EmailCategory.UNKNOWN
    importance: EmailImportance = EmailImportance.MEDIUM
    
    @property
    def age_days(self) -> int:
        """Calculate age of email in days."""
        return (datetime.utcnow() - self.date).days
    
    @property
    def is_in_inbox(self) -> bool:
        """Check if email is in inbox."""
        return "INBOX" in self.labels
    
    @property
    def is_archived(self) -> bool:
        """Check if email is archived."""
        return "INBOX" not in self.labels and "TRASH" not in self.labels
    
    @property
    def is_trashed(self) -> bool:
        """Check if email is in trash."""
        return "TRASH" in self.labels
    
    def matches_sender(self, domain_or_email: str) -> bool:
        """Check if sender matches domain or exact email."""
        if '@' in domain_or_email:
            return self.from_address.address.lower() == domain_or_email.lower()
        return self.from_address.domain.lower() == domain_or_email.lower()


@dataclass
class EmailThread:
    """
    Email thread (conversation) entity.
    
    Represents a complete email conversation with all messages.
    """
    id: str
    messages: List[EmailMessage]
    snippet: str = ""
    labels: List[str] = field(default_factory=list)
    
    @property
    def subject(self) -> str:
        """Get thread subject from first message."""
        return self.messages[0].subject if self.messages else ""
    
    @property
    def message_count(self) -> int:
        """Number of messages in thread."""
        return len(self.messages)
    
    @property
    def latest_message(self) -> Optional[EmailMessage]:
        """Get most recent message in thread."""
        return max(self.messages, key=lambda m: m.date) if self.messages else None
    
    @property
    def oldest_message(self) -> Optional[EmailMessage]:
        """Get oldest message in thread."""
        return min(self.messages, key=lambda m: m.date) if self.messages else None
    
    @property
    def age_days(self) -> int:
        """Age of thread based on latest message."""
        latest = self.latest_message
        return latest.age_days if latest else 0
    
    @property
    def total_size_bytes(self) -> int:
        """Total size of all messages in thread."""
        return sum(m.size_bytes for m in self.messages)
    
    @property
    def is_unread(self) -> bool:
        """Check if any message in thread is unread."""
        return any(m.is_unread for m in self.messages)
    
    @property
    def has_attachments(self) -> bool:
        """Check if any message has attachments."""
        return any(m.has_attachments for m in self.messages)
    
    @property
    def unique_senders(self) -> List[EmailAddress]:
        """Get list of unique senders in thread."""
        seen = set()
        senders = []
        for msg in self.messages:
            if msg.from_address.address not in seen:
                seen.add(msg.from_address.address)
                senders.append(msg.from_address)
        return senders


@dataclass
class MailboxSnapshot:
    """
    Snapshot of mailbox state at a point in time.
    
    Used for analysis, reporting, and tracking changes over time.
    """
    user_id: str
    captured_at: datetime
    threads: List[EmailThread]
    total_messages: int = 0
    total_threads: int = 0
    unread_count: int = 0
    inbox_count: int = 0
    archived_count: int = 0
    trash_count: int = 0
    total_size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_threads(cls, user_id: str, threads: List[EmailThread]) -> 'MailboxSnapshot':
        """Create snapshot from list of threads."""
        all_messages = [msg for thread in threads for msg in thread.messages]
        
        return cls(
            user_id=user_id,
            captured_at=datetime.utcnow(),
            threads=threads,
            total_messages=len(all_messages),
            total_threads=len(threads),
            unread_count=sum(1 for msg in all_messages if msg.is_unread),
            inbox_count=sum(1 for msg in all_messages if msg.is_in_inbox),
            archived_count=sum(1 for msg in all_messages if msg.is_archived),
            trash_count=sum(1 for msg in all_messages if msg.is_trashed),
            total_size_bytes=sum(msg.size_bytes for msg in all_messages),
        )
    
    @property
    def size_mb(self) -> float:
        """Total size in megabytes."""
        return self.total_size_bytes / (1024 * 1024)
    
    def get_threads_by_sender(self, domain_or_email: str) -> List[EmailThread]:
        """Get all threads from a specific sender."""
        return [
            thread for thread in self.threads
            if thread.messages and thread.messages[0].matches_sender(domain_or_email)
        ]
    
    def get_old_threads(self, days: int) -> List[EmailThread]:
        """Get threads older than specified days."""
        return [thread for thread in self.threads if thread.age_days > days]
    
    def get_large_threads(self, min_size_mb: float) -> List[EmailThread]:
        """Get threads larger than specified size in MB."""
        min_bytes = min_size_mb * 1024 * 1024
        return [thread for thread in self.threads if thread.total_size_bytes > min_bytes]
    
    def get_threads_by_category(self, category: EmailCategory) -> List[EmailThread]:
        """Get threads in a specific category."""
        return [
            thread for thread in self.threads
            if thread.messages and thread.messages[0].category == category
        ]
    
    def summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "user_id": self.user_id,
            "captured_at": self.captured_at.isoformat(),
            "total_messages": self.total_messages,
            "total_threads": self.total_threads,
            "unread_count": self.unread_count,
            "inbox_count": self.inbox_count,
            "archived_count": self.archived_count,
            "trash_count": self.trash_count,
            "size_mb": round(self.size_mb, 2),
        }
