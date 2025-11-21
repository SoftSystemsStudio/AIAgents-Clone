"""
Cleanup Rule Builder - Fluent API for creating cleanup rules.

Provides a convenient, type-safe way to build cleanup rules without
manually specifying all the required fields.
"""

from typing import Optional
from datetime import datetime
import uuid

from src.domain.cleanup_policy import (
    CleanupRule,
    CleanupAction,
    RuleCondition,
)
from src.domain.email_thread import EmailCategory, EmailImportance


class CleanupRuleBuilder:
    """
    Fluent API for building cleanup rules.
    
    Example:
        rule = (CleanupRuleBuilder()
                .category(EmailCategory.PROMOTIONS)
                .older_than_days(30)
                .archive()
                .build())
    """
    
    def __init__(self):
        self._conditions: list = []
        self._action: Optional[CleanupAction] = None
        self._action_params: dict = {}
        self._name: Optional[str] = None
        self._description: Optional[str] = None
        self._priority: int = 100
        self._enabled: bool = True
    
    def category(self, cat: EmailCategory) -> 'CleanupRuleBuilder':
        """Match messages in the specified category."""
        self._conditions.append((RuleCondition.CATEGORY_IS, cat.value))
        return self
    
    def older_than_days(self, days: int) -> 'CleanupRuleBuilder':
        """Match messages older than N days."""
        self._conditions.append((RuleCondition.OLDER_THAN_DAYS, str(days)))
        return self
    
    def sender_matches(self, pattern: str) -> 'CleanupRuleBuilder':
        """Match messages from sender matching pattern."""
        self._conditions.append((RuleCondition.SENDER_MATCHES, pattern))
        return self
    
    def subject_contains(self, text: str) -> 'CleanupRuleBuilder':
        """Match messages with subject containing text."""
        self._conditions.append((RuleCondition.SUBJECT_CONTAINS, text))
        return self
    
    def larger_than_mb(self, mb: float) -> 'CleanupRuleBuilder':
        """Match messages larger than N MB."""
        self._conditions.append((RuleCondition.LARGER_THAN_MB, str(mb)))
        return self
    
    def importance_is(self, importance: EmailImportance) -> 'CleanupRuleBuilder':
        """Match messages with specified importance."""
        self._conditions.append((RuleCondition.IMPORTANCE_IS, importance.value))
        return self
    
    def is_unread(self, unread: bool = True) -> 'CleanupRuleBuilder':
        """Match unread messages."""
        self._conditions.append((RuleCondition.IS_UNREAD, str(unread).lower()))
        return self
    
    def is_starred(self, starred: bool = True) -> 'CleanupRuleBuilder':
        """Match starred messages."""
        self._conditions.append((RuleCondition.IS_STARRED, str(starred).lower()))
        return self
    
    def has_attachments(self, has: bool = True) -> 'CleanupRuleBuilder':
        """Match messages with attachments."""
        self._conditions.append((RuleCondition.HAS_ATTACHMENTS, str(has).lower()))
        return self
    
    def has_label(self, label: str) -> 'CleanupRuleBuilder':
        """Match messages with specified label."""
        self._conditions.append((RuleCondition.LABEL_IS, label))
        return self
    
    def archive(self) -> 'CleanupRuleBuilder':
        """Apply archive action (remove from inbox)."""
        self._action = CleanupAction.ARCHIVE
        return self
    
    def delete(self) -> 'CleanupRuleBuilder':
        """Apply delete action (move to trash)."""
        self._action = CleanupAction.DELETE
        return self
    
    def mark_read(self) -> 'CleanupRuleBuilder':
        """Apply mark as read action."""
        self._action = CleanupAction.MARK_READ
        return self
    
    def mark_unread(self) -> 'CleanupRuleBuilder':
        """Apply mark as unread action."""
        self._action = CleanupAction.MARK_UNREAD
        return self
    
    def star(self) -> 'CleanupRuleBuilder':
        """Apply star action."""
        self._action = CleanupAction.STAR
        return self
    
    def unstar(self) -> 'CleanupRuleBuilder':
        """Apply unstar action."""
        self._action = CleanupAction.UNSTAR
        return self
    
    def apply_label(self, label: str) -> 'CleanupRuleBuilder':
        """Apply label to messages."""
        self._action = CleanupAction.APPLY_LABEL
        self._action_params = {"label": label}
        return self
    
    def remove_label(self, label: str) -> 'CleanupRuleBuilder':
        """Remove label from messages."""
        self._action = CleanupAction.REMOVE_LABEL
        self._action_params = {"label": label}
        return self
    
    def skip(self) -> 'CleanupRuleBuilder':
        """Skip action (no-op, for testing)."""
        self._action = CleanupAction.SKIP
        return self
    
    def with_name(self, name: str) -> 'CleanupRuleBuilder':
        """Set rule name."""
        self._name = name
        return self
    
    def with_description(self, description: str) -> 'CleanupRuleBuilder':
        """Set rule description."""
        self._description = description
        return self
    
    def with_priority(self, priority: int) -> 'CleanupRuleBuilder':
        """Set rule priority (lower = higher priority)."""
        self._priority = priority
        return self
    
    def enabled(self, is_enabled: bool = True) -> 'CleanupRuleBuilder':
        """Set whether rule is enabled."""
        self._enabled = is_enabled
        return self
    
    def build(self) -> CleanupRule:
        """
        Build the cleanup rule.
        
        Returns:
            CleanupRule instance
            
        Raises:
            ValueError: If no conditions or action specified
        """
        if not self._conditions:
            raise ValueError("At least one condition must be specified")
        
        if self._action is None:
            raise ValueError("An action must be specified")
        
        # Use first condition as primary (for single-condition rules)
        # For multi-condition rules, we'd need to extend the domain model
        condition_type, condition_value = self._conditions[0]
        
        # Generate ID if not provided
        rule_id = str(uuid.uuid4())[:8]
        
        # Generate name if not provided
        if not self._name:
            self._name = self._generate_name(condition_type, condition_value)
        
        # Generate description if not provided
        if not self._description:
            self._description = self._generate_description()
        
        return CleanupRule(
            id=rule_id,
            name=self._name,
            description=self._description,
            condition_type=condition_type,
            condition_value=condition_value,
            action=self._action,
            action_params=self._action_params,
            enabled=self._enabled,
            priority=self._priority,
            created_at=datetime.now(),
        )
    
    def _generate_name(self, condition_type: RuleCondition, condition_value: str) -> str:
        """Generate a human-readable rule name."""
        condition_map = {
            RuleCondition.CATEGORY_IS: f"Category: {condition_value}",
            RuleCondition.OLDER_THAN_DAYS: f"Older than {condition_value} days",
            RuleCondition.SENDER_MATCHES: f"From: {condition_value}",
            RuleCondition.SUBJECT_CONTAINS: f"Subject: {condition_value}",
            RuleCondition.LARGER_THAN_MB: f"Larger than {condition_value}MB",
        }
        
        action_name = self._action.value.replace('_', ' ').title() if self._action else "Process"
        condition_desc = condition_map.get(condition_type, f"{condition_type.value}: {condition_value}")
        
        return f"{action_name} - {condition_desc}"
    
    def _generate_description(self) -> str:
        """Generate a description based on conditions and action."""
        conditions_desc = []
        for cond_type, cond_val in self._conditions:
            if cond_type == RuleCondition.CATEGORY_IS:
                conditions_desc.append(f"in {cond_val} category")
            elif cond_type == RuleCondition.OLDER_THAN_DAYS:
                conditions_desc.append(f"older than {cond_val} days")
            elif cond_type == RuleCondition.SENDER_MATCHES:
                conditions_desc.append(f"from {cond_val}")
            else:
                conditions_desc.append(f"{cond_type.value} {cond_val}")
        
        action_desc = self._action.value.replace('_', ' ')
        conditions_str = " and ".join(conditions_desc)
        
        return f"Automatically {action_desc} messages {conditions_str}"


