"""
Cleanup Policy Domain Models - Business rules for email organization.

Defines the rules and policies that govern how emails should be cleaned up,
organized, and maintained.
"""

from datetime import datetime
from typing import List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from src.domain.email_thread import EmailThread, EmailMessage, EmailCategory, EmailImportance


class CleanupAction(str, Enum):
    """Actions that can be applied to emails."""
    DELETE = "delete"  # Move to trash
    ARCHIVE = "archive"  # Remove from inbox
    MARK_READ = "mark_read"  # Mark as read
    MARK_UNREAD = "mark_unread"  # Mark as unread
    STAR = "star"  # Star/flag
    UNSTAR = "unstar"  # Remove star
    APPLY_LABEL = "apply_label"  # Add label
    REMOVE_LABEL = "remove_label"  # Remove label
    SKIP = "skip"  # No action


class RuleCondition(str, Enum):
    """Condition types for matching emails."""
    SENDER_MATCHES = "sender_matches"
    SUBJECT_CONTAINS = "subject_contains"
    OLDER_THAN_DAYS = "older_than_days"
    LARGER_THAN_MB = "larger_than_mb"
    CATEGORY_IS = "category_is"
    IMPORTANCE_IS = "importance_is"
    IS_UNREAD = "is_unread"
    IS_STARRED = "is_starred"
    HAS_ATTACHMENTS = "has_attachments"
    LABEL_IS = "label_is"


@dataclass
class CleanupRule:
    """
    A rule that defines what to do with matching emails.
    
    Rules are evaluated against emails to determine what actions to take.
    """
    id: str
    name: str
    description: str
    condition_type: RuleCondition
    condition_value: str
    action: CleanupAction
    action_params: dict = field(default_factory=dict)
    enabled: bool = True
    priority: int = 100  # Lower number = higher priority
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def matches_message(self, message: EmailMessage) -> bool:
        """Check if message matches this rule's condition."""
        if not self.enabled:
            return False
        
        try:
            if self.condition_type == RuleCondition.SENDER_MATCHES:
                return message.matches_sender(self.condition_value)
            
            elif self.condition_type == RuleCondition.SUBJECT_CONTAINS:
                return self.condition_value.lower() in message.subject.lower()
            
            elif self.condition_type == RuleCondition.OLDER_THAN_DAYS:
                days = int(self.condition_value)
                return message.age_days > days
            
            elif self.condition_type == RuleCondition.LARGER_THAN_MB:
                mb = float(self.condition_value)
                return message.size_bytes > (mb * 1024 * 1024)
            
            elif self.condition_type == RuleCondition.CATEGORY_IS:
                return message.category.value == self.condition_value
            
            elif self.condition_type == RuleCondition.IMPORTANCE_IS:
                return message.importance.value == self.condition_value
            
            elif self.condition_type == RuleCondition.IS_UNREAD:
                return message.is_unread == (self.condition_value.lower() == "true")
            
            elif self.condition_type == RuleCondition.IS_STARRED:
                return message.is_starred == (self.condition_value.lower() == "true")
            
            elif self.condition_type == RuleCondition.HAS_ATTACHMENTS:
                return message.has_attachments == (self.condition_value.lower() == "true")
            
            elif self.condition_type == RuleCondition.LABEL_IS:
                return self.condition_value in message.labels
            
        except (ValueError, AttributeError):
            return False
        
        return False
    
    def matches_thread(self, thread: EmailThread) -> bool:
        """Check if thread matches this rule (checks all messages)."""
        return any(self.matches_message(msg) for msg in thread.messages)


@dataclass
class LabelingRule:
    """
    Rule for automatically applying labels to emails.
    
    Similar to CleanupRule but specifically for organization/labeling.
    """
    id: str
    name: str
    label_to_apply: str
    condition_type: RuleCondition
    condition_value: str
    enabled: bool = True
    
    def matches_message(self, message: EmailMessage) -> bool:
        """Check if message should get this label."""
        if not self.enabled:
            return False
        
        # Reuse CleanupRule matching logic
        temp_rule = CleanupRule(
            id=self.id,
            name=self.name,
            description="",
            condition_type=self.condition_type,
            condition_value=self.condition_value,
            action=CleanupAction.APPLY_LABEL,
            enabled=self.enabled,
        )
        return temp_rule.matches_message(message)


