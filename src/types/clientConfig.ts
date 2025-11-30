export interface CompanyProfile {
  name?: string;
  website?: string;
  industry?: string;
  size?: string;
  business_model?: string;
  objectives?: string[];
  urgency?: string;
}

export type IntegrationEffort = 'low' | 'medium' | 'high';

export interface Stack {
  website_platform?: string;
  crm?: string;
  helpdesk?: string;
  email?: string;
  project_tools?: string[];
  data_sources?: string[];
  comms_tools?: string[];
  telephony?: string;
  calendar?: string;
  integration_effort_level?: IntegrationEffort;
}

export interface SupportSystem {
  channels: string[];
  expected_daily_volume: number;
  ai_allowed_topics: string[];
  escalation_policies: string[];
  kb_sources: string[];
  coverage: { human: string; ai: string };
}

export interface ContentSystem {
  priority_types: string[];
  target_monthly_volume: Record<string, number>;
  channels: string[];
  voice_risk: number;
  approval_flow: string;
  brand_sources: string[];
}

export interface DataBiSystem {
  metrics: string[];
  sources: string[];
  reporting_cadence: string;
  nlq_examples: string[];
  data_quality: number;
}

export interface WorkflowFlow {
  name: string;
  tools: string[];
  manual_steps: string[];
  do_not_automate: string[];
}

export interface WorkflowSystem {
  target_departments: string[];
  flows: WorkflowFlow[];
}

export interface VoiceSystem {
  daily_calls: number;
  call_types: string[];
  objectives: string[];
  booking_method: string;
  greeting: string;
  tone: string;
  escalation_rules: string[];
}

export interface Constraints {
  compliance: string[];
  data_sensitivity: string[];
}

export type BudgetRange = '<$1k' | '$1–3k' | '$3–7k' | '$7k+';

export interface Budget {
  monthly_range: BudgetRange;
  phased_rollout_preference: 'start_small' | 'fully_designed';
}

export interface ClientConfig {
  company_profile: CompanyProfile;
  stack: Stack;
  support_system?: SupportSystem;
  content_system?: ContentSystem;
  data_bi_system?: DataBiSystem;
  workflow_system?: WorkflowSystem;
  voice_system?: VoiceSystem;
  constraints: Constraints;
  budget: Budget;
  priorities: string[];
}

export default ClientConfig;
