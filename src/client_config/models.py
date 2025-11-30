from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, HttpUrl


class SupportSystem(BaseModel):
    channels: List[str]
    expected_daily_volume: int
    ai_allowed_topics: List[str]
    escalation_policies: List[str]
    kb_sources: List[str]
    coverage: Dict[str, str]


class ContentSystem(BaseModel):
    priority_types: List[str]
    target_monthly_volume: Dict[str, int]
    channels: List[str]
    voice_risk: int
    approval_flow: str
    brand_sources: List[str]


class DataBiSystem(BaseModel):
    metrics: List[str]
    sources: List[str]
    reporting_cadence: str
    nlq_examples: List[str]
    data_quality: int


class WorkflowFlow(BaseModel):
    name: str
    tools: List[str]
    manual_steps: List[str]
    do_not_automate: List[str]


class WorkflowSystem(BaseModel):
    target_departments: List[str]
    flows: List[WorkflowFlow]


class VoiceSystem(BaseModel):
    daily_calls: int
    call_types: List[str]
    objectives: List[str]
    booking_method: str
    greeting: str
    tone: str
    escalation_rules: List[str]


class Constraints(BaseModel):
    compliance: List[str]
    data_sensitivity: List[str]


class Budget(BaseModel):
    monthly_range: Literal['<$1k', '$1–3k', '$3–7k', '$7k+']
    phased_rollout_preference: Literal['start_small', 'fully_designed']


class CompanyProfile(BaseModel):
    name: str
    website: Optional[HttpUrl]
    industry: Optional[str]
    size: Optional[str]
    business_model: Optional[str]
    objectives: List[str]
    urgency: Optional[str]


class ClientConfig(BaseModel):
    company_profile: CompanyProfile
    stack: Dict[str, Optional[str]]
    support_system: Optional[SupportSystem]
    content_system: Optional[ContentSystem]
    data_bi_system: Optional[DataBiSystem]
    workflow_system: Optional[WorkflowSystem]
    voice_system: Optional[VoiceSystem]
    constraints: Constraints
    budget: Budget
    priorities: List[str]


__all__ = [
    'SupportSystem', 'ContentSystem', 'DataBiSystem', 'WorkflowFlow', 'WorkflowSystem',
    'VoiceSystem', 'Constraints', 'Budget', 'CompanyProfile', 'ClientConfig',
]
