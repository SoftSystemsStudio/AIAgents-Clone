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


class CleanupRule:
    """
    A rule that defines what to do with matching emails.

    This implementation is backwards-compatible with older callers that used
    keyword args such as `sender_domain`, `older_than_days`, `category`, etc.
    Internally rules are normalized to `condition_type` + `condition_value`.
    """
    def __init__(
        self,
        id: str = "",
        name: str = "",
        description: str = "",
        condition_type: Optional[RuleCondition] = None,
        condition_value: Optional[str] = None,
        sender_domain: Optional[str] = None,
        subject_contains: Optional[str] = None,
        older_than_days: Optional[int] = None,
        larger_than_mb: Optional[float] = None,
        category: Optional[EmailCategory] = None,
        importance: Optional[EmailImportance] = None,
        is_unread: Optional[bool] = None,
        is_starred: Optional[bool] = None,
        has_attachments: Optional[bool] = None,
        label_is: Optional[str] = None,
        action: Optional[CleanupAction] = None,
        action_params: Optional[dict] = None,
        enabled: bool = True,
        priority: int = 100,
        created_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.action = action
        self.action_params = action_params or {}
        self.enabled = enabled
        self.priority = priority
        self.created_at = created_at or datetime.utcnow()

        # Normalize condition_type/value from either explicit fields or legacy kwargs
        if condition_type is not None and condition_value is not None:
            self.condition_type = condition_type
            self.condition_value = condition_value
        elif sender_domain is not None:
            self.condition_type = RuleCondition.SENDER_MATCHES
            self.condition_value = sender_domain
        elif subject_contains is not None:
            self.condition_type = RuleCondition.SUBJECT_CONTAINS
            self.condition_value = subject_contains
        elif older_than_days is not None:
            self.condition_type = RuleCondition.OLDER_THAN_DAYS
            self.condition_value = str(older_than_days)
        elif larger_than_mb is not None:
            self.condition_type = RuleCondition.LARGER_THAN_MB
            self.condition_value = str(larger_than_mb)
        elif category is not None:
            self.condition_type = RuleCondition.CATEGORY_IS
            self.condition_value = getattr(category, "value", str(category))
        elif importance is not None:
            self.condition_type = RuleCondition.IMPORTANCE_IS
            self.condition_value = getattr(importance, "value", str(importance))
        elif is_unread is not None:
            self.condition_type = RuleCondition.IS_UNREAD
            self.condition_value = str(is_unread).lower()
        elif is_starred is not None:
            self.condition_type = RuleCondition.IS_STARRED
            self.condition_value = str(is_starred).lower()
        elif has_attachments is not None:
            self.condition_type = RuleCondition.HAS_ATTACHMENTS
            self.condition_value = str(has_attachments).lower()
        elif label_is is not None:
            self.condition_type = RuleCondition.LABEL_IS
            self.condition_value = label_is
        else:
            # Fallback to provided condition_type/value even if one is missing
            self.condition_type = condition_type or RuleCondition.SENDER_MATCHES
            self.condition_value = condition_value or ""
    
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


class RetentionPolicy:
    """
    Policy for how long to keep different types of emails.

    Defines retention rules based on categories, importance, etc.
    Accepts legacy kwargs: `keep_starred`, `keep_unread`, `keep_recent_days`.
    """
    def __init__(
        self,
        id: str = "",
        name: str = "",
        description: str = "",
        rules: Optional[List[tuple[RuleCondition, str, int]]] = None,
        default_retention_days: int = 365,
        enabled: bool = True,
        keep_starred: Optional[bool] = None,
        keep_unread: Optional[bool] = None,
        keep_recent_days: Optional[int] = None,
    ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.rules = rules or []
        # support legacy `keep_recent_days`
        self.default_retention_days = keep_recent_days if keep_recent_days is not None else default_retention_days
        self.enabled = enabled
        # legacy flags can be stored for downstream logic if needed
        self.keep_starred = bool(keep_starred) if keep_starred is not None else False
        self.keep_unread = bool(keep_unread) if keep_unread is not None else False
    
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


class CleanupPolicy:
    """
    Complete cleanup policy for a user's mailbox.

    Combines multiple rules, labeling rules, and retention policies
    into a cohesive strategy.
    Backwards-compatible parameter names accepted: `rules` (alias to
    `cleanup_rules`) and `retention` (alias to `retention_policy`).
    """
    def __init__(
        self,
        id: str,
        user_id: str,
        name: str,
        description: str = "",
        cleanup_rules: Optional[List[CleanupRule]] = None,
        rules: Optional[List[CleanupRule]] = None,
        labeling_rules: Optional[List[LabelingRule]] = None,
        retention_policy: Optional[RetentionPolicy] = None,
        retention: Optional[RetentionPolicy] = None,
        auto_archive_promotions: bool = False,
        auto_archive_social: bool = False,
        auto_mark_read_old: bool = False,
        old_threshold_days: int = 30,
        enabled: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        dry_run: Optional[bool] = None,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.name = name
        self.description = description
        # support legacy `rules` kwarg
        self.cleanup_rules = cleanup_rules if cleanup_rules is not None else (rules or [])
        self.labeling_rules = labeling_rules or []
        # support legacy `retention` kwarg
        self.retention_policy = retention_policy if retention_policy is not None else retention
        self.auto_archive_promotions = auto_archive_promotions
        self.auto_archive_social = auto_archive_social
        self.auto_mark_read_old = auto_mark_read_old
        self.old_threshold_days = old_threshold_days
        self.enabled = enabled
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        # Some callers use `dry_run` at policy-level; store it if present
        if dry_run is not None:
            self.dry_run = bool(dry_run)
    @property
    def rules(self) -> List[CleanupRule]:
        return self.cleanup_rules

    @rules.setter
    def rules(self, value: List[CleanupRule]) -> None:
        self.cleanup_rules = value
    
    def get_actions_for_message(self, message: EmailMessage) -> List[tuple[CleanupAction, dict]]:
        """
        Determine all actions to take for a message.
        
        Returns list of (action, params) tuples.
        """
        actions = []
        
        if not self.enabled:
            return actions
        
        # SAFETY GUARDRAILS: Never touch starred or important messages
        if message.is_starred:
            return actions
        if "IMPORTANT" in message.labels:
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
