"""
Customer Domain Model - Core business entity for SaaS customers.

Represents a paying customer with plan tier, quotas, and billing info.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
from uuid import UUID, uuid4


class PlanTier(str, Enum):
    """Subscription plan tiers"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class CustomerStatus(str, Enum):
    """Customer account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class SubscriptionStatus(str, Enum):
    """Stripe subscription status"""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    INCOMPLETE = "incomplete"


@dataclass
class PlanQuota:
    """Quota limits for a plan tier"""
    plan_tier: PlanTier
    emails_per_month: int
    cleanups_per_day: int
    api_calls_per_hour: int
    price_monthly_cents: int
    features: Dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def get_plan_quotas() -> Dict[PlanTier, "PlanQuota"]:
        """Get quota definitions for all plans"""
        return {
            PlanTier.FREE: PlanQuota(
                plan_tier=PlanTier.FREE,
                emails_per_month=500,
                cleanups_per_day=1,
                api_calls_per_hour=10,
                price_monthly_cents=0,
                features={
                    "scheduled_cleanups": False,
                    "api_access": False,
                    "priority_support": False,
                }
            ),
            PlanTier.BASIC: PlanQuota(
                plan_tier=PlanTier.BASIC,
                emails_per_month=5000,
                cleanups_per_day=10,
                api_calls_per_hour=100,
                price_monthly_cents=900,  # $9.00
                features={
                    "scheduled_cleanups": True,
                    "api_access": False,
                    "priority_support": False,
                }
            ),
            PlanTier.PRO: PlanQuota(
                plan_tier=PlanTier.PRO,
                emails_per_month=50000,
                cleanups_per_day=100,
                api_calls_per_hour=1000,
                price_monthly_cents=2900,  # $29.00
                features={
                    "scheduled_cleanups": True,
                    "api_access": True,
                    "priority_support": False,
                }
            ),
            PlanTier.ENTERPRISE: PlanQuota(
                plan_tier=PlanTier.ENTERPRISE,
                emails_per_month=500000,
                cleanups_per_day=1000,
                api_calls_per_hour=10000,
                price_monthly_cents=9900,  # $99.00
                features={
                    "scheduled_cleanups": True,
                    "api_access": True,
                    "priority_support": True,
                    "custom_policies": True,
                    "sso": True,
                }
            ),
        }


@dataclass
class Customer:
    """
    Customer entity representing a SaaS customer account.
    
    Includes plan tier, billing info, and quota management.
    """
    id: UUID
    email: str
    name: Optional[str]
    password_hash: str
    plan_tier: PlanTier
    status: CustomerStatus = CustomerStatus.ACTIVE
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    
    # Billing
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_status: Optional[SubscriptionStatus] = None
    trial_ends_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_quota(self) -> PlanQuota:
        """Get quota limits for customer's plan tier"""
        quotas = PlanQuota.get_plan_quotas()
        return quotas[self.plan_tier]
    
    def is_on_trial(self) -> bool:
        """Check if customer is in trial period"""
        if not self.trial_ends_at:
            return False
        return datetime.utcnow() < self.trial_ends_at
    
    def trial_days_remaining(self) -> int:
        """Get number of trial days remaining"""
        if not self.is_on_trial():
            return 0
        delta = self.trial_ends_at - datetime.utcnow()
        return max(0, delta.days)
    
    def can_execute_cleanup(self, daily_count: int) -> bool:
        """Check if customer can execute another cleanup today"""
        quota = self.get_quota()
        return daily_count < quota.cleanups_per_day
    
    def has_feature(self, feature: str) -> bool:
        """Check if customer's plan includes a feature"""
        quota = self.get_quota()
        return quota.features.get(feature, False)
    
    def is_active(self) -> bool:
        """Check if customer account is active"""
        return self.status == CustomerStatus.ACTIVE
    
    def is_paid_plan(self) -> bool:
        """Check if customer is on a paid plan"""
        return self.plan_tier != PlanTier.FREE
    
    def monthly_price_usd(self) -> float:
        """Get monthly price in USD"""
        quota = self.get_quota()
        return quota.price_monthly_cents / 100.0
    
    @staticmethod
    def create(
        email: str,
        password_hash: str,
        name: Optional[str] = None,
        plan_tier: PlanTier = PlanTier.FREE,
        trial_days: int = 14,
    ) -> "Customer":
        """
        Create a new customer with optional trial period.
        
        Args:
            email: Customer email (will be lowercased)
            password_hash: Bcrypt password hash
            name: Customer full name
            plan_tier: Initial plan tier
            trial_days: Trial period length (default 14 days)
            
        Returns:
            New Customer instance
        """
        trial_ends_at = None
        if trial_days > 0 and plan_tier != PlanTier.FREE:
            trial_ends_at = datetime.utcnow() + timedelta(days=trial_days)
        
        return Customer(
            id=uuid4(),
            email=email.lower(),
            name=name,
            password_hash=password_hash,
            plan_tier=plan_tier,
            trial_ends_at=trial_ends_at,
            subscription_status=SubscriptionStatus.TRIALING if trial_ends_at else None,
        )


@dataclass
class UsageStats:
    """
    Usage statistics for a customer in a billing period.
    """
    customer_id: UUID
    period_start: datetime
    period_end: datetime
    
    # Usage metrics
    emails_processed: int = 0
    cleanups_executed: int = 0
    api_calls: int = 0
    storage_freed_mb: float = 0.0
    
    # Quota tracking
    quota_limit: int = 0
    quota_used: int = 0
    
    def quota_remaining(self) -> int:
        """Get remaining quota"""
        return max(0, self.quota_limit - self.quota_used)
    
    def quota_percentage(self) -> float:
        """Get quota usage as percentage"""
        if self.quota_limit == 0:
            return 0.0
        return (self.quota_used / self.quota_limit) * 100.0
    
    def is_quota_exceeded(self) -> bool:
        """Check if quota is exceeded"""
        return self.quota_used >= self.quota_limit
    
    def approaching_quota(self, threshold: float = 0.8) -> bool:
        """Check if approaching quota limit"""
        return self.quota_percentage() >= (threshold * 100)


# Quota exceeded exception
class QuotaExceededError(Exception):
    """Raised when customer exceeds their plan quota"""
    
    def __init__(self, customer: Customer, usage: UsageStats):
        self.customer = customer
        self.usage = usage
        super().__init__(
            f"Quota exceeded for customer {customer.email}. "
            f"Used {usage.quota_used}/{usage.quota_limit} emails this month."
        )
