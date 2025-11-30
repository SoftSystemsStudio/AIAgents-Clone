from .models import ClientConfig, CompanyProfile, Budget, Constraints
from typing import Any, Dict


def build_client_config_from_intake(raw: Dict[str, Any]) -> ClientConfig:
    """
    Convert a raw intake payload (dict) into a validated ClientConfig.

    This function centralizes normalization logic; keep it deterministic and testable.
    """
    company = raw.get('company_profile', {})

    company_profile = CompanyProfile(
        name=company.get('name', 'Unknown'),
        website=company.get('website'),
        industry=company.get('industry'),
        size=company.get('size'),
        business_model=company.get('business_model'),
        objectives=company.get('objectives') or [],
        urgency=company.get('urgency'),
    )

    # Stack: keep as a simple dict of strings (frontend may send optional keys)
    stack = raw.get('stack') or {
        'website_platform': raw.get('website_platform'),
        'crm': raw.get('crm'),
        'helpdesk': raw.get('helpdesk'),
        'email': raw.get('email'),
        'telephony': raw.get('telephony'),
        'calendar': raw.get('calendar'),
    }

    # Optional system sections
    support_section = raw.get('support_system')
    content_section = raw.get('content_system')
    data_bi_section = raw.get('data_bi_system')
    workflow_section = raw.get('workflow_system')
    voice_section = raw.get('voice_system')

    # Constraints and budget with sensible defaults
    constraints = raw.get('constraints') or {'compliance': [], 'data_sensitivity': []}
    budget = raw.get('budget') or {'monthly_range': '<$1k', 'phased_rollout_preference': 'start_small'}

    cfg = {
        'company_profile': company_profile.dict(),
        'stack': stack,
        'support_system': support_section,
        'content_system': content_section,
        'data_bi_system': data_bi_section,
        'workflow_system': workflow_section,
        'voice_system': voice_section,
        'constraints': constraints,
        'budget': budget,
        'priorities': company.get('objectives') or raw.get('priorities') or [],
    }

    # Validate and return a Pydantic ClientConfig instance
    return ClientConfig.parse_obj(cfg)


def infer_integration_effort(stack: Dict[str, Any]) -> str:
    """Heuristic used to populate `integration_effort_level` if needed."""
    score = 0
    platform = (stack.get('website_platform') or '').lower()
    crm = (stack.get('crm') or '').lower()
    if platform in ('webflow', 'shopify', 'squarespace', 'wordpress'):
        score -= 1
    if crm in ('hubspot', 'salesforce', 'pipedrive'):
        score -= 1
    if stack.get('custom_backend'):
        score += 2
    if stack.get('data_sources') and len(stack.get('data_sources', [])) > 1:
        score += 1

    if score <= -1:
        return 'low'
    if score == 0:
        return 'medium'
    return 'high'