@dataclass
class RetentionPolicy:
    """
    Policy for how long to keep different types of emails.
    
    Defines retention rules based on categories, importance, etc.
    """
    id: str
    name: str
    description: str
    rules: List[tuple[RuleCondition, str, int]] = field(default_factory=list)  # (condition, value, days_to_keep)
    default_retention_days: int = 365
    enabled: bool = True
    
    def get_retention_days(self, message: EmailMessage) -> int:
        """Get retention period for a message based on policy rules."""
        if not self.enabled:
            return self.default_retention_days
        
        # Check each rule in order
        for condition_type, condition_value, retention_days in self.rules:
            temp_rule = CleanupRule(
                id=f"{self.id}_temp",
                name="temp",
                description="",
                condition_type=condition_type,
                condition_value=condition_value,
                action=CleanupAction.SKIP,
            )
            if temp_rule.matches_message(message):
                return retention_days
        
        return self.default_retention_days
    
    def should_delete(self, message: EmailMessage) -> bool:
        """Check if message should be deleted based on retention policy."""
        retention_days = self.get_retention_days(message)
        return message.age_days > retention_days


@dataclass
class CleanupPolicy:
    """
    Complete cleanup policy for a user's mailbox.
    
    Combines multiple rules, labeling rules, and retention policies
    into a cohesive strategy.
    """
    id: str
    user_id: str
    name: str
    description: str
    cleanup_rules: List[CleanupRule] = field(default_factory=list)
    labeling_rules: List[LabelingRule] = field(default_factory=list)
    retention_policy: Optional[RetentionPolicy] = None
    auto_archive_promotions: bool = False
    auto_archive_social: bool = False
    auto_mark_read_old: bool = False
    old_threshold_days: int = 30
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_actions_for_message(self, message: EmailMessage) -> List[tuple[CleanupAction, dict]]:
        """
        Determine all actions to take for a message.
        
        Returns list of (action, params) tuples.
        """
        actions = []
        
        if not self.enabled:
            return actions
        
        # Sort rules by priority
        sorted_rules = sorted(self.cleanup_rules, key=lambda r: r.priority)
        
        # Apply matching cleanup rules
        for rule in sorted_rules:
            if rule.matches_message(message):
                actions.append((rule.action, rule.action_params))
                # Stop after first match for delete/archive actions
                if rule.action in (CleanupAction.DELETE, CleanupAction.ARCHIVE):
                    break
        
        # Apply labeling rules
        for label_rule in self.labeling_rules:
            if label_rule.matches_message(message):
                actions.append((
                    CleanupAction.APPLY_LABEL,
                    {"label": label_rule.label_to_apply}
                ))
        
        # Apply retention policy
        if self.retention_policy and self.retention_policy.should_delete(message):
            actions.append((CleanupAction.DELETE, {}))
        
        # Auto-archive by category
        if self.auto_archive_promotions and message.category == EmailCategory.PROMOTIONS:
            if message.age_days > self.old_threshold_days:
                actions.append((CleanupAction.ARCHIVE, {}))
        
        if self.auto_archive_social and message.category == EmailCategory.SOCIAL:
            if message.age_days > self.old_threshold_days:
                actions.append((CleanupAction.ARCHIVE, {}))
        
        # Auto mark read old emails
        if self.auto_mark_read_old and message.is_unread:
            if message.age_days > self.old_threshold_days:
                actions.append((CleanupAction.MARK_READ, {}))
        
        return actions
    
    def analyze_thread(self, thread: EmailThread) -> dict:
        """
        Analyze a thread and return proposed actions.
        
        Returns dict with analysis and actions for each message.
        """
        analysis = {
            "thread_id": thread.id,
            "subject": thread.subject,
            "message_count": thread.message_count,
            "total_actions": 0,
            "messages": []
        }
        
        for message in thread.messages:
            actions = self.get_actions_for_message(message)
            if actions:
                analysis["messages"].append({
                    "message_id": message.id,
                    "from": str(message.from_address),
                    "subject": message.subject,
                    "date": message.date.isoformat(),
                    "actions": [(action.value, params) for action, params in actions]
                })
                analysis["total_actions"] += len(actions)
        
        return analysis
    
    @classmethod
    def create_default_policy(cls, user_id: str) -> 'CleanupPolicy':
        """Create a sensible default policy."""
        return cls(
            id=f"default_{user_id}",
            user_id=user_id,
            name="Default Cleanup Policy",
            description="Automatically archives old promotional and social emails",
            cleanup_rules=[],
            labeling_rules=[],
            retention_policy=None,
            auto_archive_promotions=True,
            auto_archive_social=True,
            auto_mark_read_old=False,
            old_threshold_days=30,
            enabled=True,
        )