# Convenience factory functions for common patterns
def archive_old_promotions(days: int = 30) -> CleanupRule:
    """Create rule to archive old promotional emails."""
    return (CleanupRuleBuilder()
            .category(EmailCategory.PROMOTIONS)
            .older_than_days(days)
            .archive()
            .with_name(f"Archive Old Promotions ({days}+ days)")
            .build())


def archive_old_social(days: int = 7) -> CleanupRule:
    """Create rule to archive old social media emails."""
    return (CleanupRuleBuilder()
            .category(EmailCategory.SOCIAL)
            .older_than_days(days)
            .archive()
            .with_name(f"Archive Old Social ({days}+ days)")
            .build())


def delete_very_old(days: int = 180) -> CleanupRule:
    """Create rule to delete very old emails."""
    return (CleanupRuleBuilder()
            .older_than_days(days)
            .delete()
            .with_name(f"Delete Very Old Emails ({days}+ days)")
            .with_priority(200)  # Lower priority
            .build())


def label_newsletters(label: str = "AutoCleanup/Newsletter") -> CleanupRule:
    """Create rule to label newsletter-like emails."""
    return (CleanupRuleBuilder()
            .category(EmailCategory.PROMOTIONS)
            .apply_label(label)
            .with_name("Label Newsletters")
            .build())
